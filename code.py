import board
import analogio
import digitalio
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_displayio_sh1107 import SH1107

# Constants
DRIVE_MODE = 0
MAST_MODE = 1

# Setup joystick axes
x_axis = analogio.AnalogIn(board.A0)
y_axis = analogio.AnalogIn(board.A1)
z_axis = analogio.AnalogIn(board.A2)

# Setup button
button = digitalio.DigitalInOut(board.D4)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Setup lights
lights = digitalio.DigitalInOut(board.D5)
lights.direction = digitalio.Direction.OUTPUT

# Initial state
current_mode = DRIVE_MODE
speed_multiplier = 1.0
lights_on = False
button_pressed = False
button_held_time = 0

# Display setup
display = None
text_areas = {}

def init_display():
    """Initialize the display dynamically based on connected hardware."""
    global display, text_areas

    displayio.release_displays()
    if hasattr(board, "DISPLAY"):  # Built-in display
        display = board.DISPLAY
    else:
        i2c = board.I2C()
        display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
        display = SH1107(display_bus, width=128, height=64)

    # Create the display layout
    main_group = displayio.Group()
    layout = GridLayout(x=0, y=0, width=display.width, height=display.height, grid_size=(1, 3))
    
    # Add text labels
    for i, label_text in enumerate(["Mode", "Speed", "Values"]):
        text_area = label.Label(terminalio.FONT, text=f"{label_text}: ---", scale=1)
        layout.add_content(text_area, grid_position=(0, i))
        text_areas[label_text] = text_area

    main_group.append(layout)
    display.show(main_group)

def update_display():
    """Update the display with the latest information."""
    mode_text = "Driving" if current_mode == DRIVE_MODE else "Mast"
    speed_text = f"{speed_multiplier:.2f}"
    values_text = f"X={read_axis(x_axis):.2f}, Y={read_axis(y_axis):.2f}"

    text_areas["Mode"].text = f"Mode: {mode_text}"
    text_areas["Speed"].text = f"Speed: {speed_text}"
    text_areas["Values"].text = f"Values: {values_text}"

def read_axis(axis):
    """Normalize axis value to range -1.0 to 1.0."""
    return (axis.value - 32768) / 32768.0

def update_speed():
    """Update speed multiplier based on twist axis."""
    global speed_multiplier
    twist = read_axis(z_axis)
    speed_multiplier = max(0.5, 1.0 + twist)  # Base speed multiplier 0.5 to 1.5

def toggle_mode():
    """Toggle between drive and mast control modes."""
    global current_mode
    current_mode = DRIVE_MODE if current_mode == MAST_MODE else MAST_MODE

def toggle_lights():
    """Toggle the lights."""
    global lights_on
    lights_on = not lights_on
    lights.value = lights_on

# Initialize display
init_display()

# Main loop
while True:
    # Read joystick axes
    x = read_axis(x_axis) * speed_multiplier
    y = read_axis(y_axis) * speed_multiplier

    # Check button state
    if not button.value:  # Button pressed
        if not button_pressed:
            button_pressed = True
            button_held_time = time.monotonic()

        # Check if button is held for more than 1 second
        if time.monotonic() - button_held_time > 1:
            toggle_lights()
            while not button.value:  # Wait until button is released
                pass
            button_pressed = False

    else:  # Button released
        if button_pressed:
            button_pressed = False
            toggle_mode()

    # Update speed
    update_speed()

    # Update display
    update_display()

    # Perform actions based on mode
    if current_mode == DRIVE_MODE:
        print(f"Driving: X={x:.2f}, Y={y:.2f}, Speed={speed_multiplier:.2f}")
    elif current_mode == MAST_MODE:
        print(f"Mast Control: Tilt={x:.2f}, Height={y:.2f}, Speed={speed_multiplier:.2f}")

    # Add a small delay for debounce and smooth operation
    time.sleep(0.05)
