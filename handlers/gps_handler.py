# gps_handler.py

import time

from machine import UART, Pin


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

    # Initialize UART1 to read from the GPS module
    def init_gps(self):

        try:
            self.uart1 = UART(
                1, baudrate=9600, bits=8, parity=None, stop=1, tx=Pin(17), rx=Pin(16)
            )
            if not self.uart1:
                raise ValueError("Failed to initialize UART")
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
    def read_gps(self):
        if self.uart1 is None:
            print("UART not initialized!")
            return self.gps_data
        line = self.uart1.readline()
        if line:
            try:
                line_decoded = line.decode("ascii", "ignore").strip()

                if line_decoded.startswith("$"):
                    data = line_decoded.split(",")

                    if "GPRMC" in line_decoded and len(data) >= 7:
                        if len(data) >= 3:
                            if data[2] == "A":
                                self.gps_data["fix"] = "Valid"
                                # Turn off error LED and turn on success LED
                                self.led_handler.set_success_led(1)
                                self.led_handler.set_warning_led(0)
                                self.led_handler.set_error_led(0)
                            else:
                                self.gps_data["fix"] = "No Fix"
                                self.led_handler.set_success_led(0)
                                self.led_handler.set_warning_led(0)
                                self.led_handler.set_error_led(1)

                            if self.gps_data["fix"] == "Valid" and len(data) >= 7:
                                # Extract UTC time
                                if data[1]:
                                    utc_time = data[1]
                                    self.gps_data[
                                        "utc_time"
                                    ] = f"{utc_time[:2]}:{utc_time[2:4]}:{utc_time[4:6]}"

                                # Extract date
                                if data[9]:
                                    date = data[9]
                                    self.gps_data[
                                        "utc_date"
                                    ] = f"20{date[4:6]}-{date[2:4]}-{date[:2]}"
                                # Extract latitude and longitude
                                latitude = self.convert_to_decimal(data[3])
                                longitude = self.convert_to_decimal(data[5])
                                if latitude is not None and longitude is not None:
                                    self.gps_data["lat"] = latitude * (
                                        -1 if data[4] == "S" else 1
                                    )
                                    self.gps_data["lon"] = longitude * (
                                        -1 if data[6] == "W" else 1
                                    )

                    elif "GPGGA" in line_decoded and len(data) >= 10:
                        self.gps_data["alt"] = float(data[9]) if data[9] else 0
                        self.gps_data["sats"] = int(data[7]) if data[7] else 0

                    print(f"Decoded NMEA: {line_decoded}")
                else:
                    print(f"Invalid NMEA sentence: {line_decoded}")

            except Exception as e:
                print(f"Error processing GPS data: {str(e)[:50]}")
                print(f"Raw line: {line}")
        # Update fix status based on available data
        if self.gps_data["fix"] == "No Fix":
            if any(self.gps_data.get(key) for key in ["lat", "lon", "alt", "sats"]):
                self.gps_data["fix"] = "Partial"
                self.led_handler.set_warning_led(1)
                print("Fix status updated to Partial")

        # Short sleep to prevent CPU hogging
        # Do not remove this sleep
        time.sleep(0.3)
        return self.gps_data
