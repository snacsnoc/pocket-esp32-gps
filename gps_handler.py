# gps_handler.py

import time
from machine import UART, Pin

# Initialize UART1 to read from the GPS module
try:
    uart1 = UART(1, baudrate=9600, rx=16)
except ValueError as e:
    print(f"UART1 error: {e}")

# Global variables to store GPS data
gps_data = {"fix": "No Fix", "lat": 0.0, "lon": 0.0, "alt": 0, "sats": 0, "pps": 0}
last_pps_time = None

# Initialize LEDs
success_led = Pin(26, Pin.OUT)
error_led = Pin(27, Pin.OUT)
success_led.value(0)
error_led.value(0)

# Initialize PPS pin and attach interrupt
pps_pin = Pin(4, Pin.IN)


def pps_handler(pin):
    global gps_data, last_pps_time
    current_time = time.ticks_us()
    if pin.value() == 1:
        if last_pps_time is not None:
            interval = time.ticks_diff(current_time, last_pps_time)
            gps_data["pps"] = interval
        last_pps_time = current_time


pps_pin.irq(trigger=Pin.IRQ_RISING, handler=pps_handler)

# Convert DDDMM.MMMM to decimal degrees
def convert_to_decimal(degrees_minutes):
    if degrees_minutes:
        try:
            d, m = divmod(float(degrees_minutes), 100)
            return d + (m / 60)
        except ValueError:
            print(f"Error converting {degrees_minutes} to decimal")
            return None
    return None


# Read GPS data
def read_gps():
    global gps_data
    line = uart1.readline()
    if line:
        try:
            line_decoded = line.decode("ascii").strip()
            data = line_decoded.split(",")

            if "GPRMC" in line_decoded:
                if len(data) >= 3:
                    if data[2] == "A":
                        gps_data["fix"] = "Valid"
                        # Turn off error LED and turn on success LED
                        error_led.value(0)
                        success_led.value(1)
                    else:
                        gps_data["fix"] = "No Fix"
                        success_led.value(0)
                        error_led.value(1)

                    if gps_data["fix"] == "Valid" and len(data) >= 7:
                        latitude = convert_to_decimal(data[3])
                        longitude = convert_to_decimal(data[5])
                        if latitude is not None and longitude is not None:
                            gps_data["lat"] = latitude * (-1 if data[4] == "S" else 1)
                            gps_data["lon"] = longitude * (-1 if data[6] == "W" else 1)

            if "GPGGA" in line_decoded:
                if len(data) >= 10:
                    gps_data["alt"] = float(data[9]) if data[9] else 0
                    gps_data["sats"] = int(data[7]) if data[7] else 0

        except Exception as e:
            print(f"Error processing GPS data: {e}")
            gps_data["fix"] = f"Error: {str(e)[:10]}"
            success_led.value(0)
            error_led.value(1)

    # Short sleep to prevent CPU hogging
    time.sleep(0.2)
