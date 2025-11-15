# Robo Eye - Phidgets Servo Control System

Control system for servo-based eye movements using Phidgets AdvancedServo 8-Motor (1061) board.

## Quick Start

```bash
source ~/phidget21env/bin/activate
python test.py
```

---

## Hardware Setup Guide

Complete guide for controlling a **Phidgets AdvancedServo 8-Motor (1061)** from a **Raspberry Pi Zero**.

### ✅ Overview

* **Board:** Phidgets AdvancedServo 8-Motor (1061)
* **Library:** **Phidget 21** (the legacy "Phidget21" API, *not* Phidget 22)
* **Host:** Raspberry Pi Zero / Zero W running Raspberry Pi OS (Bookworm / Debian 12)
* **Language:** Python 3.11

---

## 1️⃣ Hardware

1. Power the 1061 with **6 – 15 V DC** on the screw-terminal input.
   (USB alone will not run servos.)
2. Plug servos into the 3-pin headers (white = signal, red = V+, black = GND).
3. Connect the board's **Mini-USB** to the Pi Zero's **USB-OTG** port using an **OTG adapter** or **powered hub**.
4. Confirm enumeration:

   ```bash
   lsusb
   ```

   You should see:
   ```
   Phidgets Inc 06c2:003a 8-Motor PhidgetAdvancedServo
   ```

---

## 2️⃣ Install Build Dependencies

```bash
sudo apt update
sudo apt install -y build-essential libusb-1.0-0-dev python3-dev unzip wget
```

---

## 3️⃣ Build & Install the C Runtime (libphidget21)

```bash
cd ~
wget https://www.phidgets.com/downloads/phidget21/libraries/linux/libphidget/libphidget_2.1.9.20190409.tar.gz
tar xf libphidget_2.1.9.20190409.tar.gz
cd libphidget_2.1.9.20190409
./configure --prefix=/usr
make
sudo make install
sudo ldconfig
```

This installs `libphidget21.so` plus the default udev rule.

---

## 4️⃣ Ensure udev Permissions

If you ever need to add it manually:

```bash
sudo tee /etc/udev/rules.d/99-phidgets.rules >/dev/null <<'EOF'
SUBSYSTEMS=="usb", ATTRS{idVendor}=="06c2", MODE="666"
EOF
sudo udevadm control --reload
sudo udevadm trigger
```

Then **unplug/re-plug** the board.

---

## 5️⃣ Install the Python Phidget21 Wrapper

```bash
cd ~
wget https://www.phidgets.com/downloads/phidget21/libraries/any/PhidgetsPython/PhidgetsPython_2.1.9.20220105.zip
unzip PhidgetsPython_2.1.9.20220105.zip -d PhidgetsPython
cd PhidgetsPython
python3 -m venv ~/phidget21env
source ~/phidget21env/bin/activate
pip install --upgrade pip wheel
python3 setup.py install
```

You should now have `Phidgets/` modules inside `~/phidget21env/lib/python3.11/site-packages/`.

Test the import:

```bash
python3 - <<'PY'
import Phidgets
from Phidgets.Devices.AdvancedServo import AdvancedServo
print("Phidget21 Python OK")
PY
```

---

## 6️⃣ Quick Motion Test

The `test.py` script provides a simple test:

```bash
source ~/phidget21env/bin/activate
python test.py
```

This will move servos on channels 0 and 1 through a simple motion sequence.

---

## 7️⃣ Troubleshooting Checklist

| Symptom                             | Likely cause / fix                                                           |
| ----------------------------------- | ---------------------------------------------------------------------------- |
| `PhidgetException 0x03 (Timed Out)` | Wrong library (Phidget22), or permissions—verify libphidget21 and udev.      |
| Works only with `sudo`              | udev rule missing—add `/etc/udev/rules.d/99-phidgets.rules`, reload, replug. |
| Servo doesn't move                  | No 6–15 V DC on power input. USB alone insufficient.                         |
| Random disconnects                  | Weak OTG cable / under-powered Pi Zero—use powered hub.                      |
| Import error                        | Not in virtualenv—`source ~/phidget21env/bin/activate`.                      |

---

## 8️⃣ Reference

