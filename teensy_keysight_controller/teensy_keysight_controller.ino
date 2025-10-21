/*
 * Teensy 4.1 Keysight 33600A Controller
 * 替代Python程式，直接控制Keysight 33600A
 * 
 * 硬體連接：
 * Teensy 4.1 USB Host (Pin 34-37) ←→ USB A-B 線纜 ←→ Keysight 33600A
 * 
 * 程式上傳：
 * 電腦 ←→ Micro USB ←→ Teensy 4.1 (僅用於程式開發)
 * 
 * 運行時：
 * Teensy 4.1 獨立運行，無需電腦和VISA
 */

#include <USBHost_t36.h>
#include "waveform_data.h"  // 包含轉換後的波形數據

// USB Host setup for connecting to Keysight
USBHost myusb;
USBSerial userial(myusb);

// 除錯模式
#define DEBUG_MODE 1

// 波形數據結構
struct WaveformData {
  float* values;
  int length;
  float sampleRate;
  float frequency;
};

// 模式配置
struct ModeConfig {
  const char* name;
  const char* file1;
  const char* file2;
  const char* ch1_polarity;
  const char* ch2_polarity;
  float ch1_voltage;
  float ch2_voltage;
};

// 4種模式配置
ModeConfig modes[4] = {
  {"Mode 1 (25k-50k Hz)", "modal1_ch1", "modal1_ch2", "NORM", "INV", 1.2, 1.2},
  {"Mode 2 (47k-94k Hz)", "modal2_ch1", "modal2_ch2", "NORM", "INV", 1.2, 1.2},
  {"Mode 3 (25k-50k Hz, CH1 Inverted)", "modal1_ch1", "modal1_ch2", "INV", "NORM", 1.2, 1.2},
  {"Mode 4 (47k-94k Hz, CH1 Inverted)", "modal2_ch1", "modal2_ch2", "INV", "NORM", 1.2, 1.2}
};

// 波形數據現在從 waveform_data.h 載入
// 包含實際的 2000 點波形數據

bool keysight_connected = false;
int current_mode = -1;

void setup() {
  Serial.begin(115200);
  
  Serial.println("=== Teensy 4.1 Keysight 33600A Controller ===");
  Serial.println("Hardware: Teensy 4.1 → USB Host → Keysight 33600A");
  Serial.println("No PC or VISA required for operation!");
  Serial.println();
  
  // 初始化 USB Host
  Serial.println("Initializing USB Host...");
  myusb.begin();
  
  // 等待 Keysight 連接
  Serial.println("Waiting for Keysight 33600A USB connection...");
  Serial.println("Please connect: Teensy USB Host ←→ USB A-B Cable ←→ Keysight");
  
  unsigned long startTime = millis();
  while (!keysight_connected && (millis() - startTime < 30000)) { // 30秒超時
    myusb.Task();
    if (userial) {
      keysight_connected = true;
      Serial.println("✅ Keysight 33600A connected successfully!");
      
      // 初始化設備
      initializeKeysight();
      break;
    }
    
    // 每5秒顯示一次等待訊息
    if ((millis() - startTime) % 5000 == 0) {
      Serial.println("Still waiting for Keysight connection...");
    }
    delay(100);
  }
  
  if (!keysight_connected) {
    Serial.println("❌ Keysight connection timeout!");
    Serial.println("Please check:");
    Serial.println("1. USB Host cable connection");
    Serial.println("2. Keysight power and USB settings");
    Serial.println("3. Cable integrity");
    while(1) delay(1000); // 停止執行
  }
  
  showMenu();
}

// 按鈕接腳定義
const int BUTTON_MODE1 = 2;
const int BUTTON_MODE2 = 3;
const int BUTTON_MODE3 = 4;
const int BUTTON_MODE4 = 5;
const int BUTTON_SHUTDOWN = 6;

