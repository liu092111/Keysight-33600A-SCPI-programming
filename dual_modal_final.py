#!/usr/bin/env python

import pyvisa as visa
import numpy as np
import csv
import time

def load_waveform_csv(filename):
    """讀取 CSV 波形文件"""
    times = []
    values = []
    
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # 跳過標題行
        for row in reader:
            if len(row) >= 2:
                try:
                    times.append(float(row[0]))
                    values.append(float(row[1]))
                except ValueError:
                    continue
    
    return np.array(times), np.array(values)

def load_waveform_dat(filename):
    """讀取 DAT 波形文件"""
    times = []
    values = []
    
    with open(filename, 'r') as f:
        reader = csv.reader(f, delimiter=' ')
        for t, p in reader:
            times.append(float(t))
            values.append(float(p))
    
    return np.array(times), np.array(values)

def align_waveforms(file1, file2, use_csv=False, invert_ch2=True):
    """讀取並對齊波形"""
    if use_csv:
        times1, values1 = load_waveform_csv(file1)
        times2, values2 = load_waveform_csv(file2)
    else:
        times1, values1 = load_waveform_dat(file1)
        times2, values2 = load_waveform_dat(file2)
    
    t_start = max(times1[0], times2[0])
    t_end = min(times1[-1], times2[-1])
    
    dt1 = np.mean(np.diff(times1))
    dt2 = np.mean(np.diff(times2))
    dt_unified = min(dt1, dt2)
    
    unified_times = np.arange(t_start, t_end + dt_unified, dt_unified)
    
    aligned_values1 = np.interp(unified_times, times1, values1)
    aligned_values2 = np.interp(unified_times, times2, values2)
    
    if invert_ch2:
        aligned_values2 = -aligned_values2
    
    sRate = str(1 / dt_unified)
    
    return (aligned_values1.astype('f4'), aligned_values2.astype('f4'), 
            sRate, len(unified_times), unified_times)

def setup_sync_internal(inst):
    """設定 Sync Internal"""
    inst.write('SOUR1:TRACK OFF')
    inst.write('SOUR2:TRACK OFF')
    inst.write('SOUR2:TRACK ON')
    inst.write('*WAI')

def clear_instrument_memory(inst):
    """清理儀器記憶體中的所有舊波形"""
    print("Clearing instrument memory...")
    
    # 嘗試刪除各種可能的舊檔案名稱
    old_files = [
        'MODAL_84DEG.arb', 'MODAL_264DEG.arb',
        'MODAL_57DEG.arb', 'MODAL_237DEG.arb',
        'M1_84DEG.arb', 'M1_264DEG.arb',
        'M2_57DEG.arb', 'M2_237DEG.arb', 
        'M3_84DEG.arb', 'M3_264DEG.arb',
        'M4_57DEG.arb', 'M4_237DEG.arb',
        'M1_84DEG_NEW.arb', 'M1_264DEG_NEW.arb',
        'M2_57DEG_NEW.arb', 'M2_237DEG_NEW.arb',
        'M3_84DEG_NEW.arb', 'M3_264DEG_NEW.arb',
        'M4_57DEG_NEW.arb', 'M4_237DEG_NEW.arb'
    ]
    
    for filename in old_files:
        try:
            inst.write(f'MMEM:DEL "INT:\\remoteAdded\\{filename}"')
        except:
            pass
    
    # 清除揮發性記憶體
    try:
        inst.write('SOUR1:DATA:VOL:CLE')
        inst.write('SOUR2:DATA:VOL:CLE')
        inst.write('*WAI')
    except:
        pass

def preload_all_waveforms(inst):
    """預載入所有波形"""
    
    # 先徹底清理記憶體
    clear_instrument_memory(inst)
    
    print("Loading waveforms...")
    
    modes_config = {
        1: {
            'file1': 'modal/25k_50k_84p88deg_2000pts.dat',
            'file2': 'modal/25k_50k_264p88deg_2000pts.dat',
            'name1': 'M1_84DEG',
            'name2': 'M1_264DEG',
            'use_csv': False
        },
        2: {
            'file1': 'modal/47k_94k_57p32deg_2000pts.dat',
            'file2': 'modal/47k_94k_237p32deg_2000pts.dat',
            'name1': 'M2_57DEG',
            'name2': 'M2_237DEG',
            'use_csv': False
        },
        3: {
            'file1': 'modal/25k_50k_84p88deg_2000pts.dat',
            'file2': 'modal/25k_50k_264p88deg_2000pts.dat',
            'name1': 'M3_84DEG',
            'name2': 'M3_264DEG',
            'use_csv': False
        },
        4: {
            'file1': 'modal/47k_94k_57p32deg_2000pts.dat',
            'file2': 'modal/47k_94k_237p32deg_2000pts.dat',
            'name1': 'M4_57DEG',
            'name2': 'M4_237DEG',
            'use_csv': False
        }
    }
    
    # 確保輸出關閉和基本設定
    inst.write('OUTP1 OFF')
    inst.write('OUTP2 OFF')
    inst.write('SOUR1:TRACK OFF')
    inst.write('SOUR2:TRACK OFF')
    inst.write('*WAI')
    
    inst.write("MMEMORY:MDIR \"INT:\\remoteAdded\"")
    inst.write('FORM:BORD SWAP')
    inst.write('*WAI')
    
    sampling_rates = {}
    
    for mode_num, config in modes_config.items():
        print(f"Loading Mode {mode_num}...")
        
        sig1, sig2, sRate, points, unified_times = align_waveforms(
            config['file1'], config['file2'], 
            use_csv=config['use_csv'], invert_ch2=True
        )
        
        sampling_rates[mode_num] = {
            'sRate': sRate,
            'points': points,
            'freq': float(sRate) / points,
            'name1': config['name1'],
            'name2': config['name2']
        }
        
        # 上傳 Channel 1 波形
        inst.write('SOUR1:DATA:VOL:CLE')
        inst.write('*WAI')
        inst.write_binary_values(f'SOUR1:DATA:ARB {config["name1"]},', sig1, datatype='f', is_big_endian=False)
        inst.write('*WAI')
        inst.write(f'MMEM:STOR:DATA "INT:\\remoteAdded\\{config["name1"]}.arb"')
        inst.write('*WAI')
        
        # 上傳 Channel 2 波形
        inst.write('SOUR2:DATA:VOL:CLE')
        inst.write('*WAI')
        inst.write_binary_values(f'SOUR2:DATA:ARB {config["name2"]},', sig2, datatype='f', is_big_endian=False)
        inst.write('*WAI')
        inst.write(f'MMEM:STOR:DATA "INT:\\remoteAdded\\{config["name2"]}.arb"')
        inst.write('*WAI')
    
    print("Ready")
    return sampling_rates

