import time
import os
import board
import analogio
import digitalio
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_displayio_sh1107 import SH1107
import adafruit_imageload

# Constants
DRIVE_MODE = 0
MAST_MODE = 1

# Setup joystick axes
x_axis = analogio.AnalogIn(board.D6)
IS_X_INVERTED = True
y_axis = analogio.AnalogIn(board.D5)
z_axis = analogio.AnalogIn(board.D9)

# Setup button
button = digitalio.DigitalInOut(board.D10)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.DOWN

# Setup lights
lights = digitalio.DigitalInOut(board.D13)
lights.direction = digitalio.Direction.OUTPUT

# Initial state
current_mode = DRIVE_MODE
speed_multiplier = 1.0
lights_on = False
button_pressed = False
button_held_time = 0

# Display setup
display = None
mast_image_tilegrid = None
drive_image_tilegrid = None
text_areas = {}

print("starting")

def init_display():
    """Initialize the display dynamically based on connected hardware."""
    global display, text_areas, mast_image_tilegrid, drive_image_tilegrid

    if hasattr(board, "DISPLAY"):  # Built-in display
        display = board.DISPLAY
    else:
        displayio.release_displays()
        i2c = board.I2C()
        display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
        display = SH1107(display_bus, width=128, height=64)
    
    # Create the display layout
    main_group = displayio.Group()
    layout = GridLayout(x=0, y=0, width=display.width, height=display.height, grid_size=(4, 3))

    palette = displayio.Palette(2)
    palette[1] = 0xFFFFFF
    
    mast_image, _ = adafruit_imageload.load(
       "/forklift-mast-140x80.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
    )
    mast_image_tilegrid = displayio.TileGrid(mast_image, pixel_shader=palette, x=-20, y=0)


    drive_image, _ = adafruit_imageload.load(
       "/forklift-drive-140x80.bmp"
    )
    drive_image_tilegrid = displayio.TileGrid(drive_image, pixel_shader=palette, x=-20, y=0)
    drive_image_tilegrid.hidden = False
    
    image_group = displayio.Group()
    # image_group.append(mast_image_tilegrid)
    # image_group.append(drive_image_tilegrid)
    layout.add_content(mast_image_tilegrid, grid_position=(2,1), cell_size=(1,1))
    layout.add_content(drive_image_tilegrid, grid_position=(2,1), cell_size=(1,1))
    # layout.add_content(mast_image_tilegrid, grid_position=(1,0), cell_size=(1,1))
    # layout.add_content(drive_image_tilegrid, grid_position=(1,0), cell_size=(1,1))
    
    # Add text labels
    for i, label_text in enumerate(["Mode", "Speed", "Values"]):
        text_area = label.Label(terminalio.FONT, text=f"{label_text}: ---", scale= 2 if i < 2 else 1)
        layout.add_content(text_area, grid_position=(0, i), cell_size=(1,1))
        text_areas[label_text] = text_area

    main_group.append(layout)
    display.root_group = main_group

def update_display():
    """Update the display with the latest information."""
    global drive_image_tilegrid, mast_image_tilegrid
    mode_text = "Driving" if current_mode == DRIVE_MODE else "Mast"
    drive_image_tilegrid.hidden = current_mode != DRIVE_MODE
    mast_image_tilegrid.hidden = current_mode == DRIVE_MODE
    speed_text = f"{speed_multiplier:.2f}"
    values_text = f"X={read_axis(x_axis):.2f}, Y={read_axis(y_axis):.2f}"

    text_areas["Mode"].text = f"Mode: {mode_text}"
    text_areas["Speed"].text = f"Speed:\n{speed_text}"
    text_areas["Values"].text = f"\n\nValues: {values_text}"

def read_axis(axis):
    """Normalize axis value to range -1.0 to 1.0."""
    #TODO: add axis real voltage via esp32 readMilivolts or whatever it's called in circuitpython
    val = axis.value
    result = (val - 32768) / 32768.0
    if axis == x_axis:
        result = -1 * result
    return result

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

counter=4
# Main loop
while True:

    # Read joystick axes
    x = read_axis(x_axis) * speed_multiplier
    y = read_axis(y_axis) * speed_multiplier

    # Check button state
    if button.value:  # Button pressed
        if not button_pressed:
            button_pressed = True
            button_held_time = time.monotonic()

        # Check if button is held for more than 1 second
        if time.monotonic() - button_held_time > 1:
            toggle_lights()
            while button.value:  # Wait until button is released
                pass                 # Move to async 
            button_pressed = False

    else:  # Button released
        if button_pressed:
            button_pressed = False
            toggle_mode()

    # Update speed
    update_speed()

    # Update display
    update_display()

    print((x_axis.value, y_axis.value, z_axis.value), end=" ")
    # Perform actions based on mode
    if current_mode == DRIVE_MODE:
        print(f"Driving: X={x:.2f}, Y={y:.2f}, Speed={speed_multiplier:.2f}", end="")
    elif current_mode == MAST_MODE:
        print(f"Mast Control: Tilt={x:.2f}, Height={y:.2f}, Speed={speed_multiplier:.2f}", end="")

    counter = counter + 1
    if counter % 8 == 0:
        print("  button state: ", button.value, "  light state: ", lights_on)
        counter = 0
    else:
        print()
    
    # Add a small delay for debounce and smooth operation
    time.sleep(0.05)


