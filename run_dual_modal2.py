#!/usr/bin/env python

import pyvisa as visa
import numpy as np
import csv

print("=== 雙通道模態波形上傳與輸出 ===")

def load_waveform_with_time(filename):
    """讀取波形文件並返回時間和數值數據"""
    times = []
    values = []
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line:  # 跳過空行
                parts = line.split()
                if len(parts) >= 2:  # 確保有至少兩個值
                    try:
                        times.append(float(parts[0]))
                        values.append(float(parts[1]))
                    except ValueError as e:
                        print(f"警告：無法解析行 '{line}': {e}")
                        continue
    
    return np.array(times), np.array(values)

def align_waveforms(file1, file2, invert_ch2=True):
    """讀取兩個波形檔案並對齊時間軸"""
    print(f"   讀取檔案 1: {file1}")
    times1, values1 = load_waveform_with_time(file1)
    
    print(f"   讀取檔案 2: {file2}")
    times2, values2 = load_waveform_with_time(file2)
    
    # 檢查數據是否有效
    if len(times1) == 0 or len(values1) == 0:
        raise ValueError(f"檔案 {file1} 沒有有效數據")
    if len(times2) == 0 or len(values2) == 0:
        raise ValueError(f"檔案 {file2} 沒有有效數據")
    
    print(f"   檔案 1: {len(times1)} 點, 時間範圍: {times1[0]:.6f} - {times1[-1]:.6f} 秒")
    print(f"   檔案 2: {len(times2)} 點, 時間範圍: {times2[0]:.6f} - {times2[-1]:.6f} 秒")
    
    # 找到共同的時間範圍
    t_start = max(times1[0], times2[0])
    t_end = min(times1[-1], times2[-1])
    
    if t_start >= t_end:
        raise ValueError("兩個檔案沒有共同的時間範圍")
    
    print(f"   共同時間範圍: {t_start:.6f} - {t_end:.6f} 秒")
    
    # 計算統一的採樣率（使用較高的採樣率）
    dt1 = np.mean(np.diff(times1))
    dt2 = np.mean(np.diff(times2))
    dt_unified = min(dt1, dt2)  # 使用較小的時間間隔（較高採樣率）
    
    if dt_unified <= 0:
        raise ValueError("無效的採樣間隔")
    
    print(f"   檔案 1 採樣間隔: {dt1:.8f} 秒")
    print(f"   檔案 2 採樣間隔: {dt2:.8f} 秒")
    print(f"   統一採樣間隔: {dt_unified:.8f} 秒")
    
    # 創建統一的時間軸
    unified_times = np.arange(t_start, t_end + dt_unified, dt_unified)
    
    # 插值到統一時間軸
    aligned_values1 = np.interp(unified_times, times1, values1)
    aligned_values2 = np.interp(unified_times, times2, values2)
    
    # 檢查是否有零值（避免除零錯誤）
    max_abs1 = max(np.abs(aligned_values1))
    max_abs2 = max(np.abs(aligned_values2))
    
    # 注釋掉正規化（和 4modes 版本保持一致）
    # if max_abs1 == 0:
    #     print("警告：檔案 1 的所有值都是零，無法正規化")
    #     aligned_values1 = aligned_values1  # 保持原值
    # else:
    #     aligned_values1 = aligned_values1 / max_abs1
    
    # if max_abs2 == 0:
    #     print("警告：檔案 2 的所有值都是零，無法正規化")
    #     aligned_values2 = aligned_values2  # 保持原值
    # else:
    #     aligned_values2 = aligned_values2 / max_abs2
    
    # *** 對 Channel 2 進行反相 ***
    if invert_ch2:
        aligned_values2 = -aligned_values2
        print("   - Channel 2 波形數據已反相")
    
    # 計算採樣率
    sRate = str(1 / dt_unified)
    
    print(f"   對齊後: {len(unified_times)} 點, 採樣率: {sRate} Hz")
    
    return (aligned_values1.astype('f4'), aligned_values2.astype('f4'), 
            sRate, len(unified_times), unified_times)