def fast_switch_mode(inst, mode_num, sampling_rates):
    """快速切換模式"""
    start_time = time.time()
    
    ch1_voltage = 1.2
    ch2_voltage = 1.2
    
    if mode_num == 1:
        ch1_polarity = 'NORM'
        ch2_polarity = 'INV'
    elif mode_num == 2:
        ch1_polarity = 'NORM'
        ch2_polarity = 'INV'
    elif mode_num == 3:
        ch1_polarity = 'INV'
        ch2_polarity = 'NORM'
    else:
        ch1_polarity = 'INV'
        ch2_polarity = 'NORM'
    
    mode_data = sampling_rates[mode_num]
    
    inst.write('OUTP1 OFF')
    inst.write('OUTP2 OFF')
    inst.write('SOUR2:TRACK OFF')
    inst.write('*WAI')
    
    inst.write('SOUR1:FUNC ARB')
    inst.write(f'SOUR1:FUNC:ARB {mode_data["name1"]}')
    inst.write(f'SOUR1:FUNC:ARB:SRAT {mode_data["sRate"]}')
    inst.write(f'SOUR1:VOLT {ch1_voltage}')
    inst.write('SOUR1:VOLT:OFFS 0')
    
    inst.write('SOUR2:FUNC ARB')
    inst.write(f'SOUR2:FUNC:ARB {mode_data["name2"]}')
    inst.write(f'SOUR2:FUNC:ARB:SRAT {mode_data["sRate"]}')
    inst.write(f'SOUR2:VOLT {ch2_voltage}')
    inst.write('SOUR2:VOLT:OFFS 0')
    
    inst.write(f'SOUR1:FREQ {mode_data["freq"]}')
    inst.write(f'SOUR2:FREQ {mode_data["freq"]}')
    inst.write('SOUR1:PHAS 0')
    inst.write('SOUR2:PHAS 0')
    inst.write('*WAI')
    
    setup_sync_internal(inst)
    
    inst.write('SOUR2:PHAS:SYNC')
    inst.write('SOUR2:PHAS 0')
    inst.write('*WAI')
    
    inst.write(f'OUTP1:POL {ch1_polarity}')
    inst.write(f'OUTP2:POL {ch2_polarity}')
    
    inst.write('OUTP:SYNC ON')
    inst.write('OUTP:SYNC:SOURCE CH1')
    inst.write('OUTP:SYNC:MODE MARK')
    
    inst.write('OUTP1 ON')
    inst.write('OUTP2 ON')
    inst.write('*WAI')
    
    inst.write("DISP:TEXT ''")
    
    switch_time = (time.time() - start_time) * 1000
    
    print(f"Mode {mode_num} | {switch_time:.1f}ms")
    
    return mode_data['freq']

if __name__ == "__main__":
    print("Dual Modal Controller")
    print("Connecting...")
    
    rm = visa.ResourceManager()
    inst = rm.open_resource('USB0::0x0957::0x5707::MY59001615::0::INSTR')
    
    try:
        inst.control_ren(6)
    except:
        pass
    
    # 溫和的初始化 - 不重置設備
    print("Initializing...")
    inst.write('OUTP1 OFF')
    inst.write('OUTP2 OFF')
    inst.write('SOUR1:TRACK OFF')
    inst.write('SOUR2:TRACK OFF')
    inst.write('*WAI')
    
    # 清除錯誤但不重置
    inst.write('*CLS')
    inst.write('*WAI')
    
    try:
        sampling_rates = preload_all_waveforms(inst)
    except Exception as e:
        print(f"Error: {e}")
        inst.close()
        exit(1)
    
    while True:
        try:
            print("\n1-Mode1  2-Mode2  3-Mode3  4-Mode4  q-Quit")
            
            user_input = input("Select: ").strip().lower()
            
            if user_input in ['1', '2', '3', '4']:
                mode_num = int(user_input)
                freq = fast_switch_mode(inst, mode_num, sampling_rates)
                
            elif user_input == 'q':
                inst.write('OUTP1 OFF')
                inst.write('OUTP2 OFF')
                inst.write('SOUR2:TRACK OFF')
                inst.close()
                break
                
            else:
                print("Invalid")
                
        except KeyboardInterrupt:
            inst.write('OUTP1 OFF')
            inst.write('OUTP2 OFF')
            inst.write('SOUR2:TRACK OFF')
            inst.close()
            break
        except Exception as e:
            print(f"Error: {e}")
