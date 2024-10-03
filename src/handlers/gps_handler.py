# gps_handler.py

import time

from machine import UART, Pin
import gc


class GPSHandler:
    def __init__(self, led_handler):
        self.led_handler = led_handler
        # Global variables to store GPS data
        self.gps_data = {
            "fix": "No Fix",
            "lat": 0.0,
            "lon": 0.0,
            "alt": 0,
            "sats": 0,
            "pps": 0,
            "utc_time": None,
            "utc_date": None,
        }
        self.last_pps_time = None

        # Initialize PPS pin and attach interrupt
        self.pps_pin = Pin(4, Pin.IN)

        # UART object
        self.uart1 = None

        # Cache frequently used methods and objects
        self.uart_readline = self.uart1.readline if self.uart1 else None
        self.led_set_success = self.led_handler.set_success_led
        self.led_set_warning = self.led_handler.set_warning_led
        self.led_set_error = self.led_handler.set_error_led

    # Initialize UART1 to read from the GPS module
    def init_gps(self):

        try:
            self.uart1 = UART(
                1, baudrate=9600, bits=8, parity=None, stop=1, tx=Pin(17), rx=Pin(16)
            )
            if not self.uart1:
                raise ValueError("Failed to initialize UART")
            self.uart_readline = self.uart1.readline
        except Exception as e:
            print(f"UART initialization error: {e}")
            self.uart1 = None
            return

        # Attach interrupt to PPS pin
        self.pps_pin.irq(trigger=Pin.IRQ_RISING, handler=self.pps_handler)

        print("GPS initialized")

    def pps_handler(self, pin):
        current_time = time.ticks_us()
        if pin.value() == 1:
            if self.last_pps_time is not None:
                interval = time.ticks_diff(current_time, self.last_pps_time)
                self.gps_data["pps"] = interval
            self.last_pps_time = current_time

    # Convert DDDMM.MMMM to decimal degrees
    @staticmethod
    @micropython.native
    def convert_to_decimal(degrees_minutes):
        if degrees_minutes and degrees_minutes.strip():
            try:
                parts = degrees_minutes.split(".")
                if len(parts) != 2:
                    return None
                degrees = float(parts[0][:-2])
                minutes = float(parts[0][-2:] + "." + parts[1])
                return degrees + (minutes / 60)
            except ValueError as e:
                print(f"Error converting {degrees_minutes} to decimal: {e}")
        return None

    # Read GPS data
    # The @micropython.native decorator gives a 5% performance boost
    def read_gps(self):
        if not self.uart_readline:
            print("UART not initialized!")
            return self.gps_data

        line = self.uart_readline()
        if line:
            try:
                line_decoded = line.decode("ascii", "ignore").strip()

                if line_decoded.startswith("$"):
                    data = line_decoded.split(",")
                    # Cache locally for performance
                    gps_data = self.gps_data

                    if "GPRMC" in line_decoded and len(data) >= 7:
                        fix = data[2] == "A"
                        gps_data["fix"] = "Valid" if fix else "No Fix"

                        self.led_set_success(1 if fix else 0)
                        self.led_set_warning(0)
                        self.led_set_error(0 if fix else 1)

                        if fix and len(data) >= 7:
                            # Extract UTC time and date
                            gps_data[
                                "utc_time"
                            ] = f"{data[1][:2]}:{data[1][2:4]}:{data[1][4:6]}"
                            gps_data[
                                "utc_date"
                            ] = f"20{data[9][4:6]}-{data[9][2:4]}-{data[9][:2]}"

                            # Extract latitude and longitude
                            latitude = self.convert_to_decimal(data[3])
                            longitude = self.convert_to_decimal(data[5])
                            if latitude is not None and longitude is not None:
                                gps_data["lat"] = latitude * (
                                    -1 if data[4] == "S" else 1
                                )
                                gps_data["lon"] = longitude * (
                                    -1 if data[6] == "W" else 1
                                )

                    elif "GPGGA" in line_decoded and len(data) >= 10:
                        gps_data["alt"] = float(data[9]) if data[9] else 0
                        gps_data["sats"] = int(data[7]) if data[7] else 0

                else:
                    print(f"Invalid NMEA sentence: {line_decoded}")

            except Exception as e:
                print(f"Error processing GPS data: {str(e)[:50]}")
                print(f"Raw line: {line}")

        # Fix status handling
        if self.gps_data["fix"] == "No Fix":
            if any(self.gps_data.get(key) for key in ["lat", "lon", "alt", "sats"]):
                self.gps_data["fix"] = "Partial"
                self.led_set_warning(1)
                print("Fix status updated to Partial")

        # Short sleep to prevent CPU hogging
        # Do not remove this sleep
        time.sleep(0.3)
        gc.collect()
        return self.gps_data
