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
    lightsleep,
    reset_cause,
    DEEPSLEEP_RESET,
)
import os
import gc
import esp32
import ssd1306
import gps_handler
from gps_handler import error_led
from utils import haversine
import utime
import ujson

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
    lightsleep(0.5)
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
reset_mode_button = Pin(14, Pin.IN, Pin.PULL_UP)
display_power_button = Pin(33, Pin.IN, Pin.PULL_UP)
nav_button = Pin(32, Pin.IN, Pin.PULL_UP)

# Mode LED
mode_led = Pin(12, Pin.OUT)
mode_led.value(0)

# Warning/display off LED
warning_led = Pin(25, Pin.OUT)
warning_led.value(0)


# Set defaults for points
point_A = None
point_B = None

DEVICE_SETTINGS = {
    "pwr_save": False,
}

# 0: GPS Display, 1: Distance Calculation, 2: Settings, 3: About
current_mode = 0
# Menu options
MODES = ["GPS Display", "Distance Calc", "Settings", "About"]

# Settings menu
settings_index = 0
SETTINGS_OPTIONS = ["Contrast", "Invert Display", "Power Save Mode"]
# Settings menu options
is_editing = False

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
    global is_editing
    time.sleep_ms(DEBOUNCE_DELAY)
    if not pin.value():
        if current_mode == 1:
            set_distance_point()
        elif current_mode == 2:  # Settings mode
            apply_setting_change()
        update_settings_display()


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


def handle_nav_button(pin):
    global settings_index
    time.sleep_ms(DEBOUNCE_DELAY)
    if not pin.value():
        if current_mode == 2:  # Settings mode
            settings_index = (settings_index + 1) % len(SETTINGS_OPTIONS)
            update_settings_display()


# Toggle device power save mode
# Lowers clock speed and turns on other options to save power
def toggle_pwrsave_mode():
    DEVICE_SETTINGS["pwr_save"] = not DEVICE_SETTINGS["pwr_save"]
    if DEVICE_SETTINGS["pwr_save"]:
        print("Entering power save mode")
        # Set clock speed to 80MHz
        # Valid settings are 20MHz, 40MHz, 80Mhz, 160MHz or 240MHz (ESP32)
        freq(40000000)
    else:
        print("Exiting power save mode")
        # Set clock speed to 240MHz
        freq(240000000)
    print(f"Power save mode: {'On' if DEVICE_SETTINGS['pwr_save'] else 'Off'}")


def apply_setting_change():
    global is_editing
    if settings_index == 0:  # Contrast
        LCD_DISPLAY_SETTINGS["contrast"] = (LCD_DISPLAY_SETTINGS["contrast"] % 15) + 1
        display.contrast(LCD_DISPLAY_SETTINGS["contrast"])
    elif settings_index == 1:  # Invert Display
        LCD_DISPLAY_SETTINGS["invert"] = not LCD_DISPLAY_SETTINGS["invert"]
        display.invert(LCD_DISPLAY_SETTINGS["invert"])
    elif settings_index == 2:  # Power Save Mode
        toggle_pwrsave_mode()

    # Toggle editing mode
    is_editing = not is_editing


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


def update_settings_display():
    display.fill(0)
    display.text("Settings", 0, 0)

    # Display only 3 options at a time
    start_index = max(0, settings_index - 1)
    end_index = min(len(SETTINGS_OPTIONS), start_index + 3)

    # Use the index to determine which setting is currently being edited
    # and whether it's being edited or not
    # Use > to indicate the cursor
    # Use * to indicate which setting is currently being edited

    for i in range(start_index, end_index):
        option = SETTINGS_OPTIONS[i]
        prefix = ">" if i == settings_index else " "
        display.text(f"{prefix}{option}", 0, (i - start_index + 1) * 16)

    # Display the current value of the selected option
    if settings_index == 0:
        value = f"Contrast: {LCD_DISPLAY_SETTINGS['contrast']}"
    elif settings_index == 1:
        value = f"Invert: {'On' if LCD_DISPLAY_SETTINGS['invert'] else 'Off'}"
    elif settings_index == 2:
        value = f"PWR Save: {'On' if DEVICE_SETTINGS['pwr_save'] else 'Off'}"
    else:
        value = ""

    # Display current setting value at the bottom of the screen
    display.text(value, 0, 56)
    display.show()

    print(f"Settings Index: {settings_index}, Editing: {is_editing}")
    print(f"Displayed Value: {value}")


def enter_settings_mode():
    global is_editing
    is_editing = False
    update_settings_display()


def save_settings():
    try:
        with open("settings.json", "w") as f:
            ujson.dump({"lcd": LCD_DISPLAY_SETTINGS, "device": DEVICE_SETTINGS}, f)
    except:
        print("Failed to save settings")


def display_about():
    display.fill(0)
    display.text("Pocket ESP32 GPS", 0, 0)
    display.text("v1.0 By Easton", 0, 10)

    # CPU frequency
    cpu_freq = freq() / 1_000_000
    display.text(f"CPU: {cpu_freq:.0f} MHz", 0, 20)

    # Free RAM
    free_ram = gc.mem_free() / 1024
    display.text(f"Free RAM: {free_ram:.1f} KB", 0, 30)

    # Available storage
    try:
        storage_info = os.statvfs("/")
        total_space = storage_info[0] * storage_info[2] / (1024 * 1024)
        free_space = storage_info[0] * storage_info[3] / (1024 * 1024)
        display.text(f"Storage: {free_space:.1f}/{total_space:.1f}MB", 0, 40)
    except:
        display.text("Storage info N/A", 0, 40)

    # Temperature if available
    try:
        temp_fahrenheit = esp32.raw_temperature()
        temp_celsius = (temp_fahrenheit - 32) * 5 / 9
        display.text(f"Temp: {temp_celsius:.2f} C", 0, 50)
    except:
        display.text("Temp info N/A", 0, 50)

    display.show()


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
reset_mode_button.irq(trigger=Pin.IRQ_FALLING, handler=handle_reset_button)
display_power_button.irq(trigger=Pin.IRQ_FALLING, handler=handle_display_power)
nav_button.irq(trigger=Pin.IRQ_FALLING, handler=handle_nav_button)
# Note: the PPS interrupt handler is set in gps_handler.py

# Main loop
while True:
    try:
        gps_handler.read_gps()
        lightsleep(200)
    except Exception as e:
        print(f"Error in main loop: {e}")
        time.sleep(1)
