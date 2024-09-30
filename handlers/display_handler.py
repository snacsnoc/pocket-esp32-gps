import lib.ssd1306 as ssd1306
from machine import Pin, I2C, freq, deepsleep
import gc
import os
import esp32
import utime
from utils.haversine import haversine


class DisplayHandler:
    def __init__(self, gps, i2c):
        self.gps = gps
        self.display = ssd1306.SSD1306_I2C(128, 64, i2c)
        self.display_power_button = None
        self.mode_led = Pin(12, Pin.OUT)
        self.warning_led = Pin(25, Pin.OUT)
        self.current_mode = 0
        self.MODES = ["GPS Display", "Distance Calc", "Settings", "About"]
        self.settings_index = 0
        self.SETTINGS_OPTIONS = ["Contrast", "Invert Display", "Power Save Mode"]
        self.is_editing = False
        self.point_A = None
        self.point_B = None
        self.LCD_DISPLAY_SETTINGS = {
            "contrast": 1,
            "invert": 0,
            "poweroff": False,
            "poweron": True,
            "rotate": 0,
        }
        self.DEVICE_SETTINGS = {
            "pwr_save": False,
        }
        self.initialize_display()

    def initialize_display(self):
        self.display.contrast(self.LCD_DISPLAY_SETTINGS["contrast"])
        self.display.invert(self.LCD_DISPLAY_SETTINGS["invert"])
        self.enter_mode(self.current_mode)

    def set_display_power_button(self, button):
        self.display_power_button = button

    def enter_mode(self, mode):
        self.current_mode = mode
        if mode == 0:
            self.update_gps_display()
        elif mode == 1:
            self.mode_led.value(1)
            self.enter_distance_mode()
        elif mode == 2:
            self.mode_led.value(1)
            self.enter_settings_mode()
        elif mode == 3:
            self.mode_led.value(1)
            self.display_about()

    # Update the GPS display
    def update_gps_display(self):
        self.display.fill(0)
        fix_status = self.gps.gps_data["fix"]

        # Display fix status
        self.display.text(f"Fix: {fix_status}", 0, 0)

        # Display available data based on fix status
        if fix_status == "Valid" or fix_status == "Partial":
            if "lat" in self.gps.gps_data and self.gps.gps_data["lat"] is not None:
                self.display.text(f"Lat: {self.gps.gps_data['lat']:.6f}", 0, 16)
            if "lon" in self.gps.gps_data and self.gps.gps_data["lon"] is not None:
                self.display.text(f"Lon: {self.gps.gps_data['lon']:.6f}", 0, 24)
            if "alt" in self.gps.gps_data and self.gps.gps_data["alt"] is not None:
                self.display.text(f"Alt: {self.gps.gps_data['alt']}m", 0, 32)
            if "sats" in self.gps.gps_data:
                self.display.text(f"Sats: {self.gps.gps_data['sats']}", 0, 40)
        else:
            self.display.text("Waiting for fix...", 0, 24)

        # Always display PPS if available
        if "pps" in self.gps.gps_data and self.gps.gps_data["pps"] is not None:
            self.display.text(f"PPS: {self.gps.gps_data['pps']}us", 0, 48)

        self.display.show()
        self.mode_led.value(not self.mode_led.value())

    def enter_distance_mode(self):
        if self.point_A is None:
            self.display_text("Distance Mode", "Set Point A", "Press SET")
        elif self.point_B is None:
            self.display_text("Point A set", "Set Point B", "Press SET")
        else:
            distance = haversine(
                self.point_A[0], self.point_A[1], self.point_B[0], self.point_B[1]
            )
            self.display_text("Distance:", f"{distance:.2f} m", "SET to reset")

    def enter_settings_mode(self):
        self.is_editing = False
        self.update_settings_display()

    def display_about(self):
        self.display.fill(0)
        self.display.text("Pocket ESP32 GPS", 0, 0)
        self.display.text("v1.0 By Easton", 0, 10)
        cpu_freq = freq() / 1_000_000
        self.display.text(f"CPU: {cpu_freq:.0f} MHz", 0, 20)
        free_ram = gc.mem_free() / 1024
        self.display.text(f"Free RAM: {free_ram:.1f} KB", 0, 30)
        try:
            storage_info = os.statvfs("/")
            total_space = storage_info[0] * storage_info[2] / (1024 * 1024)
            free_space = storage_info[0] * storage_info[3] / (1024 * 1024)
            self.display.text(f"Storage: {free_space:.1f}/{total_space:.1f}MB", 0, 40)
        except:
            self.display.text("Storage info N/A", 0, 40)
        try:
            temp_fahrenheit = esp32.raw_temperature()
            temp_celsius = (temp_fahrenheit - 32) * 5 / 9
            self.display.text(f"Temp: {temp_celsius:.2f} C", 0, 50)
        except:
            self.display.text("Temp info N/A", 0, 50)
        self.display.show()

    def display_text(self, line1, line2, line3=None):
        self.display.fill(0)
        self.display.fill_rect(0, 0, 128, 48, 0)
        self.display.text(line1, 0, 0)
        self.display.text(line2, 0, 16)
        if line3:
            self.display.text(line3, 0, 24)
        self.display.show()

    def handle_set_button(self):
        if self.current_mode == 1:
            self.set_distance_point()
        elif self.current_mode == 2:
            self.apply_setting_change()
        self.update_settings_display()

    # Calculate the distance between two points using the Haversine formula
    def set_distance_point(self):
        lat, lon = self.gps.gps_data["lat"], self.gps.gps_data["lon"]

        # Check if we have a valid fix before setting
        if self.gps.gps_data["fix"] == "Valid":
            if self.point_A is None:
                self.point_A = (lat, lon)
                self.display_text("Point A set", f"Lat: {lat:.6f}")
            elif self.point_B is None:
                self.point_B = (lat, lon)
                distance = haversine(
                    self.point_A[0], self.point_A[1], self.point_B[0], self.point_B[1]
                )
                self.display_text("Distance:", f"{distance:.2f} m", "Press mode btn")
            else:
                # Reset points if both are already set
                self.point_A = self.point_B = None
                self.display_text("Points reset", "Set new Point A")
            self.enter_distance_mode()
        else:
            self.display_text("No GPS fix", "Try again later")
            self.gps.error_led.value(1)

    # Cycle through modes
    def cycle_mode(self):
        self.current_mode = (self.current_mode + 1) % len(self.MODES)
        self.enter_mode(self.current_mode)

    def handle_nav_button(self):
        if self.current_mode == 2:
            self.settings_index = (self.settings_index + 1) % len(self.SETTINGS_OPTIONS)
            self.update_settings_display()

    def toggle_display_power(self):
        if self.display_power_button is None:
            print("Error: Display power button not set")
            return

        if self.LCD_DISPLAY_SETTINGS["poweron"]:
            print("Preparing for deep sleep")
            self.display.poweroff()
            self.warning_led.value(1)
            self.LCD_DISPLAY_SETTINGS["poweron"] = False

            # Configure wake-up source
            esp32.wake_on_ext0(pin=self.display_power_button, level=0)

            print("Entering deep sleep")
            # Wait for 1 second to avoid immediate wake-up
            utime.sleep(1)

            # Enter deep sleep
            deepsleep()
        else:
            print("Waking up from deep sleep")
            self.display.poweron()
            self.warning_led.value(0)
            self.LCD_DISPLAY_SETTINGS["poweron"] = True
            # Reinitialize the display
            self.gps.init_gps()
            self.initialize_display()

    def update_settings_display(self):
        self.display.fill(0)
        self.display.text("Settings", 0, 0)
        start_index = max(0, self.settings_index - 1)
        end_index = min(len(self.SETTINGS_OPTIONS), start_index + 3)
        for i in range(start_index, end_index):
            option = self.SETTINGS_OPTIONS[i]
            prefix = ">" if i == self.settings_index else " "
            self.display.text(f"{prefix}{option}", 0, (i - start_index + 1) * 16)
        if self.settings_index == 0:
            value = f"Contrast: {self.LCD_DISPLAY_SETTINGS['contrast']}"
        elif self.settings_index == 1:
            value = f"Invert: {'On' if self.LCD_DISPLAY_SETTINGS['invert'] else 'Off'}"
        elif self.settings_index == 2:
            value = f"PWR Save: {'On' if self.DEVICE_SETTINGS['pwr_save'] else 'Off'}"
        else:
            value = ""
        self.display.text(value, 0, 56)
        self.display.show()

    # Apply a setting change from the settings menu
    def apply_setting_change(self):
        if self.settings_index == 0:
            self.LCD_DISPLAY_SETTINGS["contrast"] = (
                self.LCD_DISPLAY_SETTINGS["contrast"] % 15
            ) + 1
            self.display.contrast(self.LCD_DISPLAY_SETTINGS["contrast"])
        elif self.settings_index == 1:
            self.LCD_DISPLAY_SETTINGS["invert"] = not self.LCD_DISPLAY_SETTINGS[
                "invert"
            ]
            self.display.invert(self.LCD_DISPLAY_SETTINGS["invert"])
        elif self.settings_index == 2:
            self.DEVICE_SETTINGS["pwr_save"] = not self.DEVICE_SETTINGS["pwr_save"]
            # Valid settings are 20MHz, 40MHz, 80Mhz, 160MHz or 240MHz (ESP32)
            freq(40000000 if self.DEVICE_SETTINGS["pwr_save"] else 240000000)
        self.is_editing = not self.is_editing