// 按鈕狀態
bool lastButtonState[5] = {HIGH, HIGH, HIGH, HIGH, HIGH};
unsigned long lastDebounceTime[5] = {0, 0, 0, 0, 0};
const unsigned long debounceDelay = 50;

void setupButtons() {
  pinMode(BUTTON_MODE1, INPUT_PULLUP);
  pinMode(BUTTON_MODE2, INPUT_PULLUP);
  pinMode(BUTTON_MODE3, INPUT_PULLUP);
  pinMode(BUTTON_MODE4, INPUT_PULLUP);
  pinMode(BUTTON_SHUTDOWN, INPUT_PULLUP);
  
  Serial.println("Physical buttons configured:");
  Serial.println("Pin 2 = Mode 1, Pin 3 = Mode 2, Pin 4 = Mode 3");
  Serial.println("Pin 5 = Mode 4, Pin 6 = Shutdown");
}

void loop() {
  myusb.Task();
  
  // 檢查實體按鈕（獨立運行時使用）
  checkButtons();
  
  // 檢查串口輸入（連接電腦時使用）
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input == "1" || input == "2" || input == "3" || input == "4") {
      int mode = input.toInt() - 1;
      runMode(mode);
    } else if (input == "5") {
      shutdownKeysight();
      Serial.println("System shutdown");
      while(1) delay(1000);
    } else if (input == "menu") {
      showMenu();
    } else {
      Serial.println("Invalid input! Type 'menu' to see options.");
    }
  }
  
  delay(10);
}

void checkButtons() {
  int buttons[] = {BUTTON_MODE1, BUTTON_MODE2, BUTTON_MODE3, BUTTON_MODE4, BUTTON_SHUTDOWN};
  
  for (int i = 0; i < 5; i++) {
    int reading = digitalRead(buttons[i]);
    
    if (reading != lastButtonState[i]) {
      lastDebounceTime[i] = millis();
    }
    
    if ((millis() - lastDebounceTime[i]) > debounceDelay) {
      if (reading == LOW) { // 按鈕被按下（因為使用 INPUT_PULLUP）
        switch (i) {
          case 0: runMode(0); break; // Mode 1
          case 1: runMode(1); break; // Mode 2
          case 2: runMode(2); break; // Mode 3
          case 3: runMode(3); break; // Mode 4
          case 4: 
            shutdownKeysight();
            Serial.println("System shutdown via button");
            while(1) delay(1000);
            break;
        }
        delay(500); // 防止重複觸發
      }
    }
    
    lastButtonState[i] = reading;
  }
}

void initializeKeysight() {
  Serial.println("Initializing Keysight 33600A...");
  
  // 查詢設備ID
  sendSCPI("*IDN?");
  delay(100);
  String response = readSCPI();
  Serial.println("Connected to: " + response);
  
  // 初始設定
  sendSCPI("OUTP1 OFF");
  sendSCPI("OUTP2 OFF");
  sendSCPI("MMEMORY:MDIR \"INT:\\remoteAdded\"");
  sendSCPI("FORM:BORD SWAP");
  
  Serial.println("Keysight initialization complete!");
}

void runMode(int mode_num) {
  if (mode_num < 0 || mode_num > 3) {
    Serial.println("Invalid mode number!");
    return;
  }
  
  current_mode = mode_num;
  ModeConfig& mode = modes[mode_num];
  
  Serial.println("\n=== Switching to " + String(mode.name) + " ===");
  
  // 關閉輸出
  sendSCPI("OUTP1 OFF");
  sendSCPI("OUTP2 OFF");
  
  // 關閉追蹤功能
  sendSCPI("SOUR2:TRACK OFF");
  delay(100);
  
  // 上傳波形數據
  uploadWaveform(1, mode_num * 2);     // CH1
  uploadWaveform(2, mode_num * 2 + 1); // CH2
  
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
  
  // 清除顯示
  sendSCPI("DISP:TEXT ''");
  
  Serial.println("✅ " + String(mode.name) + " activated!");
  Serial.println("✅ Sync Internal (Track On) enabled");
  
  // 設定實體按鈕
  setupButtons();
  
  showMenu();
}

