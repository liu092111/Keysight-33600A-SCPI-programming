#!/usr/bin/env python

import tkinter as tk
from tkinter import messagebox
import pyvisa as visa
import numpy as np
import csv
import threading

class SimpleModalSelectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dual Modal Selector")
        self.root.geometry("300x350")
        self.root.resizable(False, False)
        
        # Device connection status
        self.inst = None
        self.connected = False
        self.current_mode = None
        self.is_running = False
        
        # Create GUI elements
        self.create_widgets()
        
        # Auto connect device
        self.connect_device()
    
    def create_widgets(self):
        # Connection status
        self.status_label = tk.Label(self.root, text="Status: Disconnected", 
                                    font=("Arial", 10), fg="red")
        self.status_label.pack(pady=10)
        
        # Direction control frame
        self.direction_frame = tk.Frame(self.root)
        self.direction_frame.pack(pady=30)
        
        # Forward button (▲)
        self.forward_btn = tk.Button(self.direction_frame, text="▲", 
                                    font=("Arial", 16), width=3, height=1,
                                    command=lambda: self.select_mode(1))
        self.forward_btn.grid(row=0, column=1, padx=3, pady=3)
        
        # Left button (◄)
        self.left_btn = tk.Button(self.direction_frame, text="◄", 
                                 font=("Arial", 16), width=3, height=1,
                                 command=lambda: self.select_mode(4))
        self.left_btn.grid(row=1, column=0, padx=3, pady=3)
        
        # Pause/Start button
        self.pause_btn = tk.Button(self.direction_frame, text="START", 
                                  font=("Arial", 10, "bold"), width=5, height=1,
                                  command=self.toggle_output)
        self.pause_btn.grid(row=1, column=1, padx=3, pady=3)
        
        # Right button (►)
        self.right_btn = tk.Button(self.direction_frame, text="►", 
                                  font=("Arial", 16), width=3, height=1,
                                  command=lambda: self.select_mode(2))
        self.right_btn.grid(row=1, column=2, padx=3, pady=3)
        
        # Backward button (▼)
        self.backward_btn = tk.Button(self.direction_frame, text="▼", 
                                     font=("Arial", 16), width=3, height=1,
                                     command=lambda: self.select_mode(3))
        self.backward_btn.grid(row=2, column=1, padx=3, pady=3)
        
        # Current mode display
        self.mode_label = tk.Label(self.root, text="Mode: None", 
                                  font=("Arial", 12))
        self.mode_label.pack(pady=20)
        
        # Stop button
        self.stop_btn = tk.Button(self.root, text="STOP ALL", 
                                 font=("Arial", 10, "bold"), 
                                 command=self.stop_all_outputs)
        self.stop_btn.pack(pady=10)
        
        # Initial state
        self.update_button_states()
    
    def connect_device(self):
        """Connect to Keysight 33600A device"""
        try:
            self.status_label.config(text="Status: Connecting...", fg="orange")
            self.root.update()
            
            rm = visa.ResourceManager()
            self.inst = rm.open_resource('USB0::0x0957::0x5707::MY59001615::0::INSTR')
            
            try:
                self.inst.control_ren(6)
            except:
                pass
            
            # Test connection
            device_id = self.inst.query('*IDN?').strip()
            
            # Initialize device
            self.inst.write('OUTP1 OFF')
            self.inst.write('OUTP2 OFF')
            self.inst.write("MMEMORY:MDIR \"INT:\\remoteAdded\"")
            self.inst.write('FORM:BORD SWAP')
            
            self.connected = True
            self.status_label.config(text="Status: Connected", fg="green")
            self.update_button_states()
            
        except Exception as e:
            self.connected = False
            self.status_label.config(text="Status: Connection Failed", fg="red")
            self.update_button_states()
    
    def select_mode(self, mode_num):
        """Select and configure mode"""
        if not self.connected:
            messagebox.showwarning("Warning", "Please connect device first!")
            return
        
        # Stop current output if running
        if self.is_running:
            self.stop_all_outputs()
        
        # Run mode configuration in background thread
        threading.Thread(target=self._run_mode_thread, args=(mode_num,), daemon=True).start()
    
    def _run_mode_thread(self, mode_num):
        """Execute mode configuration in background thread"""
        try:
            # Update GUI status
            mode_names = {1: "Forward", 2: "Right", 3: "Backward", 4: "Left"}
            self.root.after(0, lambda: self.mode_label.config(text=f"Mode: Setting {mode_names[mode_num]}..."))
            
            # Execute mode configuration
            freq = self.run_mode(mode_num)
            self.current_mode = mode_num
            
            # Update GUI
            self.root.after(0, lambda: self.mode_label.config(text=f"Mode: {mode_names[mode_num]}"))
            self.root.after(0, lambda: self.pause_btn.config(text="PAUSE"))
            self.root.after(0, lambda: setattr(self, 'is_running', True))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Mode setup failed:\n{str(e)}"))
            self.root.after(0, lambda: self.mode_label.config(text="Mode: Setup Failed"))
    
    def toggle_output(self):
        """Toggle output on/off"""
        if not self.connected:
            messagebox.showwarning("Warning", "Please connect device first!")
            return
        
        if not self.current_mode:
            messagebox.showwarning("Warning", "Please select a mode first!")
            return
        
        try:
            if self.is_running:
                # Pause output
                self.inst.write('OUTP1 OFF')
                self.inst.write('OUTP2 OFF')
                self.pause_btn.config(text="START")
                self.is_running = False
            else:
                # Start output
                self.inst.write('OUTP1 ON')
                self.inst.write('OUTP2 ON')
                self.pause_btn.config(text="PAUSE")
                self.is_running = True
                
        except Exception as e:
            messagebox.showerror("Error", f"Output control failed:\n{str(e)}")
    
    def stop_all_outputs(self):
        """Stop all outputs"""
        if not self.connected:
            return
        
        try:
            self.inst.write('OUTP1 OFF')
            self.inst.write('OUTP2 OFF')
            self.inst.write('SOUR2:TRACK OFF')
            self.is_running = False
            self.pause_btn.config(text="START")
            self.mode_label.config(text="Mode: Stopped")
            
        except Exception as e:
            messagebox.showerror("Error", f"Stop output failed:\n{str(e)}")
    
    def update_button_states(self):
        """Update button states"""
        state = tk.NORMAL if self.connected else tk.DISABLED
        
        self.forward_btn.config(state=state)
        self.left_btn.config(state=state)
        self.right_btn.config(state=state)
        self.backward_btn.config(state=state)
        self.pause_btn.config(state=state)
        self.stop_btn.config(state=state)
    
    def exit_program(self):
        """Exit program"""
        if self.connected:
            try:
                self.inst.write('OUTP1 OFF')
                self.inst.write('OUTP2 OFF')
                self.inst.write('SOUR2:TRACK OFF')
                self.inst.close()
            except:
                pass
        
        self.root.quit()
        self.root.destroy()
    
    # Core functionality from original program
    def load_waveform_with_time(self, filename):
        """Load waveform file and return time and value data"""
        times = []
        values = []
        
        with open(filename, 'r') as f:
            reader = csv.reader(f, delimiter=' ')
            for t, p in reader:
                times.append(float(t))
                values.append(float(p))
        
        return np.array(times), np.array(values)
    
    def align_waveforms(self, file1, file2, invert_ch2=True):
        """Load and align two waveform files"""
        times1, values1 = self.load_waveform_with_time(file1)
        times2, values2 = self.load_waveform_with_time(file2)
        
        # Find common time range
        t_start = max(times1[0], times2[0])
        t_end = min(times1[-1], times2[-1])
        
        # Calculate unified sampling rate
        dt1 = np.mean(np.diff(times1))
        dt2 = np.mean(np.diff(times2))
        dt_unified = min(dt1, dt2)
        
        # Create unified time axis
        unified_times = np.arange(t_start, t_end + dt_unified, dt_unified)
        
        # Interpolate to unified time axis
        aligned_values1 = np.interp(unified_times, times1, values1)
        aligned_values2 = np.interp(unified_times, times2, values2)
        
        # Normalize signals
        aligned_values1 = aligned_values1 / max(np.abs(aligned_values1))
        aligned_values2 = aligned_values2 / max(np.abs(aligned_values2))
        
        # Invert Channel 2 if needed
        if invert_ch2:
            aligned_values2 = -aligned_values2
        
        # Calculate sampling rate
        sRate = str(1 / dt_unified)
        
        return (aligned_values1.astype('f4'), aligned_values2.astype('f4'), 
                sRate, len(unified_times), unified_times)
    
    def setup_sync_internal(self):
        """Setup Sync Internal (Track On) functionality"""
        self.inst.write('SOUR1:TRACK OFF')
        self.inst.write('SOUR2:TRACK OFF')
        self.inst.write('SOUR2:TRACK ON')
        self.inst.write('*WAI')
    
    def run_mode(self, mode_num):
        """Execute specified mode waveform output"""
        
        # Select waveform files and polarity settings based on mode
        if mode_num == 1:  # Forward
            file1 = 'modal/25k_50k_84p88deg_2000pts.dat'
            file2 = 'modal/25k_50k_264p88deg_2000pts.dat'
            ch1_polarity = 'NORM'
            ch2_polarity = 'INV'
        elif mode_num == 2:  # Right
            file1 = 'modal/47k_94k_57p32deg_2000pts.dat'
            file2 = 'modal/47k_94k_237p32deg_2000pts.dat'
            ch1_polarity = 'NORM'
            ch2_polarity = 'INV'
        elif mode_num == 3:  # Backward
            file1 = 'modal/25k_50k_84p88deg_2000pts.dat'
            file2 = 'modal/25k_50k_264p88deg_2000pts.dat'
            ch1_polarity = 'INV'
            ch2_polarity = 'NORM'
        else:  # mode_num == 4, Left
            file1 = 'modal/47k_94k_57p32deg_2000pts.dat'
            file2 = 'modal/47k_94k_237p32deg_2000pts.dat'
            ch1_polarity = 'INV'
            ch2_polarity = 'NORM'
        
        # Turn off outputs
        self.inst.write('OUTP1 OFF')
        self.inst.write('OUTP2 OFF')
        
        # Turn off tracking function
        self.inst.write('SOUR2:TRACK OFF')
        self.inst.write('*WAI')
        
        # Load and align waveforms
        sig1, sig2, sRate, points, unified_times = self.align_waveforms(file1, file2, invert_ch2=True)
        
        # Upload Channel 1 waveform
        self.inst.write('SOUR1:DATA:VOL:CLE')
        self.inst.write_binary_values('SOUR1:DATA:ARB MODAL_84DEG,', sig1, datatype='f', is_big_endian=False)
        self.inst.write('*WAI')
        self.inst.write('MMEM:STOR:DATA "INT:\\remoteAdded\\MODAL_84DEG.arb"')
        
        # Upload Channel 2 waveform
        self.inst.write('SOUR2:DATA:VOL:CLE')
        self.inst.write_binary_values('SOUR2:DATA:ARB MODAL_264DEG,', sig2, datatype='f', is_big_endian=False)
        self.inst.write('*WAI')
        self.inst.write('MMEM:STOR:DATA "INT:\\remoteAdded\\MODAL_264DEG.arb"')
        
        # Configure dual channel parameters
        # Configure Channel 1
        self.inst.write('SOUR1:FUNC ARB')
        self.inst.write('SOUR1:FUNC:ARB MODAL_84DEG')
        self.inst.write('SOUR1:FUNC:ARB:SRAT ' + sRate)
        self.inst.write('SOUR1:VOLT 2.0')
        self.inst.write('SOUR1:VOLT:OFFS 0')
        
        # Configure Channel 2
        self.inst.write('SOUR2:FUNC ARB')
        self.inst.write('SOUR2:FUNC:ARB MODAL_264DEG')
        self.inst.write('SOUR2:FUNC:ARB:SRAT ' + sRate)
        self.inst.write('SOUR2:VOLT 2.0')
        self.inst.write('SOUR2:VOLT:OFFS 0')
        
        # Set basic frequency and phase
        freq = float(sRate) / points
        self.inst.write(f'SOUR1:FREQ {freq}')
        self.inst.write(f'SOUR2:FREQ {freq}')
        self.inst.write('SOUR1:PHAS 0')
        self.inst.write('SOUR2:PHAS 0')
        self.inst.write('*WAI')
        
        # Setup Sync Internal (Track On)
        self.setup_sync_internal()
        
        # Synchronize Channel 2 phase to Channel 1
        self.inst.write('SOUR2:PHAS:SYNC')
        self.inst.write('SOUR2:PHAS 0')
        self.inst.write('*WAI')
        
        # Set channel polarity based on mode
        self.inst.write(f'OUTP1:POL {ch1_polarity}')
        self.inst.write(f'OUTP2:POL {ch2_polarity}')
        
        # Setup sync output
        self.inst.write('OUTP:SYNC ON')
        self.inst.write('OUTP:SYNC:SOURCE CH1')
        self.inst.write('OUTP:SYNC:MODE MARK')
        
        # Enable both channel outputs
        self.inst.write('OUTP1 ON')
        self.inst.write('OUTP2 ON')
        self.inst.write('*WAI')
        
        return freq

def main():
    root = tk.Tk()
    app = SimpleModalSelectorGUI(root)
    
    # Set close event
    root.protocol("WM_DELETE_WINDOW", app.exit_program)
    
    root.mainloop()

if __name__ == "__main__":
    main()
