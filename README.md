# Keysight 33600A Dual Modal Selector

A Python-based control system for the Keysight 33600A arbitrary waveform generator, featuring dual-channel modal waveform selection with both command-line and GUI interfaces.

## 🚀 Features

- **4 Operation Modes**: Forward, Right, Backward, Left directional control
- **Dual Channel Control**: Independent channel configuration with polarity control
- **GUI Interface**: Clean, keyboard-like directional control interface
- **Command Line Interface**: Full-featured terminal-based control
- **Sync Internal**: Automatic channel synchronization (Track On functionality)
- **Real-time Control**: Start/Pause/Stop functionality
- **Auto-connection**: Automatic device detection and connection

## 📋 Requirements

- Python 3.7+
- PyVISA
- NumPy
- Tkinter (for GUI)
- Keysight 33600A Arbitrary Waveform Generator

## 🔧 Installation

1. Clone this repository:
```bash
git clone https://github.com/liu092111/Keysight-33600A-SCPI-programming.git
cd Keysight-33600A-SCPI-programming
```

2. Install required packages:
```bash
pip install pyvisa numpy
```

3. Ensure your Keysight 33600A is connected via USB.

## 🎮 Usage

### GUI Version (Recommended)
```bash
python selector_gui.py
```

The GUI provides a clean, keyboard-like interface with directional arrows:
- **▲** Forward (Mode 1)
- **►** Right (Mode 2) 
- **▼** Backward (Mode 3)
- **◄** Left (Mode 4)
- **START/PAUSE** Central control
- **STOP ALL** Emergency stop

### Command Line Version
```bash
python dual_modal_selector_4modes.py
```

## 📊 Operation Modes

### Mode 1 - Forward (25k-50k Hz)
- **Channel 1**: Normal polarity
- **Channel 2**: Inverted polarity
- **Frequency Range**: 25kHz - 50kHz
- **Waveform Files**: `25k_50k_84p88deg_2000pts.dat`, `25k_50k_264p88deg_2000pts.dat`

![Mode 1](img/mode%201.JPG)

### Mode 2 - Right (47k-94k Hz)
- **Channel 1**: Normal polarity
- **Channel 2**: Inverted polarity
- **Frequency Range**: 47kHz - 94kHz
- **Waveform Files**: `47k_94k_57p32deg_2000pts.dat`, `47k_94k_237p32deg_2000pts.dat`

![Mode 2](img/mode%202.JPG)

### Mode 3 - Backward (25k-50k Hz)
- **Channel 1**: Inverted polarity
- **Channel 2**: Normal polarity
- **Frequency Range**: 25kHz - 50kHz
- **Waveform Files**: `25k_50k_84p88deg_2000pts.dat`, `25k_50k_264p88deg_2000pts.dat`

### Mode 4 - Left (47k-94k Hz)
- **Channel 1**: Inverted polarity
- **Channel 2**: Normal polarity
- **Frequency Range**: 47kHz - 94kHz
- **Waveform Files**: `47k_94k_57p32deg_2000pts.dat`, `47k_94k_237p32deg_2000pts.dat`

## 📁 File Structure

```
├── selector_gui.py                    # Simple GUI version (recommended)
├── dual_modal_selector_4modes.py     # Command-line 4-mode version
├── run_dual_modal_selector_2modes.py # Original 2-mode version
├── run_dual_modal.py                 # Basic dual modal script
├── run_dual_modal2.py                # Alternative dual modal script
├── modal/                            # Waveform data files
│   ├── 25k_50k_84p88deg_2000pts.dat
│   ├── 25k_50k_264p88deg_2000pts.dat
│   ├── 47k_94k_57p32deg_2000pts.dat
│   ├── 47k_94k_237p32deg_2000pts.dat
│   └── *.csv                         # Additional waveform data
├── img/                              # Documentation images
│   ├── mode 1.JPG
│   └── mode 2.JPG
└── README.md
```

## ⚙️ Technical Details

### Waveform Processing
- **Time Alignment**: Automatic synchronization of dual waveform files
- **Sampling Rate**: Unified sampling rate calculation for optimal performance
- **Signal Normalization**: Automatic amplitude normalization
- **Phase Synchronization**: Channel 2 automatically tracks Channel 1

### Device Configuration
- **Output Voltage**: 2.0V amplitude
- **Offset**: 0V
- **Sync Output**: Enabled with Channel 1 as source
- **Track Mode**: Channel 2 tracks Channel 1 frequency and phase

### Safety Features
- **Auto-disconnect**: Safe device disconnection on program exit
- **Error Handling**: Comprehensive error messages and recovery
- **Output Control**: Independent start/pause/stop functionality

## 🔌 Hardware Setup

1. Connect Keysight 33600A via USB cable
2. Ensure device is powered on and recognized by the system
3. Run the program - it will automatically detect and connect to the device

## 🐛 Troubleshooting

### Connection Issues
- Verify USB connection
- Check device power status
- Ensure no other software is using the device
- Try reconnecting the USB cable

### Waveform Loading Issues
- Verify all `.dat` files are present in the `modal/` directory
- Check file permissions
- Ensure sufficient disk space

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Note**: This software is designed specifically for the Keysight 33600A Arbitrary Waveform Generator. Compatibility with other models is not guaranteed.
