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

def align_waveforms(file1, file2):
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
    
    if max_abs1 == 0:
        print("警告：檔案 1 的所有值都是零，無法正規化")
        aligned_values1 = aligned_values1  # 保持原值
    else:
        aligned_values1 = aligned_values1 / max_abs1
    
    if max_abs2 == 0:
        print("警告：檔案 2 的所有值都是零，無法正規化")
        aligned_values2 = aligned_values2  # 保持原值
    else:
        aligned_values2 = aligned_values2 / max_abs2
    
    # 計算採樣率
    sRate = str(1 / dt_unified)
    
    print(f"   對齊後: {len(unified_times)} 點, 採樣率: {sRate} Hz")
    
    return (aligned_values1.astype('f4'), aligned_values2.astype('f4'), 
            sRate, len(unified_times), unified_times)

try:
    # 1. 讀取並對齊兩個模態波形
    print("1. 正在讀取並對齊模態波形文件...")

    # 對齊兩個波形檔案的時間軸
    sig1, sig2, sRate, points, unified_times = align_waveforms(
        'modal/47k_94k_57p32deg_2000pts.dat',
        'modal/47k_94k_237p32deg_2000pts.dat'
    )

    print(f"   時間對齊完成！")
    print(f"   統一後數據點數: {points}")
    print(f"   統一採樣率: {sRate} Hz")
    print(f"   時間軸範圍: {unified_times[0]:.6f} - {unified_times[-1]:.6f} 秒")

    # 2. 連接設備
    print("2. 正在連接設備...")
    rm = visa.ResourceManager()
    inst = rm.open_resource('USB0::0x0957::0x5707::MY59001615::0::INSTR')

    try:
        inst.control_ren(6)
    except:
        pass

    print(f"   已連接到: {inst.query('*IDN?').strip()}")

    # 3. 上傳 Channel 1 波形
    print("3. 正在上傳 Channel 1 波形...")
    inst.write("DISP:TEXT 'Uploading CH1 Modal'")
    inst.write("MMEMORY:MDIR \"INT:\\remoteAdded\"")
    inst.write('FORM:BORD SWAP')
    inst.write('SOUR1:DATA:VOL:CLE')
    inst.write_binary_values('SOUR1:DATA:ARB MODAL_84DEG,', sig1, datatype='f', is_big_endian=False)
    inst.write('*WAI')
    inst.write('MMEM:STOR:DATA "INT:\\remoteAdded\\MODAL_84DEG.arb"')
    print("   Channel 1 波形上傳完成！")

    # 4. 上傳 Channel 2 波形
    print("4. 正在上傳 Channel 2 波形...")
    inst.write("DISP:TEXT 'Uploading CH2 Modal'")
    inst.write('SOUR2:DATA:VOL:CLE')
    inst.write_binary_values('SOUR2:DATA:ARB MODAL_264DEG,', sig2, datatype='f', is_big_endian=False)
    inst.write('*WAI')
    inst.write('MMEM:STOR:DATA "INT:\\remoteAdded\\MODAL_264DEG.arb"')
    print("   Channel 2 波形上傳完成！")

    # 5. 配置雙通道輸出（時間對齊的波形）
    print("5. 正在配置雙通道輸出...")

    # 先關閉所有輸出
    inst.write('OUTP1 OFF')
    inst.write('OUTP2 OFF')

    # 配置 Channel 1
    inst.write('SOUR1:FUNC ARB')
    inst.write('SOUR1:FUNC:ARB MODAL_84DEG')
    inst.write('SOUR1:FUNC:ARB:SRAT ' + sRate)
    inst.write('SOUR1:VOLT 2.0')
    inst.write('SOUR1:VOLT:OFFS 0')

    # 配置 Channel 2
    inst.write('SOUR2:FUNC ARB')
    inst.write('SOUR2:FUNC:ARB MODAL_264DEG')
    inst.write('SOUR2:FUNC:ARB:SRAT ' + sRate)
    inst.write('SOUR2:VOLT 2.0')
    inst.write('SOUR2:VOLT:OFFS 0')

    # 6. 設置同步輸出
    print("6. 正在設置同步輸出...")

    # 設置相位為0（時間已對齊，不需要相位差）
    inst.write('SOUR1:PHAS 0')      # Channel 1 相位 0 度
    inst.write('SOUR2:PHAS 0')      # Channel 2 相位 0 度

    # 設置兩個通道使用相同的頻率
    freq = float(sRate) / points  # 計算基頻
    inst.write(f'SOUR1:FREQ {freq}')
    inst.write(f'SOUR2:FREQ {freq}')

    # 7. 啟用輸出
    print("7. 正在啟用輸出...")

    # 啟用兩個通道
    inst.write('OUTP1 ON')
    inst.write('OUTP2 ON')

    # 執行相位同步
    inst.write('SOUR:PHAS:SYNC')

    # 清除顯示信息
    inst.write("DISP:TEXT ''")

    print("   雙通道同步輸出已啟用！")
    print(f"   - Channel 1: MODAL_84DEG (時間對齊), 2.0V")
    print(f"   - Channel 2: MODAL_264DEG (時間對齊), 2.0V")
    print(f"   - 基頻: {freq:.2f} Hz")
    print("   - 兩個通道的時間軸已完全對齊")

    inst.close()

    print("\n=== 完成！===")
    print("你的 Agilent 33622A 現在正在雙通道同步輸出時間對齊的模態波形：")
    print(f"- Channel 1: 84.88度相位模態波形")
    print(f"- Channel 2: 264.88度相位模態波形")
    print(f"- 基頻: {freq:.2f} Hz")
    print("- 兩個通道的時間軸完全對齊，在示波器上會重複顯示")
    print("請檢查示波器上的兩個通道信號")

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