void uploadWaveform(int channel, int waveform_index) {
  Serial.println("Uploading waveform to Channel " + String(channel) + "...");
  
  // 使用實際的波形數據
  const WaveformInfo& wf = waveform_info[waveform_index];
  String waveform_name = "MODAL_CH" + String(channel);
  
  // 清除數據
  sendSCPI("SOUR" + String(channel) + ":DATA:VOL:CLE");
  
  // 上傳波形數據
  String cmd = "SOUR" + String(channel) + ":DATA:ARB " + waveform_name + ",";
  sendSCPI(cmd);
  
  // 發送二進制數據
  sendBinaryData(wf.data, wf.length);
  
  // 儲存波形
  sendSCPI("MMEM:STOR:DATA \"INT:\\remoteAdded\\" + waveform_name + ".arb\"");
  
  Serial.println("   - Uploaded " + String(wf.length) + " points");
  delay(100);
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
  
  // 計算基頻
  float frequency = wf.sample_rate / wf.length;
  sendSCPI("SOUR" + ch + ":FREQ " + String(frequency, 2));
  sendSCPI("SOUR" + ch + ":PHAS 0");
  
  Serial.println("   - Channel " + ch + " configured: " + String(frequency, 2) + " Hz");
}

void setupSyncInternal() {
  Serial.println("Setting up Sync Internal (Track On)...");
  
  sendSCPI("SOUR1:TRACK OFF");
  sendSCPI("SOUR2:TRACK OFF");
  sendSCPI("SOUR2:TRACK ON");
  
  delay(100);
  
  sendSCPI("SOUR2:PHAS:SYNC");
  sendSCPI("SOUR2:PHAS 0");
  
  Serial.println("   - Channel 2 now tracks Channel 1");
}

void shutdownKeysight() {
  Serial.println("Shutting down Keysight outputs...");
  sendSCPI("OUTP1 OFF");
  sendSCPI("OUTP2 OFF");
  sendSCPI("SOUR2:TRACK OFF");
}

void sendSCPI(String command) {
  if (userial) {
    userial.println(command);
    userial.flush();
    
    if (DEBUG_MODE) {
      Serial.println("SCPI → " + command);
    }
  } else {
    Serial.println("❌ Error: Keysight not connected!");
  }
}

String readSCPI() {
  String response = "";
  unsigned long timeout = millis() + 1000; // 1秒超時
  
  while (millis() < timeout) {
    if (userial.available()) {
      response = userial.readStringUntil('\n');
      response.trim();
      break;
    }
    delay(1);
  }
  
  return response;
}

void sendBinaryData(const float* data, int length) {
  // 實作二進制數據傳輸
  // 根據 SCPI 協議格式化二進制數據
  if (userial) {
    for (int i = 0; i < length; i++) {
      userial.write((uint8_t*)&data[i], sizeof(float));
    }
    userial.flush();
    
    if (DEBUG_MODE) {
      Serial.println("Binary data sent: " + String(length) + " points");
    }
  }
}

void showMenu() {
  Serial.println("\n" + String('=', 50));
  Serial.println("Select Mode:");
  Serial.println("1 - Mode 1 (25k-50k Hz, CH1:Normal, CH2:Inverted)");
  Serial.println("2 - Mode 2 (47k-94k Hz, CH1:Normal, CH2:Inverted)");
  Serial.println("3 - Mode 3 (25k-50k Hz, CH1:Inverted, CH2:Normal)");
  Serial.println("4 - Mode 4 (47k-94k Hz, CH1:Inverted, CH2:Normal)");
  Serial.println("5 - Shutdown");
  Serial.println("Type 'menu' to show this menu again");
  Serial.print("Enter choice (1-5): ");
}
