# Teensy Ethernet Keysight Controller 優化說明

## 主要問題與解決方案

### 1. 重複建立連線問題 ❌ → ✅
**原問題**: 每次操作都可能重新連線，觸發 ARP/三向交握
**解決方案**: 
- 使用全域 `EthernetClient client` 持續維持連線
- 只在連線中斷時才重新連接
- 新增連線狀態監控

### 2. SCPI 指令缺少換行符 ❌ → ✅
**原問題**: 使用 `client.println()` 會送出 `\r\n`，但有些情況可能缺少 `\n`
**解決方案**:
- 所有 SCPI 指令確保以 `\n` 結尾
- 使用 `client.print()` 而非 `println()` 避免多餘的 `\r`
- 新增 `sendSCPIFast()` 函數自動添加 `\n`

### 3. DHCP/ARP 延遲問題 ❌ → ✅
**原問題**: 使用 APIPA (169.254.x.x) 和 DHCP 造成網路延遲
**解決方案**:
- 改用固定 IP 設定：
  - Teensy: `192.168.0.10`
  - Keysight: `192.168.0.21`
  - 子網路: `255.255.255.0`
- 避免 ARP 解析和 DHCP 租約延遲

### 4. W5500 重傳參數優化 ❌ → ✅
**原問題**: W5500 預設重傳時間過長，封包遺失時延遲爆增
**解決方案**:
- 重傳時間 (RTR): 2000ms → 200ms
- 重傳次數 (RCR): 保持 3 次
- 使用 `Ethernet.setRetransmissionTimeout(200)`

### 5. Nagle 演算法延遲 ❌ → ✅
**原問題**: 小封包被延遲合併，增加傳輸時間
**解決方案**:
- 啟用 `client.setNoDelay(true)` 關閉 Nagle 演算法
- 小封包立即發送，不等待合併

### 6. 指令分散發送效率低 ❌ → ✅
**原問題**: 每條 SCPI 指令單獨發送，增加網路往返次數
**解決方案**:
- 新增 `sendSCPIBatch()` 函數批次發送多條指令
- 初始化、配置、關閉等操作都使用批次指令
- 減少網路往返次數

## 新增功能

### 1. 執行時間監控
- `runModeOptimized()` 會顯示模式切換總耗時
- 幫助監控優化效果

### 2. 連線狀態檢查
- 新增 `showConnectionStatus()` 函數
- 顯示 Ethernet 連結、IP 地址、TCP 連線狀態

### 3. 波形上傳優化
- `uploadWaveformOptimized()` 分批上傳大型波形
- 每批 200 個點，避免緩衝區溢出
- 減少單次傳輸的資料量

### 4. 錯誤處理改進
- 所有 SCPI 函數都檢查連線狀態
- 連線中斷時自動標記並提示重連
- 重連機制有重試次數限制

## 預期效果

### 延遲改善
- **原版**: 10-20+ 秒
- **優化版**: 預期 < 2 秒

### 主要改善來源
1. **持續連線**: 省去重複 TCP 握手 (~1-3 秒)
2. **固定 IP**: 省去 DHCP/ARP 解析 (~2-5 秒)
3. **批次指令**: 減少網路往返 (~1-2 秒)
4. **W5500 優化**: 減少重傳延遲 (~2-10 秒)
5. **關閉 Nagle**: 減少小封包延遲 (~100-500ms)

## 使用說明

### 網路設定
1. 將 Keysight 33600A 設定為固定 IP: `192.168.0.21`
2. 確保 Teensy 和 Keysight 在同一網段
3. 如需修改 IP，請更改程式中的 `local_ip` 和 `keysight_ip`

### 新指令
- `s` 或 `status`: 顯示連線狀態
- `r` 或 `reconnect`: 手動重新連線
- `m` 或 `menu`: 顯示選單

### 除錯模式
- 設定 `DEBUG_MODE 1` 可顯示所有 SCPI 指令
- 正常使用建議保持 `DEBUG_MODE 0`

## 故障排除

### 如果仍有延遲
1. 檢查網路設定是否正確
2. 確認 Keysight IP 設定
3. 使用 `s` 指令檢查連線狀態
4. 嘗試 `r` 指令重新連線

### 連線問題
1. 檢查網路線連接
2. 確認 IP 地址沒有衝突
3. 檢查防火牆設定
4. 確認 Keysight SCPI 服務已啟用

### 波形上傳失敗
1. 檢查 `waveform_data.h` 檔案
2. 確認波形數據格式正確
3. 檢查 Keysight 記憶體空間

## 技術細節

### 批次指令格式
```cpp
String batch = "OUTP1 OFF\n"
               "OUTP2 OFF\n"
               "SOUR2:TRACK OFF\n";
sendSCPIBatch(batch);
```

### W5500 參數設定
```cpp
Ethernet.setRetransmissionTimeout(200);  // 200ms
Ethernet.setRetransmissionCount(3);      // 3次重試
```

### TCP_NODELAY 啟用
```cpp
client.setNoDelay(true);  // 關閉 Nagle 演算法
