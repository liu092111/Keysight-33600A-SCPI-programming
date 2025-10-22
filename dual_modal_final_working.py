#!/usr/bin/env python

import pyvisa as visa
import numpy as np
import csv
import time

def load_waveform_dat(filename):
    """讀取 DAT 波形文件"""
    times = []
    values = []
    
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    t = float(parts[0])
                    v = float(parts[1])
                    times.append(t)
                    values.append(v)
                except ValueError:
                    continue
    
    return np.array(times), np.array(values)

def align_waveforms(file1, file2, invert_ch2=True):
    """讀取並對齊波形 - 不進行任何標準化"""
    times1, values1 = load_waveform_dat(file1)
    times2, values2 = load_waveform_dat(file2)
    
    t_start = max(times1[0], times2[0])
    t_end = min(times1[-1], times2[-1])
    
    dt1 = np.mean(np.diff(times1))
    dt2 = np.mean(np.diff(times2))
    dt_unified = min(dt1, dt2)
    
    unified_times = np.arange(t_start, t_end + dt_unified, dt_unified)
    
    # 直接使用原始值，不做標準化
    aligned_values1 = np.interp(unified_times, times1, values1)
    aligned_values2 = np.interp(unified_times, times2, values2)
    
    if invert_ch2:
        aligned_values2 = -aligned_values2
    
    sRate = 1 / dt_unified
    
    return (aligned_values1.astype('f4'), aligned_values2.astype('f4'), 
            sRate, len(unified_times))

def clear_instrument_memory(inst):
    """清理儀器記憶體"""
    print("Clearing instrument memory...")
    inst.write('SOUR1:DATA:VOL:CLE')
    inst.write('SOUR2:DATA:VOL:CLE')
    inst.write('*WAI')

def reset_instrument_completely(inst):
    """完全重置儀器狀態"""
    print("Resetting instrument...")
    inst.write('OUTP1 OFF')
    inst.write('OUTP2 OFF')
    inst.write('SOUR1:TRACK OFF')
    inst.write('SOUR2:TRACK OFF')
    inst.write('*WAI')
    
    # 重置波形函數為預設
    inst.write('SOUR1:FUNC SIN')
    inst.write('SOUR2:FUNC SIN')
    inst.write('SOUR1:FREQ 1000')
    inst.write('SOUR2:FREQ 1000')
    inst.write('SOUR1:VOLT 0.1')
    inst.write('SOUR2:VOLT 0.1')
    inst.write('OUTP1:POL NORM')
    inst.write('OUTP2:POL NORM')
    inst.write('*WAI')
    
    # 清理自定義波形
    clear_instrument_memory(inst)

def preload_all_waveforms(inst):
    """預載入所有波形"""
    print("Loading waveforms...")
    clear_instrument_memory(inst)
    
    # 模式配置 - Mode 1 和 Mode 3 使用相同波形，Mode 2 和 Mode 4 使用相同波形
    modes_config = {
        1: {
            'file1': 'modal/25k_50k_84p88deg_2000pts.dat',
            'file2': 'modal/25k_50k_264p88deg_2000pts.dat',
            'name1': 'WF_25K_84',
            'name2': 'WF_25K_264'
        },
        2: {
            'file1': 'modal/47k_94k_57p32deg_2000pts.dat',
            'file2': 'modal/47k_94k_237p32deg_2000pts.dat',
            'name1': 'WF_47K_57',
            'name2': 'WF_47K_237'
        },
        3: {
            'file1': 'modal/25k_50k_84p88deg_2000pts.dat',
            'file2': 'modal/25k_50k_264p88deg_2000pts.dat',
            'name1': 'WF_25K_84',  # 與 Mode 1 使用相同名稱
            'name2': 'WF_25K_264'  # 與 Mode 1 使用相同名稱
        },
        4: {
            'file1': 'modal/47k_94k_57p32deg_2000pts.dat',
            'file2': 'modal/47k_94k_237p32deg_2000pts.dat',
            'name1': 'WF_47K_57',  # 與 Mode 2 使用相同名稱
            'name2': 'WF_47K_237'  # 與 Mode 2 使用相同名稱
        }
    }
    
    inst.write('OUTP1 OFF')
    inst.write('OUTP2 OFF')
    inst.write('*WAI')
    
    sampling_rates = {}
    
    for mode_num, config in modes_config.items():
        print(f"Loading Mode {mode_num}...")
        
        try:
            sig1, sig2, sRate, points = align_waveforms(
                config['file1'], config['file2'], invert_ch2=True
            )
            
            freq = sRate / points
            
            sampling_rates[mode_num] = {
                'sRate': sRate,
                'points': points,
                'freq': freq,
                'name1': config['name1'],
                'name2': config['name2']
            }
            
            # 上傳 Channel 1 波形
            print(f"  Uploading CH1: {config['name1']}")
            inst.write_binary_values(f'SOUR1:DATA:ARB {config["name1"]},', sig1, datatype='f', is_big_endian=False)
            inst.write('*WAI')
            
            # 上傳 Channel 2 波形
            print(f"  Uploading CH2: {config['name2']}")
            inst.write_binary_values(f'SOUR2:DATA:ARB {config["name2"]},', sig2, datatype='f', is_big_endian=False)
            inst.write('*WAI')
            
            print(f"  Mode {mode_num} loaded - Freq: {freq:.1f} Hz")
            
        except Exception as e:
            print(f"  Error loading Mode {mode_num}: {e}")
    
    print("All waveforms loaded!")
    return sampling_rates