* **Lib:** `libphidget21 2.1.9.20190409`
* **Python API:** `PhidgetsPython 2.1.9.20220105`
* **Device:** 1061 AdvancedServo 8-Motor (legacy, Phidget21 only)
* **USB VID:PID:** 06c2:003a
* **Docs:** [Phidgets 1061 Product Page](https://www.phidgets.com/?tier=3&catid=25&pcid=19&prodid=1061)

---

## Saccade Control System

The `saccade.py` script provides an interactive CLI for controlling servo-based saccadic eye movements.

### Features

- **Interactive REPL** - Stay connected and issue immediate commands
- **Motion Profiling** - Record position, velocity, and acceleration during movements
- **CSV Export** - Save profile data for analysis
- **Command History** - Use ↑/↓ arrow keys to navigate previous commands
- **Tab Completion** - Press Tab to autocomplete commands
- **Boundary Checking** - Automatic validation of position limits
- **Real-time Monitoring** - Observe servo positions as they move

### Coordinate System

- **X-axis (Pan)** - Servo 0, positive = right
- **Y-axis (Tilt)** - Servo 1, positive = up
- **Zero Position** - Default at (97°, 93°) absolute servo coordinates

### Running the Saccade Controller

```bash
source ~/phidget21env/bin/activate
python saccade.py
```

Optional arguments:
```bash
# Custom zero positions
python saccade.py --pan-zero 100 --tilt-zero 85

# Custom default dynamics
python saccade.py --acceleration 3000 --velocity 500
```

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `saccade <x> <y> [accel] [velocity]` | Perform saccade to position | `saccade 10 -5` |
| `profile <x> <y> [accel] [velocity]` | Profiled saccade (records motion) | `profile 20 10 3000 500` |
| `save [filename]` | Save last profile to CSV | `save my_saccade.csv` |
| `position` | Show current position | `position` |
| `limits` | Show servo position limits | `limits` |
| `zero` | Return to zero position | `zero` |
| `disengage` | Power off servos | `disengage` |
| `engage` | Power on servos | `engage` |
| `help` | Show help message | `help` |
| `quit` / `exit` | Exit program | `quit` |

### Motion Profiling

The profiling feature records motion data at 100 Hz and provides analysis:

```bash
saccade> profile 20 10
```

Output includes:
- Duration and sample count
- Final position and accuracy
- Peak velocity (actual vs commanded)
- Peak acceleration (90th percentile, smoothed)
- Average acceleration during main movement

Profile data is saved as CSV with columns:
- `time` - Time in seconds from start
- `pan_abs`, `tilt_abs` - Absolute servo positions
- `pan_rel`, `tilt_rel` - Positions relative to zero
- `pan_vel`, `tilt_vel` - Instantaneous velocities

### Default Parameters

Based on human saccade characteristics:
- **Max Velocity:** 400°/s (human range: 400-700°/s)
- **Acceleration:** 2000°/s² (conservative for servo hardware)

These can be overridden per-command or set as defaults at startup.

---

## Example Session

```bash
$ source ~/phidget21env/bin/activate
$ python saccade.py

============================================================
Saccade Control System - Interactive Mode
============================================================

Available commands:
  saccade <x> <y> [accel] [velocity]  - Perform saccade
  profile <x> <y> [accel] [velocity]  - Profiled saccade (records motion)
  save [filename]                      - Save last profile to CSV
  position                             - Show current position
  limits                               - Show servo position limits
  zero                                 - Return to zero position
  disengage                            - Power off servos
  engage                               - Power on servos
  help                                 - Show this help message
  quit / exit                          - Exit program

Defaults: accel=2000.0°/s², velocity=400.0°/s

Tip: Use ↑/↓ arrows for history, Tab for command completion
============================================================

saccade> limits

Servo Position Limits (Absolute):
  Pan (X):  0.0° to 180.0° (range: 180.0°)
  Tilt (Y): 0.0° to 180.0° (range: 180.0°)

Relative to Zero Position (Pan=97.0°, Tilt=93.0°):
  Pan (X):  -97.0° to 83.0° (left to right)
  Tilt (Y): -93.0° to 87.0° (down to up)

saccade> profile 20 10
Executing profiled saccade to (20.0°, 10.0°)
  Absolute positions: Pan=77.0°, Tilt=83.0°
  Acceleration: 2000.0°/s²
  Max velocity: 400.0°/s
  Sampling at 100 Hz
Saccade complete - captured 28 samples

============================================================
Motion Profile Analysis
============================================================
Duration: 285.3 ms
Samples: 28

Commanded:
  Target: (20.00°, 10.00°)
  Max velocity: 400.0°/s
  Acceleration: 2000.0°/s²

Actual:
  Final position: (20.01°, 9.98°)
  Position error: (0.01°, -0.02°)
  Peak pan velocity: 385.3°/s
  Peak tilt velocity: 192.7°/s
  Peak pan accel (90th %ile): 1950.2°/s²
  Avg pan accel: 1825.5°/s²
  Peak tilt accel (90th %ile): 1880.5°/s²
  Avg tilt accel: 1750.3°/s²

  Note: Velocity/acceleration estimated from position
        (smoothed with 5-point moving average)
============================================================

saccade> save
Profile data saved to: saccade_profile_20251111_143052.csv

saccade> quit
Exiting...
Connection closed
```

---

## Files

- **`saccade.py`** - Interactive saccade control system with profiling
- **`test.py`** - Simple servo motion test script
- **`README.md`** - This file

---

## ✅ Summary

After following the setup steps:

* `lsusb` shows **06c2:003a**
* `libphidget21.so` is installed and registered
* The **PhidgetsPython** wrapper imports successfully
* Running `test.py` moves servos on channels 0 and 1
* Running `saccade.py` provides full interactive control with profiling

Your Raspberry Pi Zero can now directly control the Phidgets 1061 board via Python.
