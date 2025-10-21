/*
 * Teensy 4.1 Keysight 33600A Controller via Ethernet - OPTIMIZED VERSION
 * 
 * 優化項目：
 * 1. 持續維持 TCP 連線，避免重複 connect()
 * 2. 確保所有 SCPI 指令都有換行符 (\n)
 * 3. 使用固定 IP，避免 DHCP/ARP 延遲
 * 4. 調整 W5500 重傳參數
 * 5. 啟用 TCP_NODELAY，關閉 Nagle 演算法
 * 6. 合併多條 SCPI 指令一次傳送
 */

#include <SPI.h>
#include <Ethernet.h>
#include "waveform_data.h"

// W5500 SPI 引腳配置 (Teensy 4.1)
#define W5500_CS_PIN 10
#define W5500_RST_PIN 8

// 固定 IP 網路設定 - 避免 DHCP 延遲
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED};
IPAddress local_ip(192, 168, 0, 10);      // Teensy 固定 IP
IPAddress keysight_ip(192, 168, 0, 21);   // Keysight 固定 IP
IPAddress gateway(192, 168, 0, 1);
IPAddress subnet(255, 255, 255, 0);
int keysight_port = 5025;

// 全域 Ethernet 客戶端 - 持續維持連線
EthernetClient client;

#define DEBUG_MODE 0

struct ModeConfig {
  const char* name;
  const char* ch1_polarity;
  const char* ch2_polarity;
  float ch1_voltage;
  float ch2_voltage;
};

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
  while (!Serial) delay(10);
  
  Serial.println("=== Teensy 4.1 Keysight Controller - OPTIMIZED ===");
  
  // 初始化 W5500
  initializeW5500();
  
  // 使用固定 IP 初始化 Ethernet
  Ethernet.begin(mac, local_ip, gateway, subnet);
  delay(100);
  
  Serial.print("Local IP: ");
  Serial.println(Ethernet.localIP());
  Serial.print("Target IP: ");
  Serial.println(keysight_ip);
  
  // 優化 W5500 TCP 參數
  optimizeW5500Settings();
  
  // 建立持續連線
  establishPersistentConnection();
  
  showMenu();
}

void loop() {
  // 輕量級連線檢查
  static unsigned long last_check = 0;
  if (millis() - last_check > 1000) {  // 每秒檢查一次
    if (!client.connected() && keysight_connected) {
      Serial.println("Connection lost, reconnecting...");
      establishPersistentConnection();
    }
    last_check = millis();
  }
  
  // 立即處理 Serial 輸入
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input.length() == 1 && input >= "1" && input <= "4") {
      int mode = input.toInt() - 1;
      runModeOptimized(mode);
    } else if (input == "5") {
      shutdownKeysight();
    } else if (input == "menu" || input == "m") {
      showMenu();
    } else if (input == "reconnect" || input == "r") {
      establishPersistentConnection();
    } else if (input == "status" || input == "s") {
      showConnectionStatus();
    } else if (input.length() > 0) {
      Serial.println("Invalid! Type 'menu'");
    }
  }
  
  // 最小延遲
  delay(1);
}

void initializeW5500() {
  pinMode(W5500_CS_PIN, OUTPUT);
  digitalWrite(W5500_CS_PIN, HIGH);
  pinMode(W5500_RST_PIN, OUTPUT);
  
  // 硬體重置 W5500
  digitalWrite(W5500_RST_PIN, LOW);
  delay(10);
  digitalWrite(W5500_RST_PIN, HIGH);
  delay(50);
  
  Serial.println("W5500 initialized");
}

void optimizeW5500Settings() {
  // 調整 W5500 重傳參數以減少延遲
  // 這些設定需要直接操作 W5500 暫存器
  
  // 設定較短的重傳時間 (RTR) - 預設值通常太大
  // RTR = 2000 (200ms) instead of default 2000 (2000ms)
  Ethernet.setRetransmissionTimeout(200);  // 200ms
  Ethernet.setRetransmissionCount(3);      // 3次重試
  
  Serial.println("W5500 TCP parameters optimized");
}

void establishPersistentConnection() {
  if (client.connected()) {
    client.stop();
    delay(100);
  }
  
  Serial.print("Establishing persistent connection...");
  
  // 嘗試連線，有重試機制
  for (int attempt = 1; attempt <= 3; attempt++) {
    if (client.connect(keysight_ip, keysight_port)) {
      keysight_connected = true;
      
      // 啟用 TCP_NODELAY (關閉 Nagle 演算法)
      client.setNoDelay(true);
      
      Serial.println(" ✅ Connected!");
      
      // 批次初始化指令
      initializeKeysightBatch();
      return;
    } else {
      Serial.print(" Attempt ");
      Serial.print(attempt);
      Serial.println(" failed");
      delay(500);
    }
  }
  
  keysight_connected = false;
  Serial.println(" ❌ All attempts failed!");
}

