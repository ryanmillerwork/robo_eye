## Robo Eye Controller

This project drives a pair of fake eyes using an Adafruit ESP32-S2 Reverse TFT board with a PCA9685 Servo FeatherWing. It offers multiple simultaneous control surfaces:

- A built-in touchscreen UI with the hardware buttons on the ESP32-S2.
- A USB serial command interface so a laptop or Android device can issue scripted eye motions.
- A browser-based console (Web Serial) for logging, quick commands, and freehand eye steering.

### Hardware

- `Adafruit Feather ESP32-S2 Reverse TFT` (runs CircuitPython 10.x, provides display + USB serial)
- `Adafruit 8-Channel Servo FeatherWing (PCA9685)` (handles four servos)
- `EMAX ES08MA II 12g Mini Servos` (two per eye: pan + tilt)
- Power via USB-C on the Feather. Servos draw power from the FeatherWing (ensure adequate 5 V supply if you extend the build).

### Firmware Overview

The firmware lives in `micropython controller/code.py`. Key features:

- Predefined 9-point gaze matrix (UL, UC, UR, …, LR) with adjustable distance.
- Menu system for selecting target eye(s) and range, plus zeroing both eyes.
- USB serial parser running alongside the UI loop, so external commands do not interrupt the built-in controls.

### On-Device UI

- Buttons:
  - `D2` (top button): short press cycles menu sections; press-and-hold (>0.6 s) to confirm selection.
  - `D1` (middle button): cycle within the options of the current section.
  - `D0` (boot button): select/activate the highlighted option.
- Screen shows three sections:
  - `9-pt`: choose a direction; pressing select moves the targeted eyes there.
  - `Zero`: centers all servos.
  - `Settings`: select which eye(s) respond (`L`, `R`, `B` both) and the distance (degrees) applied in 9-pt moves.
- Status line continuously displays each eye’s current pan/tilt in degrees.

### USB Serial Command Interface

The board stays responsive to button input while it also listens for newline-terminated commands over USB serial (115200 baud). You can use:

- **macOS/Linux**: `mpremote connect /dev/cu.usbmodemXXXX repl` or `screen /dev/cu.usbmodemXXXX 115200`
- **Windows**: any serial terminal on the assigned COM port.
- **Android**: Termux with `pyserial`, or the “Serial USB Terminal” app via USB OTG.

Available commands (case-insensitive):

1. **9-point shortcuts**  
   Send one of `UL UC UR L C R LL LC LR`. Example:
   ```
   UR
   ```
   Response: `CMD OK 9PT UR` or an error message if the move failed.

2. **Saccade command**  
   `SAC <left_pan> <left_tilt> <right_pan> <right_tilt>`  
   Values are floats in degrees. Use any of `X`, `H`, `HOLD`, `SKIP`, `KEEP`, or `NC` to leave an axis unchanged. Example:
   ```
   SAC 10 -5 X X
   ```
   Moves the left eye to +10° pan / -5° tilt while keeping the right eye where it is. Successful responses include the applied angles:  
   `CMD OK SAC 10.0 -5.0 0.0 0.0`

Serial responses always start with `CMD OK` or `CMD ERR` so host scripts can parse them easily.

### Web UI (Browser Serial Console)

Located in `micropython_controller/web_ui/index.html`. Features:

- Connect/disconnect via Chrome/Edge Web Serial dialog.
- Scrollback log showing board output plus `CMD OK/ERR` responses.
- Command input box and quick logging of manual entries.
- Pointer pad that maps the full square to ±20° pan/tilt. Click or drag to stream `SAC` commands for both eyes (throttled to one command per 100 ms). Includes a toggle to swap left/right pan directions if you want mirrored motion.

Usage tips:

1. Serve the folder locally (`cd micropython_controller/web_ui && python -m http.server 8000`) and open `http://localhost:8000` in Chrome.
2. Click **Connect**, pick the ESP32 device, then use the pointer pad or text box to drive the eyes.
3. You can also open the HTML directly from the board’s CIRCUITPY drive in Chrome (needs Web Serial support).

### Development Notes

- The firmware depends on CircuitPython libraries: `adafruit_display_text`, `adafruit_pca9685`, and their transitive requirements. Install them on the board’s `lib/` directory.
- After copying `code.py` to the device, it boots directly into the UI loop. You no longer need to break into the REPL for remote control thanks to the serial parser.
- To soft reboot the board (e.g., after editing), press `Ctrl-D` in `mpremote` or tap the reset button.

### Roadmap Ideas

- Add scripted sequences triggered over serial (e.g., play from JSON/YAML).
- Expose the same command set over Wi-Fi (TCP or WebSockets) for wireless control.
- Create a desktop CLI wrapper that remembers common gaze positions and timings.

