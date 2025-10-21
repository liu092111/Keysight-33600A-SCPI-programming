/*
 * Teensy 4.1 Keysight 33600A Controller via Ethernet
 * 
 * 硬體連接：
 * Teensy 4.1 ←→ W5500 Ethernet Shield ←→ 網路交換器 ←→ Keysight 33600A LAN
 * 電腦 ←→ Micro USB ←→ Teensy 4.1 (供電 + 程式上傳 + Serial 控制)
 * 
 * 優勢：
 * - 無需製作 USB Host 線纜
 * - 可透過電腦 Serial Monitor 控制
 * - 網路連接更穩定
 * - 支援遠端控制
 */

#include <SPI.h>
#include <Ethernet.h>
#include "waveform_data.h"

// W5500 SPI 引腳配置 (Teensy 4.1)
#define W5500_CS_PIN 10    // Chip Select 引腳
#define W5500_RST_PIN 8    // Reset 引腳 (可選)

// 網路設定
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED};
IPAddress keysight_ip(169, 254, 5, 21);  // Keysight IP 地址
int keysight_port = 5025;  // SCPI 標準端口

// Ethernet 客戶端
EthernetClient client;

// 除錯模式 (設為0可大幅減少輸出訊息，提升響應速度)
#define DEBUG_MODE 0

// 模式配置
struct ModeConfig {
  const char* name;
  const char* ch1_polarity;
  const char* ch2_polarity;
  float ch1_voltage;
  float ch2_voltage;
};

// 4種模式配置
ModeConfig modes[4] = {
  {"Mode 1 (25k-50k Hz)", "NORM", "INV", 1.2, 1.2},
  {"Mode 2 (47k-94k Hz)", "NORM", "INV", 1.2, 1.2},
  {"Mode 3 (25k-50k Hz, CH1 Inverted)", "INV", "NORM", 1.2, 1.2},
  {"Mode 4 (47k-94k Hz, CH1 Inverted)", "INV", "NORM", 1.2, 1.2}
};

bool keysight_connected = false;
int current_mode = -1;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);  // 減少等待時間
  
  Serial.println("=== Teensy 4.1 Keysight Controller ===");
  
  // 初始化 W5500 SPI 引腳 (簡化輸出)
  pinMode(W5500_CS_PIN, OUTPUT);
  digitalWrite(W5500_CS_PIN, HIGH);
  pinMode(W5500_RST_PIN, OUTPUT);
  digitalWrite(W5500_RST_PIN, LOW);
  delay(10);
  digitalWrite(W5500_RST_PIN, HIGH);
  delay(50);  // 減少delay時間
  
  // 初始化 Ethernet
  if (Ethernet.begin(mac) == 0) {
    // 使用靜態 IP
    IPAddress ip(169, 254, 5, 100);
    IPAddress gateway(169, 254, 5, 21);
    IPAddress subnet(255, 255, 0, 0);
    Ethernet.begin(mac, ip, gateway, subnet);
  }
  
  delay(500);  // 減少delay時間
  
  Serial.print("IP: ");
  Serial.println(Ethernet.localIP());
  
  // 連接到 Keysight
  connectToKeysight();
  
  showMenu();
}

void loop() {
  // 維持 Ethernet 連接 (每100次循環執行一次)
  static int maintain_counter = 0;
  if (++maintain_counter >= 100) {
    Ethernet.maintain();
    maintain_counter = 0;
  }
  
  // 檢查 Serial 輸入 (立即響應)
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input.length() == 1 && input >= "1" && input <= "4") {
      int mode = input.toInt() - 1;
      runMode(mode);
    } else if (input == "5") {
      shutdownKeysight();
      Serial.println("Shutdown");
    } else if (input == "menu" || input == "m") {
      showMenu();
    } else if (input == "reconnect" || input == "r") {
      connectToKeysight();
    } else if (input == "ip") {
      Serial.println(Ethernet.localIP());
    } else if (input.length() > 0) {
      Serial.println("Invalid! Type 'menu'");
    }
  }
  
  delay(1);  // 大幅減少delay，提升響應速度
}

