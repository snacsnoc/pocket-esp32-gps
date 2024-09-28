# boot.py

import math
import time
from machine import Pin, I2C
import ssd1306
import gps_handler

# Button debounce delay in ms
DEBOUNCE_DELAY = 150

# Initialize I2C and display
i2c = I2C(scl=Pin(22), sda=Pin(21))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# Built-in ESP32 LED
builtin_led = Pin(2, Pin.OUT)

# Buttons
set_button = Pin(13, Pin.IN, Pin.PULL_UP)
reset_button = Pin(14, Pin.IN, Pin.PULL_UP)

# Mode LED
mode_led = Pin(12, Pin.OUT)
mode_led.value(0)

# Initialize variables
builtin_led.value(0)

# Set defaults for points
point_A = None
point_B = None

# 0: GPS Display, 1: Distance Calculation
mode = 0

# Function to calculate distance between two GPS coordinates in meters using Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    # Distance in meters
    return R * c


# Update the GPS display
def update_gps_display():
    if mode == 0:
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
    display.fill_rect(0, 0, 128, 48, 0)
    display.text(line1, 0, 0)
    display.text(line2, 0, 16)
    if line3:
        display.text(line3, 0, 24)
    display.show()


# Button handler to set points A and B with debounce
def handle_set_button(pin):
    time.sleep_ms(DEBOUNCE_DELAY)
    if not pin.value():
        global point_A, point_B
        mode_led.value(1)
        print("pressed set button")

        # Use stored GPS data
        lat = gps_handler.gps_data["lat"]
        lon = gps_handler.gps_data["lon"]

        # Check if we have a valid fix before setting
        if gps_handler.gps_data["fix"] == "Valid":
            if point_A is None:
                point_A = (lat, lon)
                display.fill(0)
                display_text("Point A set", f"Lat: {lat:.6f}")
                print(f"Point A set: {point_A}")
                display.fill(0)
                display_text("Set Point B", "Press button again")
            elif point_B is None:
                point_B = (lat, lon)
                display.fill(0)
                display_text("Point B set", f"Lat: {lat:.6f}")
                print(f"Point B set: {point_B}")

                # Calculate distance when both points are set
                distance = haversine(point_A[0], point_A[1], point_B[0], point_B[1])
                display.fill(0)
                display_text("Distance:", f"{distance:.2f} m", "Press mode btn")
                print(f"Distance: {distance:.2f} meters")
        else:
            print("No valid GPS data available")


# Button handler to reset/mode change
def handle_reset_button(pin):
    time.sleep_ms(DEBOUNCE_DELAY)
    if not pin.value():
        global mode, point_A, point_B
        print("Pressed reset/mode button")
        # Toggle between GPS mode (0) and distance mode (1)
        mode = (mode + 1) % 2
        point_A = None
        point_B = None
        if mode == 0:
            mode_led.value(0)
            display_text("GPS Mode", "Real-time data")
        else:
            mode_led.value(1)
            display_text("Distance Mode", "Set Point A")


# Attach interrupts to buttons
set_button.irq(trigger=Pin.IRQ_FALLING, handler=handle_set_button)
reset_button.irq(trigger=Pin.IRQ_FALLING, handler=handle_reset_button)
# Note: the PPS interrupt handler is set in gps_handler.py

# Start reading GPS data
display.fill(0)
display.text("Starting GPS...", 0, 0)
display.show()

while True:
    # Continuously read GPS data
    gps_handler.read_gps()

    if mode == 0:  # GPS Display Mode
        update_gps_display()
    time.sleep(0.5)