void initializeKeysightBatch() {
  // 合併多條初始化指令一次送出
  String batch_commands = "*IDN?\n"
                         "OUTP1 OFF\n"
                         "OUTP2 OFF\n"
                         "MMEMORY:MDIR \"INT:\\remoteAdded\"\n"
                         "FORM:BORD SWAP\n";
  
  sendSCPIBatch(batch_commands);
  
  // 讀取設備 ID 回應
  delay(100);
  if (client.available()) {
    String response = client.readStringUntil('\n');
    response.trim();
    Serial.println("Device: " + response.substring(0, 30) + "...");
  }
  
  Serial.println("Keysight initialized with batch commands");
}

void runModeOptimized(int mode_num) {
  if (mode_num < 0 || mode_num > 3) {
    Serial.println("Invalid mode!");
    return;
  }
  
  if (!keysight_connected || !client.connected()) {
    Serial.println("❌ Not connected! Reconnecting...");
    establishPersistentConnection();
    if (!keysight_connected) return;
  }
  
  current_mode = mode_num;
  ModeConfig& mode = modes[mode_num];
  
  Serial.print("Switching to ");
  Serial.println(mode.name);
  
  unsigned long start_time = millis();
  
  // 步驟 1: 關閉輸出 (批次指令)
  String shutdown_batch = "OUTP1 OFF\n"
                         "OUTP2 OFF\n"
                         "SOUR2:TRACK OFF\n";
  sendSCPIBatch(shutdown_batch);
  delay(50);
  
  // 步驟 2: 上傳波形數據 (優化版)
  uploadWaveformOptimized(1, mode_num * 2);
  uploadWaveformOptimized(2, mode_num * 2 + 1);
  
  // 步驟 3: 配置通道參數 (批次指令)
  configureChannelsBatch(mode, mode_num);
  
  // 步驟 4: 最終設定和啟用 (批次指令)
  String final_batch = "OUTP1:POL " + String(mode.ch1_polarity) + "\n"
                      "OUTP2:POL " + String(mode.ch2_polarity) + "\n"
                      "OUTP:SYNC ON\n"
                      "OUTP:SYNC:SOURCE CH1\n"
                      "OUTP:SYNC:MODE MARK\n"
                      "OUTP1 ON\n"
                      "OUTP2 ON\n"
                      "DISP:TEXT ''\n";
  sendSCPIBatch(final_batch);
  
  unsigned long elapsed = millis() - start_time;
  Serial.print("✅ Mode activated in ");
  Serial.print(elapsed);
  Serial.println(" ms");
}

void uploadWaveformOptimized(int channel, int waveform_index) {
  const WaveformInfo& wf = waveform_info[waveform_index];
  String waveform_name = "MODAL_CH" + String(channel);
  
  // 清除舊數據
  sendSCPIFast("SOUR" + String(channel) + ":DATA:VOL:CLE");
  
  // 分批上傳大型波形數據以避免緩衝區溢出
  const int BATCH_SIZE = 200;  // 每批 200 個點
  
  for (int start = 0; start < wf.length; start += BATCH_SIZE) {
    int end = min(start + BATCH_SIZE, wf.length);
    
    String cmd;
    if (start == 0) {
      cmd = "SOUR" + String(channel) + ":DATA:ARB " + waveform_name + ",";
    } else {
      cmd = "SOUR" + String(channel) + ":DATA:ARB:APPEND ";
    }
    
    // 建構數據字串
    for (int i = start; i < end; i++) {
      if (i > start) cmd += ",";
      cmd += String(wf.data[i], 6);
    }
    cmd += "\n";
    
    // 直接發送，不使用 println() 避免額外的 \r
    client.print(cmd);
    client.flush();
    
    // 小延遲讓設備處理
    delay(10);
  }
  
  // 儲存波形
  sendSCPIFast("MMEM:STOR:DATA \"INT:\\remoteAdded\\" + waveform_name + ".arb\"");
  
  Serial.print("CH");
  Serial.print(channel);
  Serial.print(" uploaded ");
  Serial.print(wf.length);
  Serial.println(" points");
}