void connectToKeysight() {
  Serial.print("Connecting...");
  
  if (client.connect(keysight_ip, keysight_port)) {
    keysight_connected = true;
    Serial.println(" ✅ Connected!");
    
    // 初始化設備
    initializeKeysight();
  } else {
    keysight_connected = false;
    Serial.println(" ❌ Failed!");
    Serial.println("Type 'reconnect' to try again");
  }
}

void initializeKeysight() {
  // 查詢設備ID (簡化輸出)
  String response = sendSCPIQuery("*IDN?");
  if (response.length() > 0) {
    Serial.println("Device: " + response.substring(0, 20) + "...");
  }
  
  // 初始設定
  sendSCPI("OUTP1 OFF");
  sendSCPI("OUTP2 OFF");
  sendSCPI("MMEMORY:MDIR \"INT:\\remoteAdded\"");
  sendSCPI("FORM:BORD SWAP");
  
  Serial.println("Ready!");
}

void runMode(int mode_num) {
  if (mode_num < 0 || mode_num > 3) {
    Serial.println("Invalid mode!");
    return;
  }
  
  if (!keysight_connected) {
    Serial.println("❌ Not connected! Type 'reconnect'");
    return;
  }
  
  current_mode = mode_num;
  ModeConfig& mode = modes[mode_num];
  
  Serial.print("Switching to ");
  Serial.println(mode.name);
  
  // 關閉輸出
  sendSCPI("OUTP1 OFF");
  sendSCPI("OUTP2 OFF");
  sendSCPI("SOUR2:TRACK OFF");
  delay(50);  // 減少delay
  
  // 上傳波形數據
  uploadWaveform(1, mode_num * 2);
  uploadWaveform(2, mode_num * 2 + 1);
  
  // 配置通道參數
  configureChannel(1, mode, mode_num * 2);
  configureChannel(2, mode, mode_num * 2 + 1);
  
  // 設定同步
  setupSyncInternal();
  
  // 設定極性
  sendSCPI("OUTP1:POL " + String(mode.ch1_polarity));
  sendSCPI("OUTP2:POL " + String(mode.ch2_polarity));
  
  // 設定同步輸出
  sendSCPI("OUTP:SYNC ON");
  sendSCPI("OUTP:SYNC:SOURCE CH1");
  sendSCPI("OUTP:SYNC:MODE MARK");
  
  // 啟用輸出
  sendSCPI("OUTP1 ON");
  sendSCPI("OUTP2 ON");
  sendSCPI("DISP:TEXT ''");
  
  Serial.println("✅ Mode activated!");
}

void uploadWaveform(int channel, int waveform_index) {
  const WaveformInfo& wf = waveform_info[waveform_index];
  String waveform_name = "MODAL_CH" + String(channel);
  
  sendSCPI("SOUR" + String(channel) + ":DATA:VOL:CLE");
  
  // 上傳完整波形數據 (2000點)
  String cmd = "SOUR" + String(channel) + ":DATA:ARB " + waveform_name + ",";
  cmd += String(wf.data[0], 6);
  for (int i = 1; i < wf.length; i++) {  // 使用完整長度
    cmd += "," + String(wf.data[i], 6);
  }
  
  sendSCPI(cmd);
  sendSCPI("MMEM:STOR:DATA \"INT:\\remoteAdded\\" + waveform_name + ".arb\"");
  
  Serial.print("Uploaded ");
  Serial.print(wf.length);
  Serial.println(" points");
  
  delay(100);  // 增加delay給更多時間處理
}

