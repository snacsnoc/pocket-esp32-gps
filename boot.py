# boot.py

from lib.typing import Tuple, Optional
import time
from machine import (
    Pin,
    I2C,
    lightsleep,
    freq,
    ADC,
    deepsleep,
    reset_cause,
    DEEPSLEEP_RESET,
)
import esp32
import ssd1306
import gps_handler
from gps_handler import error_led
from utils import haversine
import utime

# Button debounce delay in ms
DEBOUNCE_DELAY = 150
POWERSAVE_BOOT = False

# Initialize I2C and display
i2c = I2C(scl=Pin(22), sda=Pin(21))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

if POWERSAVE_BOOT:
    # Set CPU frequency to 80MHz for power saving
    freq(80000000)
    # ADC power down
    adc = ADC(0)
    adc.atten(ADC.ATTN_0DB)
    adc.width(ADC.WIDTH_9BIT)

    # Delay turning on display upon boot for 5 seconds
    display.poweroff()
    display.contrast(1)
    lightsleep(5000)
    display.poweron()


# Mutable LCD settings
LCD_DISPLAY_SETTINGS = {
    "contrast": 1,
    "invert": 0,
    "poweroff": False,
    "poweron": True,
    "rotate": 0,
}

# Initialize display
display.contrast(LCD_DISPLAY_SETTINGS["contrast"])
display.invert(LCD_DISPLAY_SETTINGS["invert"])


if reset_cause() == DEEPSLEEP_RESET:
    print("Woke from deep sleep")
    time.sleep(0.5)
    display_on = True
    gps_handler.init_gps()
    display.poweron()

# Track display state
display_on = True

# Built-in ESP32 LED
builtin_led = Pin(2, Pin.OUT)
builtin_led.value(0)

# Buttons
set_button = Pin(13, Pin.IN, Pin.PULL_UP)
reset_button = Pin(14, Pin.IN, Pin.PULL_UP)
display_power_button = Pin(33, Pin.IN, Pin.PULL_UP)

# Mode LED
mode_led = Pin(12, Pin.OUT)
mode_led.value(0)

# Warning/display off LED
warning_led = Pin(25, Pin.OUT)
warning_led.value(0)


# Set defaults for points
point_A = None
point_B = None

# 0: GPS Display, 1: Distance Calculation, 2: Settings, 3: About
current_mode = 0
# Menu options
MODES = ["GPS Display", "Distance Calc", "Settings", "About"]


# Update the GPS display
def update_gps_display():
    if current_mode == 0:
        display.fill(0)
        display.text(f"Fix: {gps_handler.gps_data['fix']}", 0, 0)
        display.text(f"Lat: {gps_handler.gps_data['lat']:.6f}", 0, 16)
        display.text(f"Lon: {gps_handler.gps_data['lon']:.6f}", 0, 24)
        display.text(f"Alt: {gps_handler.gps_data['alt']}m", 0, 32)
        display.text(f"Sats: {gps_handler.gps_data['sats']}", 0, 40)
        display.text(f"PPS: {gps_handler.gps_data['pps']}us", 0, 48)
        display.show()


# Display two lines of text, optionally three
def display_text(line1, line2, line3=None):
    display.fill(0)
    display.fill_rect(0, 0, 128, 48, 0)
    display.text(line1, 0, 0)
    display.text(line2, 0, 16)
    if line3:
        display.text(line3, 0, 24)
    display.show()


def handle_set_button(pin):
    time.sleep_ms(DEBOUNCE_DELAY)
    if not pin.value():
        # Distance mode
        if current_mode == 1:
            set_distance_point()
        # Add other mode-specific SET button actions here


def set_distance_point() -> None:
    global point_A, point_B
    mode_led.value(1)
    print("pressed set button")

    lat: float = gps_handler.gps_data["lat"]
    lon: float = gps_handler.gps_data["lon"]

    # Check if we have a valid fix before setting
    if gps_handler.gps_data["fix"] == "Valid":
        if point_A is None:
            point_A: Tuple[float, float] = (lat, lon)
            display_text("Point A set", f"Lat: {lat:.6f}")
            print(f"Point A set: {point_A}")
            display.fill(0)
            display_text("Set Point B", "Press button again")
        elif point_B is None:
            point_B: Tuple[float, float] = (lat, lon)
            display_text("Point B set", f"Lat: {lat:.6f}")
            print(f"Point B set: {point_B}")

            # Calculate distance when both points are set
            distance = haversine(point_A[0], point_A[1], point_B[0], point_B[1])
            display_text("Distance:", f"{distance:.2f} m", "Press mode btn")
            print(f"Distance: {distance:.2f} meters")
        else:
            # Reset points if both are already set
            point_A = point_B = None
            display_text("Points reset", "Set new Point A")
            print("Points reset. Ready to set new points.")
        enter_distance_mode()
    else:
        display_text("No GPS fix", "Try again later")
        error_led.value(1)
        print("No valid GPS data available")


def enter_distance_mode():
    global point_A, point_B
    if point_A is None:
        display_text("Distance Mode", "Set Point A", "Press SET")
    elif point_B is None:
        display_text("Point A set", "Set Point B", "Press SET")
    else:
        distance = haversine(point_A[0], point_A[1], point_B[0], point_B[1])
        display_text("Distance:", f"{distance:.2f} m", "SET to reset")


# Button handler to reset/mode change
def handle_reset_button(pin):
    global current_mode
    time.sleep_ms(DEBOUNCE_DELAY)
    if not pin.value():
        current_mode = (current_mode + 1) % len(MODES)
        enter_mode(current_mode)


# Button handler to toggle display power
def handle_display_power(pin):
    global display_on
    time.sleep_ms(DEBOUNCE_DELAY)
    if not pin.value():
        print("Pressed display power button")
        if display_on:
            # Prepare for deep sleep
            display.poweroff()
            warning_led.value(1)
            print("Entering deep sleep")

            # Configure wake-up source using the same btn
            esp32.wake_on_ext0(pin=display_power_button, level=0)
            # Wait for 1 second to avoid immediate wake-up
            # This is just to avoid immediate wake-up
            utime.sleep(1)
            # Enter deep sleep
            deepsleep()
        else:
            # Wake up actions
            display.poweron()
            warning_led.value(0)
            display_on = True
            print("Waking up from deep sleep")

            # Re-initialize GPS
            # This is probably redundant, but just in case
            gps_handler.init_gps()


def enter_settings_mode():
    display_text("Settings", "Contrast", str(LCD_DISPLAY_SETTINGS["contrast"]))


def display_about():
    display_text("Pocket ESP32 GPS", "v1.0", "By Easton")


# Enter mode based on current_mode
def enter_mode(mode):
    if mode == 0:
        update_gps_display()
    elif mode == 1:
        enter_distance_mode()
    elif mode == 2:
        enter_settings_mode()
    elif mode == 3:
        display_about()


# Attach interrupts to buttons
set_button.irq(trigger=Pin.IRQ_FALLING, handler=handle_set_button)
reset_button.irq(trigger=Pin.IRQ_FALLING, handler=handle_reset_button)
display_power_button.irq(trigger=Pin.IRQ_FALLING, handler=handle_display_power)
# Note: the PPS interrupt handler is set in gps_handler.py

# Main loop
while True:
    # Continuously read GPS data
    gps_handler.read_gps()
    if display_on:
        enter_mode(current_mode)
    time.sleep(0.5)
