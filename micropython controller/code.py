import board
import displayio
import keypad
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

SERVO_CONFIG = [
    {"name": "Left pan", "channel": 4, "zero_pulse_us": 2100}, # increase is left
    {"name": "Left tilt", "channel": 5, "zero_pulse_us": 1700}, # increase is up
    {"name": "Right pan", "channel": 6, "zero_pulse_us": 1350}, # increase is left
    {"name": "Right tilt", "channel": 7, "zero_pulse_us": 1300}, # increase is down
]

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
    pull=False,
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
        "name": "Eye",
        "options": ["L", "R", "B"],
        "row_length": 3,
        "cell_width": 5,
        "default_option": "B",
    },
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
        "name": "Serv",
        "options": [],
        "message": lambda: servo_status,
    },
]

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


def zero_servos():
    controller = ensure_servo_controller()
    if controller is None:
        print("Unable to zero servos without a controller.")
        return False

    success = True
    for servo in SERVO_CONFIG:
        channel = servo["channel"]
        pulse = servo["zero_pulse_us"]
        if not set_servo_pulse(channel, pulse):
            print(f"Failed to zero {servo['name']} (channel {channel}).")
            success = False
        else:
            print(f"Zeroed {servo['name']} on channel {channel} to {pulse}us.")

    if success:
        status_label.text = "L: 0°, 0°  R: 0°, 0°"
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
    if section["name"] == "Serv":
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

        text = f"[{option}]" if is_current else option
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

    option_index = current_option_indices[current_menu_index]
    if option_index is not None and section["options"]:
        selection = section["options"][option_index]
        selected_option_indices[current_menu_index] = option_index
        print(f"Selected {section['name']} -> {selection}")
    else:
        selected_option_indices[current_menu_index] = 0
        print(f"Selected {section['name']}")
    render_options()


update_menu_labels()
render_options()

print("GUI ready. Use D2 (cycle), D1 (options), D0 (select).")

while True:
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
