#!/usr/bin/env python
"""
將CSV波形數據轉換為C語言數組格式
用於Teensy 4.1程式
"""

import csv
import numpy as np
import os

def convert_csv_to_c_array(csv_file, array_name, output_file):
    """將CSV文件轉換為C數組"""
    
    print(f"Converting {csv_file} to C array...")
    
    # 讀取CSV數據
    times = []
    values = []
    
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # 跳過標題行
        for row in reader:
            if len(row) >= 2:  # 確保有兩列數據
                times.append(float(row[0]))
                values.append(float(row[1]))
    
    values = np.array(values)
    
    # 使用原始數據，不做正規化處理
    
    # 生成C數組代碼
    c_code = f"// Generated from {csv_file}\n"
    c_code += f"// Original points: {len(values)}, Sample rate: {1.0/np.mean(np.diff(times)):.0f} Hz\n"
    c_code += f"const float {array_name}[] = {{\n"
    
    # 每行8個數值
    for i in range(0, len(values), 8):
        line_values = values[i:i+8]
        line = "  " + ", ".join([f"{v:.6f}f" for v in line_values])
        if i + 8 < len(values):
            line += ","
        c_code += line + "\n"
    
    c_code += "};\n"
    c_code += f"const int {array_name}_length = {len(values)};\n"
    c_code += f"const float {array_name}_sample_rate = {1.0/np.mean(np.diff(times)):.0f};\n\n"
    
    # 寫入文件
    with open(output_file, 'a') as f:
        f.write(c_code)
    
    print(f"   - Generated {len(values)} points")
    print(f"   - Sample rate: {1.0/np.mean(np.diff(times)):.0f} Hz")
    print(f"   - Appended to {output_file}")

def main():
    """主程式：轉換所有模態波形文件"""
    
    print("=== CSV to C Array Converter ===")
    print("Converting modal waveform files for Teensy 4.1...")
    
    # 輸出文件
    output_file = "waveform_data.h"
    
    # 清空輸出文件
    with open(output_file, 'w') as f:
        f.write("/*\n")
        f.write(" * Waveform Data for Teensy 4.1 Keysight Controller\n")
        f.write(" * Generated from CSV modal files\n")
        f.write(" */\n\n")
        f.write("#ifndef WAVEFORM_DATA_H\n")
        f.write("#define WAVEFORM_DATA_H\n\n")
    
    # 要轉換的文件列表
    files_to_convert = [
        ("modal/ONEPERIOD_A_25k_50k_84p88deg_2000pts.csv", "modal1_ch1_data"),
        ("modal/ONEPERIOD_B_25k_50k_264p88deg_2000pts.csv", "modal1_ch2_data"),
        ("modal/ONEPERIOD_C_47k_94k_57p32deg_2000pts.csv", "modal2_ch1_data"),
        ("modal/ONEPERIOD_D_47k_94k_237p32deg_2000pts.csv", "modal2_ch2_data")
    ]
    
    # 轉換每個文件
    for csv_file, array_name in files_to_convert:
        if os.path.exists(csv_file):
            convert_csv_to_c_array(csv_file, array_name, output_file)
        else:
            print(f"Warning: {csv_file} not found!")
    
    # 添加結構定義
    with open(output_file, 'a') as f:
        f.write("// Waveform structure definitions\n")
        f.write("struct WaveformInfo {\n")
        f.write("  const float* data;\n")
        f.write("  int length;\n")
        f.write("  float sample_rate;\n")
        f.write("};\n\n")
        
        f.write("// Waveform data array\n")
        f.write("const WaveformInfo waveform_info[] = {\n")
        f.write("  {modal1_ch1_data, modal1_ch1_data_length, modal1_ch1_data_sample_rate},\n")
        f.write("  {modal1_ch2_data, modal1_ch2_data_length, modal1_ch2_data_sample_rate},\n")
        f.write("  {modal2_ch1_data, modal2_ch1_data_length, modal2_ch1_data_sample_rate},\n")
        f.write("  {modal2_ch2_data, modal2_ch2_data_length, modal2_ch2_data_sample_rate}\n")
        f.write("};\n\n")
        
        f.write("#endif // WAVEFORM_DATA_H\n")
    
    print(f"\n✅ Conversion complete! Output saved to {output_file}")
    print("You can now include this file in your Teensy project.")

if __name__ == "__main__":
    main()
