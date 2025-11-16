import board
import displayio
import keypad
import supervisor
import sys
import terminalio
import time
from adafruit_display_text import label
from adafruit_pca9685 import PCA9685

# --- Servo controller state ---------------------------------------------------
SERVO_DEFAULT_STATUS = "Controller not found"
servo_status = SERVO_DEFAULT_STATUS
servo_controller = None
SERVO_FREQUENCY = 50
SERVO_RANGE_DEGREES = 45
SERVO_US_PER_DEGREE = 11

SERVO_CONFIG = [
    {
        "name": "Left pan",
        "eye": "L",
        "axis": "pan",
        "channel": 4,
        "zero_pulse_us": 1490,
        "direction": -1,  # increase is right
    },
    {
        "name": "Left tilt",
        "eye": "L",
        "axis": "tilt",
        "channel": 5,
        "zero_pulse_us": 1460,
        "direction": 1,  # increase is up
    },
    {
        "name": "Right pan",
        "eye": "R",
        "axis": "pan",
        "channel": 6,
        "zero_pulse_us": 1560,
        "direction": -1,  # increase is right
    },
    {
        "name": "Right tilt",
        "eye": "R",
        "axis": "tilt",
        "channel": 7,
        "zero_pulse_us": 1460,
        "direction": -1,  # increase is down
    },
]

EYE_KEYS = ("L", "R")
EYE_OPTIONS = ("L", "R", "B")
EYE_AXES = ("pan", "tilt")
eye_angles = {eye: {"pan": 0.0, "tilt": 0.0} for eye in EYE_KEYS}
eye_selection_index = EYE_OPTIONS.index("B")

SERVO_LOOKUP = {}
for servo in SERVO_CONFIG:
    SERVO_LOOKUP[(servo["eye"], servo["axis"])] = servo

NINE_POINT_VECTORS = {
    "UL": (-1, 1),
    "UC": (0, 1),
    "UR": (1, 1),
    "L": (-1, 0),
    "C": (0, 0),
    "R": (1, 0),
    "LL": (-1, -1),
    "LC": (0, -1),
    "LR": (1, -1),
}
POINT_DISTANCE_OPTIONS = (1, 5, 10, 20, 40)
point_distance_index = POINT_DISTANCE_OPTIONS.index(10)

# --- Input setup ------------------------------------------------------------
# D0 (BOOT) is pulled high and reads low when pressed.
boot_button = keypad.Keys(
    (board.D0,),
    value_when_pressed=False,
    pull=True,
)

# D1/D2 (labeled A/B on the TFT board) are pulled low and read high when pressed.
user_buttons = keypad.Keys(
    (board.D1, board.D2),
    value_when_pressed=True,
    pull=True,
)

BUTTON_GROUPS = (
    (boot_button, ("D0",)),
    (user_buttons, ("D1", "D2")),
)

D2_SELECT_HOLD_SECONDS = 0.6
d2_press_time = None

# --- Menu definition --------------------------------------------------------
MENU = [
    {
        "name": "9-pt",
        "options": ["UL", "UC", "UR", "L", "C", "R", "LL", "LC", "LR"],
        "row_length": 3,
        "default_option": "C",
    },
    {
        "name": "Zero",
        "options": [],
        "message": "Reset eye(s)\nto center",
    },
    {
        "name": "Settings",
        "options": ["Eye", "Range"],
        "row_length": 1,
        "default_option": 0,
    },
]

MENU_9PT_INDEX = 0

current_menu_index = 0
def default_option_index(section):
    options = section["options"]
    if not options:
        return None
    default_value = section.get("default_option")
    if default_value is None:
        return 0
    if isinstance(default_value, int):
        return default_value % len(options)
    if isinstance(default_value, str) and default_value in options:
        return options.index(default_value)
    return 0


current_option_indices = [
    default_option_index(section) for section in MENU
]
selected_option_indices = [
    default_option_index(section) for section in MENU
]

# --- Display setup ----------------------------------------------------------
display = board.DISPLAY
display.rotation = 180  # Upside-down orientation

root_group = displayio.Group()
display.root_group = root_group

screen_width = display.width
screen_height = display.height

MENU_COLOR = 0x888888
MENU_HIGHLIGHT_COLOR = 0xFFFFFF
OPTION_COLOR = 0x00FFFF
OPTION_HIGHLIGHT_COLOR = 0xFF8800
OPTION_SELECTED_COLOR = 0xFFFFFF
STATUS_COLOR = 0xAAAAAA
STATUS_CONNECTED_COLOR = 0x00FF00
STATUS_DISCONNECTED_COLOR = 0xFF0000
MENU_LABEL_SCALE = 2
OPTION_LABEL_SCALE = 2
OPTION_ROW_SPACING = 24