def switch_mode(inst, mode_num, sampling_rates):
    """切換模式"""
    if mode_num not in sampling_rates:
        print(f"Mode {mode_num} not available!")
        return None
        
    start_time = time.time()
    
    # 極性配置
    if mode_num == 1:
        ch1_polarity = 'NORM'
        ch2_polarity = 'INV'
    elif mode_num == 2:
        ch1_polarity = 'NORM'
        ch2_polarity = 'INV'
    elif mode_num == 3:
        ch1_polarity = 'INV'
        ch2_polarity = 'NORM'
    else:  # mode_num == 4
        ch1_polarity = 'INV'
        ch2_polarity = 'NORM'
    
    mode_data = sampling_rates[mode_num]
    
    # 關閉輸出
    inst.write('OUTP1 OFF')
    inst.write('OUTP2 OFF')
    inst.write('*WAI')
    
    # 設定 Channel 1
    inst.write('SOUR1:FUNC ARB')
    inst.write(f'SOUR1:FUNC:ARB {mode_data["name1"]}')
    inst.write(f'SOUR1:FUNC:ARB:SRAT {mode_data["sRate"]:.0f}')
    inst.write('SOUR1:VOLT 1.2')
    inst.write('SOUR1:VOLT:OFFS 0')
    inst.write(f'SOUR1:FREQ {mode_data["freq"]}')
    inst.write('SOUR1:PHAS 0')
    
    # 設定 Channel 2
    inst.write('SOUR2:FUNC ARB')
    inst.write(f'SOUR2:FUNC:ARB {mode_data["name2"]}')
    inst.write(f'SOUR2:FUNC:ARB:SRAT {mode_data["sRate"]:.0f}')
    inst.write('SOUR2:VOLT 1.2')
    inst.write('SOUR2:VOLT:OFFS 0')
    inst.write(f'SOUR2:FREQ {mode_data["freq"]}')
    inst.write('SOUR2:PHAS 0')
    inst.write('*WAI')
    
    # 設定同步
    inst.write('SOUR1:TRACK OFF')
    inst.write('SOUR2:TRACK OFF')
    inst.write('SOUR2:TRACK ON')
    inst.write('SOUR2:PHAS:SYNC')
    inst.write('*WAI')
    
    # 設定極性 (必須在開啟輸出前設定)
    inst.write(f'OUTP1:POL {ch1_polarity}')
    inst.write(f'OUTP2:POL {ch2_polarity}')
    inst.write('*WAI')
    
    # 開啟輸出
    inst.write('OUTP1 ON')
    inst.write('OUTP2 ON')
    inst.write('*WAI')
    
    switch_time = (time.time() - start_time) * 1000
    
    print(f"Mode {mode_num} | {switch_time:.1f}ms | Freq: {mode_data['freq']:.1f} Hz | CH1={ch1_polarity}, CH2={ch2_polarity}")
    
    return mode_data['freq']

if __name__ == "__main__":
    print("Dual Modal Controller - Fixed Version")
    print("Connecting...")
    
    rm = visa.ResourceManager()
    inst = rm.open_resource('USB0::0x0957::0x5707::MY59001615::0::INSTR')
    
    try:
        inst.control_ren(6)
    except:
        pass
    
    # 完全重置儀器
    reset_instrument_completely(inst)
    
    # 初始化
    print("Initializing...")
    inst.write('*CLS')
    inst.write('*WAI')
    
    try:
        sampling_rates = preload_all_waveforms(inst)
        if not sampling_rates:
            print("ERROR: No waveforms loaded!")
            reset_instrument_completely(inst)
            inst.close()
            exit(1)
        else:
            print(f"Successfully loaded {len(sampling_rates)} mode(s)")
            
            # **修復問題1: 自動載入預設模式 (Mode 1)**
            print("\nAuto-loading default Mode 1...")
            switch_mode(inst, 1, sampling_rates)
            
    except Exception as e:
        print(f"Error: {e}")
        reset_instrument_completely(inst)
        inst.close()
        exit(1)
    
    while True:
        try:
            available_modes = list(sampling_rates.keys())
            print(f"\nAvailable modes: {available_modes}")
            print("1-Mode1  2-Mode2  3-Mode3  4-Mode4  q-Quit")
            
            user_input = input("Select: ").strip().lower()
            
            if user_input in ['1', '2', '3', '4']:
                mode_num = int(user_input)
                if mode_num in sampling_rates:
                    freq = switch_mode(inst, mode_num, sampling_rates)
                else:
                    print(f"Mode {mode_num} is not available!")
                
            elif user_input == 'q':
                # **修復問題2: 完全清理儀器狀態**
                print("Cleaning up and exiting...")
                reset_instrument_completely(inst)
                inst.close()
                print("Exit complete!")
                break
                
            else:
                print("Invalid")
                
        except KeyboardInterrupt:
            print("\nCleaning up and exiting...")
            reset_instrument_completely(inst)
            inst.close()
            print("Exit complete!")
            break
        except Exception as e:
            print(f"Error: {e}")
            reset_instrument_completely(inst)
            inst.close()
            break
