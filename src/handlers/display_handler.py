import lib.ssd1306 as ssd1306
from machine import Pin, I2C, freq, deepsleep
import gc
import os
import esp32
import esp
import utime
from utils.haversine import haversine


class DisplayHandler:
    def __init__(self, gps, i2c, led_handler, settings_handler):
        self.gps = gps
        self.display = ssd1306.SSD1306_I2C(128, 64, i2c)
        self.display_power_button = None
        self.led_handler = led_handler
        self.settings_handler = settings_handler
        self.current_mode = 0
        self.MODES = ["GPS Display", "Distance Calc", "Settings", "About"]
        self.settings_index = 0
        self.SETTINGS_OPTIONS = ["Contrast", "Invert Display", "Power Save Mode"]
        self.is_editing = False
        self.point_A = None
        self.point_B = None
        self.initialize_display()

    def initialize_display(self):
        self.display.contrast(
            self.settings_handler.get_setting("contrast", "LCD_SETTINGS")
        )
        self.display.invert(self.settings_handler.get_setting("invert", "LCD_SETTINGS"))
        self.enter_mode(self.current_mode)

    def set_display_power_button(self, button):
        self.display_power_button = button

    def enter_mode(self, mode):
        self.current_mode = mode
        if mode == 0:
            self.show_main_gps_display()
        elif mode == 1:
            self.led_handler.set_mode_led(1)
            self.enter_distance_mode()
        elif mode == 2:
            self.led_handler.set_mode_led(1)
            self.enter_settings_mode()
        elif mode == 3:
            self.led_handler.set_mode_led(1)
            self.display_about()

    def show_main_gps_display(self):
        self.update_gps_display()

    def show_second_gps_display(self):
        self.gps_second_display()

    # Update the GPS main display
    def update_gps_display(self):
        self.display.fill(0)
        fix_status = self.gps.gps_data["fix"]

        # Display fix status
        self.display.text(f"Fix: {fix_status}", 0, 0)

        # Display available data based on fix status
        if fix_status == "Valid" or fix_status == "Partial":
            if "lat" in self.gps.gps_data and self.gps.gps_data["lat"] is not None:
                self.display.text(f"Lat: {self.gps.gps_data['lat']:.6f}", 0, 20)
            if "lon" in self.gps.gps_data and self.gps.gps_data["lon"] is not None:
                self.display.text(f"Lon: {self.gps.gps_data['lon']:.6f}", 0, 30)
            if "alt" in self.gps.gps_data and self.gps.gps_data["alt"] is not None:
                self.display.text(f"Alt: {self.gps.gps_data['alt']}m", 0, 40)
            if "sats" in self.gps.gps_data:
                self.display.text(f"Sats: {self.gps.gps_data['sats']}", 0, 50)
        else:
            self.display.text("Waiting for fix...", 0, 30)

        self.display.show()
        self.led_handler.toggle_mode_led()

    def gps_second_display(self):
        self.display.fill(0)
        # Display UTC time if available
        if self.gps.gps_data["utc_time"] and self.gps.gps_data["utc_date"] is not None:
            self.display.text(f"Time: {self.gps.gps_data['utc_time']}", 0, 0)
            self.display.text(f"Date: {self.gps.gps_data['utc_date']}", 0, 9)
        # Display PPS if available
        if "pps" in self.gps.gps_data and self.gps.gps_data["pps"] is not None:
            self.display.text(f"PPS: {self.gps.gps_data['pps']}us", 0, 48)
        self.display.show()
        # Wait for 2.5 seconds before returning to main display
        utime.sleep(2.5)

    # Entry point for distance mode
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

    # Entry point for settings mode
    def enter_settings_mode(self):
        self.is_editing = False
        self.update_settings_display()

    def display_about(self):
        self.display.fill(0)
        self.display.text("Pocket ESP32 GPS", 0, 0)
        self.display.text("v1.0 By Easton", 0, 9)
        cpu_freq = freq() / 1_000_000
        self.display.text(f"CPU: {cpu_freq:.0f} MHz", 0, 20)
        free_ram = gc.mem_free() / 1024
        self.display.text(f"RAM: {free_ram:.1f} KB", 0, 30)
        try:
            temp_fahrenheit = esp32.raw_temperature()
            temp_celsius = (temp_fahrenheit - 32) * 5 / 9
            self.display.text(f"Temp: {temp_celsius:.2f} C", 0, 40)
        except:
            self.display.text("Temp info N/A", 0, 40)
        self.display.text("Press NAV btn for more", 0, 50)
        self.display.show()

    def display_device_storage(self):
        self.display.fill(0)
        self.display.text("Device Storage", 0, 0)
        try:
            storage_info = os.statvfs("/")
            total_space = storage_info[0] * storage_info[2] / (1024 * 1024)
            free_space = storage_info[0] * storage_info[3] / (1024 * 1024)
            flash_size = esp.flash_size()
            self.display.text(f"Storage: {free_space:.1f}/{total_space:.1f}MB", 0, 40)
            self.display.text(f"Flash: {flash_size}B", 0, 50)
        except:
            self.display.text("Storage info N/A", 0, 40)
        self.display.show()
        utime.sleep(2.5)

    # Initial boot screen
    def display_boot_screen(self):
        self.display.fill(0)
        self.display.text("Pocket ESP32 GPS", 0, 9)
        self.display.show()

        # Simulate a booting progress bar animation
        for i in range(0, 101, 10):  # Increase in steps of 10
            self.display.fill_rect(10, 30, i, 10, 1)

            # Clear the area where the percentage will be displayed
            self.display.fill_rect(10, 45, 128, 10, 0)

            self.display.text(f"Booting... {i}%", 10, 45)
            self.display.show()

            # Cycle through the LEDs
            if i % 20 == 0:
                self.led_handler.set_warning_led(1)
                utime.sleep(0.1)
                self.led_handler.set_warning_led(0)
                self.led_handler.set_success_led(1)
                utime.sleep(0.1)
                self.led_handler.set_success_led(0)
                self.led_handler.set_mode_led(1)
                utime.sleep(0.1)
                self.led_handler.set_mode_led(0)
                self.led_handler.set_error_led(1)
                utime.sleep(0.1)
                self.led_handler.set_error_led(0)

            # Pause for animation
            utime.sleep(0.25)

        # Clear the progress bar once boot is complete
        self.display.fill(0)
        self.display.text("Boot Complete", 10, 30)
        self.display.show()
        utime.sleep(1)

    # Display two lines of text on the display
    def display_text(self, line1, line2=None, line3=None):
        self.display.fill(0)
        self.display.fill_rect(0, 0, 128, 48, 0)
        self.display.text(line1, 0, 0)
        if line2:
            self.display.text(line2, 0, 16)
        if line3:
            self.display.text(line3, 0, 24)
        self.display.show()

    # Handle the SET button press per mode
    def handle_set_button(self):
        if self.current_mode == 1:
            self.set_distance_point()
        elif self.current_mode == 2:
            self.apply_setting_change()
        # SET button has no function on the main screen
        if not self.current_mode == 0:
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
            self.led_handler.set_error_led(1)

    # Cycle through modes
    def cycle_mode(self):
        self.current_mode = (self.current_mode + 1) % len(self.MODES)
        self.enter_mode(self.current_mode)

    # Handle navigation button per mode
    def handle_nav_button(self):
        if self.current_mode == 0:
            self.gps_second_display()
        elif self.current_mode == 2:
            self.settings_index = (self.settings_index + 1) % len(self.SETTINGS_OPTIONS)
            self.update_settings_display()
        elif self.current_mode == 3:
            self.display_device_storage()

    # Toggle display power and enter deep sleep
    def toggle_display_power(self, timer=None):
        print(f"[DEBUG] Toggling display power with timer: {timer}")

        if self.display_power_button is None:
            print("Error: Display power button not set")
            return

        if self.settings_handler.get_setting("poweron", "LCD_SETTINGS"):
            self.display_text("Entering deep", "sleep in 1.5s")
            utime.sleep(1.5)
            print("Preparing for deep sleep")
            self.display.poweroff()
            self.led_handler.set_warning_led(1)
            self.settings_handler.update_setting("poweron", False, "LCD_SETTINGS")

            # Configure wake-up source
            esp32.wake_on_ext0(pin=self.display_power_button, level=0)

            print("[DEBUG] Entering deep sleep")

            # Wait for 1 second to avoid immediate wake-up
            utime.sleep(1)

            # Enter deep sleep
            deepsleep()
        else:
            print("[DEBUG] Waking up from deep sleep")
            self.display.poweron()
            self.led_handler.set_warning_led(0)
            self.settings_handler.update_setting("poweron", True, "LCD_SETTINGS")

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

        # Display the current value of the selected setting
        if self.settings_index == 0:
            contrast = self.settings_handler.get_setting("contrast", "LCD_SETTINGS")
            value = f"Contrast: {contrast}"
        elif self.settings_index == 1:
            invert = self.settings_handler.get_setting("invert", "LCD_SETTINGS")
            value = f"Invert: {'On' if invert else 'Off'}"
        elif self.settings_index == 2:
            pwr_save = self.settings_handler.get_setting("pwr_save", "DEVICE_SETTINGS")
            value = f"PWR Save: {'On' if pwr_save else 'Off'}"
        else:
            value = ""

        self.display.text(value, 0, 56)
        self.display.show()

    # Apply a setting change from the settings menu
    def apply_setting_change(self):
        if self.settings_index == 0:
            # Update contrast setting
            current_contrast = self.settings_handler.get_setting(
                "contrast", "LCD_SETTINGS"
            )
            new_contrast = (current_contrast % 15) + 1
            self.settings_handler.update_setting(
                "contrast", new_contrast, "LCD_SETTINGS"
            )
            self.display.contrast(new_contrast)
        elif self.settings_index == 1:
            # Toggle invert display
            invert = self.settings_handler.get_setting("invert", "LCD_SETTINGS")
            new_invert = not invert
            self.settings_handler.update_setting("invert", new_invert, "LCD_SETTINGS")
            self.display.invert(new_invert)
        elif self.settings_index == 2:
            # Toggle power save mode
            pwr_save = self.settings_handler.get_setting("pwr_save", "DEVICE_SETTINGS")
            new_pwr_save = not pwr_save
            self.settings_handler.update_setting(
                "pwr_save", new_pwr_save, "DEVICE_SETTINGS"
            )
            # Valid settings are 20MHz, 40MHz, 80Mhz, 160MHz or 240MHz (ESP32)
            freq(40000000 if new_pwr_save else 240000000)

        self.is_editing = not self.is_editing