top_row_y = 2
menu_labels = []
for idx, section in enumerate(MENU):
    horizontal_fraction = (idx + 0.5) / len(MENU)
    anchored_x = int(horizontal_fraction * screen_width)
    menu_label = label.Label(
        terminalio.FONT,
        text=section["name"],
        color=MENU_COLOR,
        scale=MENU_LABEL_SCALE,
        anchor_point=(0.5, 0.0),
        anchored_position=(anchored_x, top_row_y),
    )
    menu_labels.append(menu_label)
    root_group.append(menu_label)

options_base_y = top_row_y + 36
options_group = displayio.Group()
root_group.append(options_group)

status_label = label.Label(
    terminalio.FONT,
    text="L: 0.0, 0.0  R: 0.0, 0.0",
    color=STATUS_COLOR,
    scale=1,
    anchor_point=(0.5, 1.0),
    anchored_position=(screen_width // 2, screen_height - 2),
)
root_group.append(status_label)


def format_eye_state(eye_key):
    state = eye_angles[eye_key]
    return f"{state['pan']:+.0f}°, {state['tilt']:+.0f}°"


def update_eye_status():
    status_label.text = f"L: {format_eye_state('L')}  R: {format_eye_state('R')}"


update_eye_status()


def connect_servo_controller(address=0x40, frequency=SERVO_FREQUENCY, i2c=None):
    """Return an initialized PCA9685 driver for the Servo FeatherWing."""
    if i2c is None:
        i2c = board.I2C()

    while not i2c.try_lock():
        time.sleep(0.001)
    i2c.unlock()

    controller = PCA9685(i2c, address=address)
    controller.frequency = frequency
    print(
        f"Servo controller ready on I2C address 0x{address:02X} at {frequency} Hz."
    )
    return controller


def ensure_servo_controller():
    global servo_controller, servo_status
    if servo_controller is not None:
        return servo_controller
    try:
        servo_controller = connect_servo_controller()
    except Exception as err:
        print(f"Servo controller connection failed: {err}")
        servo_controller = None
        servo_status = SERVO_DEFAULT_STATUS
        return None
    else:
        servo_status = "Controller connected"
        return servo_controller


def get_servo_status_color():
    return STATUS_CONNECTED_COLOR if servo_controller else STATUS_DISCONNECTED_COLOR


def pulse_us_to_duty_cycle(pulse_us, frequency=SERVO_FREQUENCY):
    period_seconds = 1.0 / frequency
    pulse_seconds = pulse_us / 1_000_000
    duty_cycle = int((pulse_seconds / period_seconds) * 0xFFFF)
    return max(0, min(0xFFFF, duty_cycle))


def set_servo_pulse(channel, pulse_us):
    controller = ensure_servo_controller()
    if controller is None:
        return False
    duty_cycle = pulse_us_to_duty_cycle(pulse_us, controller.frequency)
    controller.channels[channel].duty_cycle = duty_cycle
    return True


def clamp_degrees(value):
    return max(-SERVO_RANGE_DEGREES, min(SERVO_RANGE_DEGREES, value))


def set_axis_angle(eye, axis, degrees):
    servo = SERVO_LOOKUP.get((eye, axis))
    if servo is None:
        print(f"No servo configured for {eye} {axis}.")
        return False, 0.0
    clamped = clamp_degrees(degrees)
    pulse = servo["zero_pulse_us"] + servo["direction"] * clamped * SERVO_US_PER_DEGREE
    success = set_servo_pulse(servo["channel"], pulse)
    return success, clamped


def move_eye_to_angles(eye, pan_deg, tilt_deg):
    pan_ok, pan_applied = set_axis_angle(eye, "pan", pan_deg)
    tilt_ok, tilt_applied = set_axis_angle(eye, "tilt", tilt_deg)

    if pan_ok:
        eye_angles[eye]["pan"] = pan_applied
    if tilt_ok:
        eye_angles[eye]["tilt"] = tilt_applied

    if pan_ok or tilt_ok:
        update_eye_status()

    return pan_ok and tilt_ok


def apply_point_selection(point_key):
    vector = NINE_POINT_VECTORS.get(point_key)
    if vector is None:
        print(f"Unknown 9-pt selection: {point_key}")
        return False

    distance = get_point_distance()
    pan_deg = vector[0] * distance
    tilt_deg = vector[1] * distance
    applied = False
    for eye in get_target_eyes():
        if move_eye_to_angles(eye, pan_deg, tilt_deg):
            print(f"Moved {eye} eye to {point_key} ({pan_deg}°, {tilt_deg}°).")
            applied = True
    return applied


def perform_saccade(left_pan, left_tilt, right_pan, right_tilt):
    left_pan_value = eye_angles["L"]["pan"] if left_pan is None else left_pan
    left_tilt_value = eye_angles["L"]["tilt"] if left_tilt is None else left_tilt
    right_pan_value = eye_angles["R"]["pan"] if right_pan is None else right_pan
    right_tilt_value = eye_angles["R"]["tilt"] if right_tilt is None else right_tilt

    left_ok = move_eye_to_angles("L", left_pan_value, left_tilt_value)
    right_ok = move_eye_to_angles("R", right_pan_value, right_tilt_value)
    return (
        left_ok and right_ok,
        (left_pan_value, left_tilt_value, right_pan_value, right_tilt_value),
    )


def parse_saccade_arg(token):
    normalized = token.strip().upper()
    if normalized in ("X", "H", "HOLD", "SKIP", "KEEP", "NC"):
        return None
    return float(token)


serial_command_buffer = ""


def handle_serial_command(command):
    command = command.strip()
    if not command:
        return

    parts = command.split()
    command_key = parts[0].upper()
    args = parts[1:]

    if len(parts) == 1 and command_key in NINE_POINT_VECTORS:
        applied = apply_point_selection(command_key)
        if applied:
            print(f"CMD OK 9PT {command_key}")
        else:
            print(f"CMD ERR 9PT {command_key}")
        return

    if command_key in ("SAC", "SACCADE"):
        if len(args) != 4:
            print("CMD ERR SAC needs 4 angles")
            return
        try:
            left_pan, left_tilt, right_pan, right_tilt = (
                parse_saccade_arg(value) for value in args
            )
        except ValueError:
            print("CMD ERR SAC invalid angle")
            return
        success, applied = perform_saccade(left_pan, left_tilt, right_pan, right_tilt)
        if success:
            lp, lt, rp, rt = applied
            print(f"CMD OK SAC {lp:.1f} {lt:.1f} {rp:.1f} {rt:.1f}")
        else:
            print("CMD ERR SAC move failed")
        return

    print(f"CMD ERR Unknown command: {command}")


def poll_serial_commands():
    global serial_command_buffer

    if not supervisor.runtime.serial_connected:
        serial_command_buffer = ""
        return

    while supervisor.runtime.serial_bytes_available:
        char = sys.stdin.read(1)
        if char in ("\n", "\r"):
            command = serial_command_buffer.strip()
            serial_command_buffer = ""
            if command:
                handle_serial_command(command)
        else:
            serial_command_buffer += char
            if len(serial_command_buffer) > 64:
                serial_command_buffer = ""
                print("CMD ERR Line too long")


def zero_servos():
    success = True
    for eye in EYE_KEYS:
        if not move_eye_to_angles(eye, 0, 0):
            print(f"Failed to zero {eye} eye.")
            success = False
    if success:
        nine_pt_options = MENU[MENU_9PT_INDEX]["options"]
        if "C" in nine_pt_options:
            selected_option_indices[MENU_9PT_INDEX] = nine_pt_options.index("C")
        print("All servos centered.")
    return success

def update_menu_labels():
    for idx, menu_label in enumerate(menu_labels):
        menu_label.color = (
            MENU_HIGHLIGHT_COLOR if idx == current_menu_index else MENU_COLOR
        )


def render_options():
    while len(options_group):
        options_group.pop()

    section = MENU[current_menu_index]
    if section["name"] == "Settings":
        ensure_servo_controller()

    options = section["options"]
    selected_option = selected_option_indices[current_menu_index]

    if not options:
        message = section.get("message")
        if callable(message):
            text = message()
        elif isinstance(message, str):
            text = message
        else:
            text = ""

        color = OPTION_SELECTED_COLOR if selected_option is not None else OPTION_COLOR
        zero_label = label.Label(
            terminalio.FONT,
            text=text,
            color=color,
            scale=OPTION_LABEL_SCALE,
            line_spacing=1.2,
            anchor_point=(0.0, 0.0),
            anchored_position=(8, options_base_y),
        )
        options_group.append(zero_label)
        return

    row_length = section.get("row_length", len(options))
    col_width = screen_width // row_length

    for idx, option in enumerate(options):
        row = idx // row_length
        col = idx % row_length
        x = col_width * col + col_width // 2
        y = options_base_y + row * OPTION_ROW_SPACING

        is_current = idx == (current_option_indices[current_menu_index] or 0)
        is_selected = selected_option == idx

        display_text = option
        if section["name"] == "Settings":
            if option == "Eye":
                display_text = f"{option}: {get_eye_selection()}"
            elif option == "Range":
                display_text = f"{option}: {get_point_distance()}°"

        text = f"[{display_text}]" if is_current else display_text
        color = OPTION_HIGHLIGHT_COLOR if is_current else OPTION_COLOR
        if is_selected:
            color = OPTION_SELECTED_COLOR

        option_label = label.Label(
            terminalio.FONT,
            text=text,
            color=color,
            scale=OPTION_LABEL_SCALE,
            anchor_point=(0.5, 0.0),
            anchored_position=(x, y),
        )
        options_group.append(option_label)

    if section["name"] == "Settings":
        status_color = get_servo_status_color()
        status_msg = servo_status
        status_option_label = label.Label(
            terminalio.FONT,
            text=status_msg,
            color=status_color,
            scale=OPTION_LABEL_SCALE,
            anchor_point=(0.0, 0.0),
            anchored_position=(
                8,
                options_base_y + len(options) * OPTION_ROW_SPACING + 10,
            ),
        )
        options_group.append(status_option_label)


def get_eye_selection():
    return EYE_OPTIONS[eye_selection_index]


def cycle_eye_selection():
    global eye_selection_index
    eye_selection_index = (eye_selection_index + 1) % len(EYE_OPTIONS)


def get_point_distance():
    return POINT_DISTANCE_OPTIONS[point_distance_index]


def cycle_point_distance():
    global point_distance_index
    point_distance_index = (point_distance_index + 1) % len(POINT_DISTANCE_OPTIONS)


def get_target_eyes():
    eye_selection = get_eye_selection()
    if eye_selection == "L":
        return ("L",)
    if eye_selection == "R":
        return ("R",)
    return EYE_KEYS


def cycle_menu():
    global current_menu_index
    current_menu_index = (current_menu_index + 1) % len(MENU)
    if MENU[current_menu_index]["options"] and current_option_indices[current_menu_index] is None:
        current_option_indices[current_menu_index] = 0
    update_menu_labels()
    render_options()


def cycle_option():
    section = MENU[current_menu_index]
    options = section["options"]
    if not options:
        return
    current_option = current_option_indices[current_menu_index] or 0
    current_option = (current_option + 1) % len(options)
    current_option_indices[current_menu_index] = current_option
    render_options()


def handle_selection():
    section = MENU[current_menu_index]
    if section["name"] == "Zero":
        zero_servos()
        selected_option_indices[current_menu_index] = 0
        render_options()
        return

    if section["name"] == "Settings":
        option_index = current_option_indices[current_menu_index]
        if option_index is None or option_index >= len(section["options"]):
            return
        selection = section["options"][option_index]
        selected_option_indices[current_menu_index] = option_index
        if selection == "Eye":
            cycle_eye_selection()
            print(f"Settings -> Eye target: {get_eye_selection()}")
        elif selection == "Range":
            cycle_point_distance()
            print(f"Settings -> Range: {get_point_distance()}°")
        render_options()
        return

    option_index = current_option_indices[current_menu_index]
    if option_index is not None and section["options"]:
        selection = section["options"][option_index]
        selected_option_indices[current_menu_index] = option_index
        print(f"Selected {section['name']} -> {selection}")
        if section["name"] == "9-pt":
            apply_point_selection(selection)
    else:
        selected_option_indices[current_menu_index] = 0
        print(f"Selected {section['name']}")
    render_options()


update_menu_labels()
render_options()

print("GUI ready. Use D2 (cycle), D1 (options), D0 (select).")

while True:
    poll_serial_commands()
    for key_group, names in BUTTON_GROUPS:
        event = key_group.events.get()
        while event:
            button_name = names[event.key_number]

            if button_name == "D0" and event.pressed:
                handle_selection()

            elif button_name == "D1" and event.pressed:
                cycle_option()

            elif button_name == "D2":
                if event.pressed:
                    d2_press_time = time.monotonic()
                elif event.released:
                    if d2_press_time is None:
                        cycle_menu()
                    else:
                        held_time = time.monotonic() - d2_press_time
                        d2_press_time = None
                        if held_time >= D2_SELECT_HOLD_SECONDS:
                            handle_selection()
                        else:
                            cycle_menu()

            event = key_group.events.get()

    time.sleep(0.01)