def setup_sync_internal(inst):
    """設定 Sync Internal (Track On) 功能"""
    print("正在設定 Sync Internal (Track On)...")
    
    # 先確保兩個通道都關閉追蹤
    inst.write('SOUR1:TRACK OFF')
    inst.write('SOUR2:TRACK OFF')
    
    # 讓 Channel 2 追蹤 Channel 1 (這就是 Sync Internal 的核心)
    inst.write('SOUR2:TRACK ON')
    
    # 可選：明確指定追蹤類型
    # inst.write('SOUR2:TRACK:FREQ ON')   # 追蹤頻率
    # inst.write('SOUR2:TRACK:PHASE ON')  # 追蹤相位
    
    inst.write('*WAI')
    print("   - Channel 2 現在會自動追蹤 Channel 1 的頻率和相位變化")
    print("   - 這等同於前端面板的 'Sync Internal' 功能")

print("\n=== Mode 2 (47k-94k Hz) - 雙通道模態波形輸出 ===")

try:
    # 統一電壓設定
    ch1_voltage = 1.2  # Channel 1 電壓
    ch2_voltage = 1.2  # Channel 2 電壓

    # 讀取並對齊波形 (Channel 2 反相)
    print("正在讀取並對齊模態波形文件...")
    sig1, sig2, sRate, points, unified_times = align_waveforms(
        'modal/47k_94k_57p32deg_2000pts.dat',
        'modal/47k_94k_237p32deg_2000pts.dat',
        invert_ch2=True
    )

    # 連接設備
    print("正在連接設備...")
    rm = visa.ResourceManager()
    inst = rm.open_resource('USB0::0x0957::0x5707::MY59001615::0::INSTR')

    try:
        inst.control_ren(6)
    except:
        pass

    print(f"已連接到: {inst.query('*IDN?').strip()}")

    # 確保輸出關閉
    inst.write('OUTP1 OFF')
    inst.write('OUTP2 OFF')

    # 設定目錄
    inst.write("MMEMORY:MDIR \"INT:\\remoteAdded\"")
    inst.write('FORM:BORD SWAP')

    # 重要：先關閉追蹤功能，以便獨立配置每個通道
    inst.write('SOUR2:TRACK OFF')
    inst.write('*WAI')

    # 上傳 Channel 1 波形
    print("正在上傳 Channel 1 波形...")
    inst.write("DISP:TEXT 'Uploading CH1 Modal'")
    inst.write('SOUR1:DATA:VOL:CLE')
    inst.write_binary_values('SOUR1:DATA:ARB MODAL_57DEG,', sig1, datatype='f', is_big_endian=False)
    inst.write('*WAI')
    inst.write('MMEM:STOR:DATA "INT:\\remoteAdded\\MODAL_57DEG.arb"')

    # 上傳 Channel 2 波形
    print("正在上傳 Channel 2 波形...")
    inst.write("DISP:TEXT 'Uploading CH2 Modal'")
    inst.write('SOUR2:DATA:VOL:CLE')
    inst.write_binary_values('SOUR2:DATA:ARB MODAL_237DEG,', sig2, datatype='f', is_big_endian=False)
    inst.write('*WAI')
    inst.write('MMEM:STOR:DATA "INT:\\remoteAdded\\MODAL_237DEG.arb"')

    # 配置雙通道參數（但保持輸出關閉）
    print("正在配置雙通道參數...")

    # 配置 Channel 1 參數
    inst.write('SOUR1:FUNC ARB')
    inst.write('SOUR1:FUNC:ARB MODAL_57DEG')
    inst.write('SOUR1:FUNC:ARB:SRAT ' + sRate)
    inst.write(f'SOUR1:VOLT {ch1_voltage}')
    inst.write('SOUR1:VOLT:OFFS 0')

    # 配置 Channel 2 參數
    inst.write('SOUR2:FUNC ARB')
    inst.write('SOUR2:FUNC:ARB MODAL_237DEG')
    inst.write('SOUR2:FUNC:ARB:SRAT ' + sRate)
    inst.write(f'SOUR2:VOLT {ch2_voltage}')
    inst.write('SOUR2:VOLT:OFFS 0')

    # 設置基本頻率和相位
    freq = float(sRate) / points
    inst.write(f'SOUR1:FREQ {freq}')
    inst.write(f'SOUR2:FREQ {freq}')
    inst.write('SOUR1:PHAS 0')
    inst.write('SOUR2:PHAS 0')
    inst.write('*WAI')

    # *** 新增：設定 Sync Internal (Track On) ***
    setup_sync_internal(inst)

    # 讓 Channel 2 同步到 Channel 1 的相位
    print("正在同步 Channel 2 相位到 Channel 1...")
    inst.write('SOUR2:PHAS:SYNC')    # Channel 2 同步到 Channel 1
    inst.write('SOUR2:PHAS 0')       # Channel 2 相位設為 0
    inst.write('*WAI')
    print("   - Channel 2 已同步到 Channel 1")

    # 在 Track 設定完成後，設定通道極性 (Mode 2: CH1=NORM, CH2=INV)
    print("正在設定通道極性...")
    inst.write('OUTP1:POL NORM')  # Channel 1 極性: Normal
    inst.write('OUTP2:POL INV')   # Channel 2 極性: Inverted
    print("   - Channel 1 極性: NORM, Channel 2 極性: INV")

    # 設定同步輸出（可選）
    print("正在設定同步輸出...")
    inst.write('OUTP:SYNC ON')           # 啟用同步輸出
    inst.write('OUTP:SYNC:SOURCE CH1')   # 同步信號來自 Channel 1
    inst.write('OUTP:SYNC:MODE MARK')    # 同步模式為標記

    # 最後同時啟用兩個通道輸出
    print("正在啟用雙通道輸出...")
    inst.write('OUTP1 ON')
    inst.write('OUTP2 ON')
    inst.write('*WAI')

    # 清除顯示信息
    inst.write("DISP:TEXT ''")

    # 驗證 Track 狀態
    try:
        track_status = inst.query('SOUR2:TRACK?')
        print(f"   - Channel 2 Track 狀態: {'ON' if track_status.strip() == '1' else 'OFF'}")
    except:
        print("   - 無法查詢 Track 狀態")

    print(f"✅ Mode 2 (47k-94k Hz) 已啟用！基頻: {freq:.2f} Hz")
    print("✅ Sync Internal (Track On) 已啟用")

    inst.close()

    print("\n=== 完成！===")
    print("你的 Agilent 33622A 現在正在雙通道同步輸出模態波形：")
    print(f"- Channel 1: 57.32度相位模態波形 (Normal)")
    print(f"- Channel 2: 237.32度相位模態波形 (Inverted)")
    print(f"- 基頻: {freq:.2f} Hz")
    print("- Channel 2 自動追蹤 Channel 1 (Sync Internal)")

except FileNotFoundError as e:
    print(f"\n❌ 錯誤：找不到檔案 - {e}")
    print("請確認以下檔案存在：")
    print("- modal/47k_94k_57p32deg_2000pts.dat")
    print("- modal/47k_94k_237p32deg_2000pts.dat")

except ValueError as e:
    print(f"\n❌ 數據錯誤：{e}")
    print("請檢查數據檔案格式是否正確")

except visa.VisaIOError as e:
    print(f"\n❌ 設備連接錯誤：{e}")
    print("請確認：")
    print("- Agilent 33622A 已連接並開機")
    print("- USB 驅動程式已正確安裝")
    print("- 設備地址是否正確")

except Exception as e:
    print(f"\n❌ 未預期的錯誤：{e}")
    print("請檢查所有設定並重試")
    # 嘗試關閉設備連接
    try:
        if 'inst' in locals():
            inst.close()
    except:
        pass

finally:
    # 確保資源被正確釋放
    try:
        if 'inst' in locals():
            inst.close()
        if 'rm' in locals():
            rm.close()
    except:
        pass