void configureChannelsBatch(ModeConfig& mode, int mode_num) {
  const WaveformInfo& wf1 = waveform_info[mode_num * 2];
  const WaveformInfo& wf2 = waveform_info[mode_num * 2 + 1];
  
  float freq1 = wf1.sample_rate / wf1.length;
  float freq2 = wf2.sample_rate / wf2.length;
  
  // 合併所有通道配置指令
  String config_batch = "SOUR1:FUNC ARB\n"
                       "SOUR1:FUNC:ARB MODAL_CH1\n"
                       "SOUR1:FUNC:ARB:SRAT " + String(wf1.sample_rate, 0) + "\n"
                       "SOUR1:VOLT " + String(mode.ch1_voltage, 1) + "\n"
                       "SOUR1:VOLT:OFFS 0\n"
                       "SOUR1:FREQ " + String(freq1, 2) + "\n"
                       "SOUR1:PHAS 0\n"
                       "SOUR2:FUNC ARB\n"
                       "SOUR2:FUNC:ARB MODAL_CH2\n"
                       "SOUR2:FUNC:ARB:SRAT " + String(wf2.sample_rate, 0) + "\n"
                       "SOUR2:VOLT " + String(mode.ch2_voltage, 1) + "\n"
                       "SOUR2:VOLT:OFFS 0\n"
                       "SOUR2:FREQ " + String(freq2, 2) + "\n"
                       "SOUR2:PHAS 0\n"
                       "SOUR1:TRACK OFF\n"
                       "SOUR2:TRACK OFF\n"
                       "SOUR2:TRACK ON\n";
  
  sendSCPIBatch(config_batch);
  
  // 同步相位
  delay(50);
  sendSCPIFast("SOUR2:PHAS:SYNC");
  sendSCPIFast("SOUR2:PHAS 0");
  
  Serial.print("Configured: CH1=");
  Serial.print(freq1, 2);
  Serial.print("Hz, CH2=");
  Serial.print(freq2, 2);
  Serial.println("Hz");
}

void sendSCPIBatch(String commands) {
  if (!client.connected()) {
    Serial.println("❌ Connection lost during batch send!");
    keysight_connected = false;
    return;
  }
  
  // 直接發送批次指令，確保每行都有 \n
  client.print(commands);
  client.flush();
  
  if (DEBUG_MODE) {
    Serial.println("SCPI Batch → ");
    Serial.print(commands);
  }
}

void sendSCPIFast(String command) {
  if (!client.connected()) {
    Serial.println("❌ Connection lost!");
    keysight_connected = false;
    return;
  }
  
  // 確保指令以 \n 結尾
  if (!command.endsWith("\n")) {
    command += "\n";
  }
  
  client.print(command);
  client.flush();
  
  if (DEBUG_MODE) {
    Serial.println("SCPI → " + command.substring(0, command.length()-1));
  }
}

String sendSCPIQuery(String command) {
  String response = "";
  
  if (!client.connected()) {
    Serial.println("❌ Connection lost during query!");
    keysight_connected = false;
    return response;
  }
  
  // 確保查詢指令以 \n 結尾
  if (!command.endsWith("\n")) {
    command += "\n";
  }
  
  client.print(command);
  client.flush();
  
  // 優化的超時等待
  unsigned long timeout = millis() + 1000; // 減少到 1 秒
  while (millis() < timeout && !client.available()) {
    delay(1);
  }
  
  if (client.available()) {
    response = client.readStringUntil('\n');
    response.trim();
  }
  
  return response;
}

void shutdownKeysight() {
  Serial.println("Shutting down...");
  
  if (client.connected()) {
    String shutdown_batch = "OUTP1 OFF\n"
                           "OUTP2 OFF\n"
                           "SOUR2:TRACK OFF\n";
    sendSCPIBatch(shutdown_batch);
    delay(100);
  }
  
  Serial.println("✅ Shutdown complete");
}

void showConnectionStatus() {
  Serial.println("\n=== Connection Status ===");
  Serial.print("Ethernet Link: ");
  Serial.println(Ethernet.linkStatus() == LinkON ? "✅ UP" : "❌ DOWN");
  Serial.print("Local IP: ");
  Serial.println(Ethernet.localIP());
  Serial.print("TCP Connection: ");
  Serial.println(client.connected() ? "✅ Connected" : "❌ Disconnected");
  Serial.print("Keysight Status: ");
  Serial.println(keysight_connected ? "✅ Ready" : "❌ Not Ready");
  Serial.println("========================");
}

void showMenu() {
  Serial.println("\n" + String('=', 60));
  Serial.println("Teensy 4.1 Keysight Controller - OPTIMIZED VERSION");
  Serial.println("Connection: " + String(keysight_connected ? "✅ Connected" : "❌ Disconnected"));
  Serial.println(String('=', 60));
  Serial.println("Commands:");
  Serial.println("1-4 - Switch to Mode 1-4");
  Serial.println("5   - Shutdown outputs");
  Serial.println("r   - Reconnect");
  Serial.println("s   - Show connection status");
  Serial.println("m   - Show this menu");
  Serial.println(String('=', 60));
  Serial.print("Enter command: ");
}