void configureChannel(int channel, ModeConfig& mode, int waveform_index) {
  const WaveformInfo& wf = waveform_info[waveform_index];
  String ch = String(channel);
  String waveform_name = "MODAL_CH" + ch;
  
  sendSCPI("SOUR" + ch + ":FUNC ARB");
  sendSCPI("SOUR" + ch + ":FUNC:ARB " + waveform_name);
  sendSCPI("SOUR" + ch + ":FUNC:ARB:SRAT " + String(wf.sample_rate, 0));
  
  float voltage = (channel == 1) ? mode.ch1_voltage : mode.ch2_voltage;
  sendSCPI("SOUR" + ch + ":VOLT " + String(voltage, 1));
  sendSCPI("SOUR" + ch + ":VOLT:OFFS 0");
  
  // 正確的頻率計算：基頻 = 採樣率 / 波形長度
  float frequency = wf.sample_rate / wf.length;
  sendSCPI("SOUR" + ch + ":FREQ " + String(frequency, 2));
  sendSCPI("SOUR" + ch + ":PHAS 0");
  
  Serial.print("CH");
  Serial.print(channel);
  Serial.print(": ");
  Serial.print(frequency, 2);
  Serial.print(" Hz, SR: ");
  Serial.print(wf.sample_rate, 0);
  Serial.println(" Hz");
}

void setupSyncInternal() {
  sendSCPI("SOUR1:TRACK OFF");
  sendSCPI("SOUR2:TRACK OFF");
  sendSCPI("SOUR2:TRACK ON");
  delay(50);  // 減少delay
  sendSCPI("SOUR2:PHAS:SYNC");
  sendSCPI("SOUR2:PHAS 0");
}

void shutdownKeysight() {
  Serial.println("Shutting down Keysight outputs...");
  sendSCPI("OUTP1 OFF");
  sendSCPI("OUTP2 OFF");
  sendSCPI("SOUR2:TRACK OFF");
  
  if (client.connected()) {
    client.stop();
  }
  keysight_connected = false;
}

void sendSCPI(String command) {
  if (client.connected()) {
    client.println(command);
    client.flush();
    
    if (DEBUG_MODE) {
      Serial.println("SCPI → " + command);
    }
  } else {
    Serial.println("❌ Error: Keysight not connected!");
    keysight_connected = false;
  }
}

String sendSCPIQuery(String command) {
  String response = "";
  
  if (client.connected()) {
    client.println(command);
    client.flush();
    
    if (DEBUG_MODE) {
      Serial.println("SCPI Query → " + command);
    }
    
    // 等待回應
    unsigned long timeout = millis() + 2000; // 2秒超時
    while (millis() < timeout && !client.available()) {
      delay(1);
    }
    
    if (client.available()) {
      response = client.readStringUntil('\n');
      response.trim();
      
      if (DEBUG_MODE) {
        Serial.println("SCPI Response ← " + response);
      }
    }
  } else {
    Serial.println("❌ Error: Keysight not connected!");
    keysight_connected = false;
  }
  
  return response;
}

void showMenu() {
  Serial.println("\n" + String('=', 60));
  Serial.println("Teensy 4.1 Keysight 33600A Ethernet Controller");
  Serial.println("Connection Status: " + String(keysight_connected ? "✅ Connected" : "❌ Disconnected"));
  Serial.println(String('=', 60));
  Serial.println("Commands:");
  Serial.println("1 - Mode 1 (25k-50k Hz, CH1:Normal, CH2:Inverted)");
  Serial.println("2 - Mode 2 (47k-94k Hz, CH1:Normal, CH2:Inverted)");
  Serial.println("3 - Mode 3 (25k-50k Hz, CH1:Inverted, CH2:Normal)");
  Serial.println("4 - Mode 4 (47k-94k Hz, CH1:Inverted, CH2:Normal)");
  Serial.println("5 - Shutdown");
  Serial.println("reconnect - Reconnect to Keysight");
  Serial.println("ip - Show current IP address");
  Serial.println("menu - Show this menu");
  Serial.println(String('=', 60));
  Serial.print("Enter command: ");
}
