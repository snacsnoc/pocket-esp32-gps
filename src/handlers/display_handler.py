import ssd1306
from machine import freq, lightsleep, I2C, Pin
import gc
import os
import esp32
import esp
import utime
from utils.haversine import haversine

from handlers.vector_map_handler import VectorMap

from handlers.power_management import PowerManager


class DisplayHandler:
    MODES = [
        "GPS Display",
        "Map Display",
        "Distance Calc",
        "Settings",
        "About",
    ]
    SETTINGS_OPTIONS = [
        "Contrast",
        "Invert Display",
        "Power Save Mode",
        "Enable LEDs",
    ]

    def __init__(self, gps, led_handler, settings_handler):
        self.gps = gps
        self.i2c, self.display, self.display_power_button = self.initialize_display()

        self.display_power_button = None
        self.led_handler = led_handler
        self.settings_handler = settings_handler
        self.power_manager = PowerManager(
            self.display, self.gps, self.settings_handler, self.led_handler
        )
        self.power_manager.set_display_power_button(self.display_power_button)

        self.current_mode = 0
        self.settings_index = 0
        self.is_editing = False
        self.point_A = None
        self.point_B = None
        self.vector_map_file = "/simplified_out_0229.geojson"
        self.zoom_level = 2.0
        self.prev_zoom_level = self.zoom_level
        self.prev_lat = None
        self.prev_lon = None
        self.location_update_threshold = 25
        self.vector_map = VectorMap(self.display, self.vector_map_file, bbox=None)
        self.vector_map.set_zoom(self.zoom_level)
        self.apply_display_settings_and_mode()

    def set_display_power_button(self, button):
        self.power_manager.set_display_power_button(button)

    def handle_user_interaction(self):
        self.power_manager.handle_user_interaction()

    # Initialize I2C, the OLED display, and the display power button
    @staticmethod
    def initialize_display():
        i2c = I2C(scl=Pin(22), sda=Pin(21))
        display = ssd1306.SSD1306_I2C(128, 64, i2c)
        display_power_button = Pin(13, Pin.IN, Pin.PULL_UP)  # Wake from sleep button
        return i2c, display, display_power_button

    def apply_display_settings_and_mode(self):
        self.display.contrast(
            self.settings_handler.get_setting("contrast", "LCD_SETTINGS")
        )
        self.display.invert(self.settings_handler.get_setting("invert", "LCD_SETTINGS"))
        self.enter_mode(self.current_mode)

    # Enter a mode and run the associated function
    def enter_mode(self, mode):
        self.current_mode = mode
        mode_functions = {
            0: self.show_main_gps_display,
            1: self.display_map,
            2: self.enter_distance_mode,
            3: self.enter_settings_mode,
            4: self.display_about,
        }
        self.led_handler.set_mode_led(1 if mode > 0 else 0)
        mode_functions.get(mode, self.show_main_gps_display)()
        gc.collect()

    # Main GPS display
    def show_main_gps_display(self):
        self.update_gps_display()

    # Secondary GPS display
    def show_second_gps_display(self):
        self.gps_second_display()
        gc.collect()

    # Update the GPS main display
    def update_gps_display(self):
        self.display.fill(0)
        fix_status = self.gps.gps_data.get("fix", "No Fix")
        self.display.text(f"Fix: {fix_status}", 0, 0)

        if fix_status in ["Valid", "Partial"]:
            lat = self.gps.gps_data.get("lat")
            lon = self.gps.gps_data.get("lon")
            alt = self.gps.gps_data.get("alt")
            sats = self.gps.gps_data.get("sats")

            if lat is not None:
                self.display.text(f"Lat: {lat:.6f}", 0, 20)
            if lon is not None:
                self.display.text(f"Lon: {lon:.6f}", 0, 30)
            if alt is not None:
                self.display.text(f"Alt: {alt}m", 0, 40)
            if sats is not None:
                self.display.text(f"Sats: {sats}", 0, 50)
        else:
            self.display.text("Waiting for fix...", 0, 30)

        self.display.show()
        self.led_handler.toggle_mode_led()

    def gps_second_display(self):
        self.display.fill(0)
        # Display UTC time if available
        if self.gps.gps_data["utc_time"] and self.gps.gps_data["utc_date"] is not None:
            self.display.text("Timezone: UTC", 0, 0)
            self.display.text(f"Time: {self.gps.gps_data['utc_time']}", 0, 10)
            self.display.text(f"Date: {self.gps.gps_data['utc_date']}", 0, 20)

        # Display horizontal dilution of precision if available
        if "hdop" in self.gps.gps_data and self.gps.gps_data["hdop"] is not None:
            self.display.text(f"hdop: {self.gps.gps_data['hdop']}m", 0, 30)

        # Display PPS if available
        if "pps" in self.gps.gps_data and self.gps.gps_data["pps"] is not None:
            self.display.text(f"PPS: {self.gps.gps_data['pps']}us", 0, 48)
        self.display.show()
        # Wait for 3 seconds before returning to main display
        lightsleep(3000)

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

    # Display the about screen
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
        except Exception as e:
            self.display.text("Temp info N/A", 0, 40)
            print(f"[DEBUG] Error: {e}")
        self.display.text("Press NAV btn for more", 0, 50)
        self.display.show()

    # Display device storage information
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
        except Exception as e:
            self.display.text("Storage info N/A", 0, 40)
            print(f"[DEBUG] Error: {e}")
        self.display.show()
        utime.sleep(2.5)

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

        gc.collect()

    # Display the map
    def show_map_display(self):
        self.display_map()

    # Handle nav button press to change zoom level when on map display
    def update_map_zoom(self):
        # Toggle between 3.0, 2.0 and 1.0 and 0.5 zoom levels
        if self.zoom_level == 3.0:
            self.zoom_level = 2.0
        elif self.zoom_level == 2.0:
            self.zoom_level = 1.0
        elif self.zoom_level == 1.0:
            self.zoom_level = 0.5
        else:
            self.zoom_level = 3.0

        print(f"[DEBUG] Setting zoom level to {self.zoom_level}")
        self.display_map()
        self.prev_zoom_level = None
        gc.collect()

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
        elif self.settings_index == 1:
            enable_leds = self.settings_handler.get_setting(
                "enable_leds", "DEVICE_SETTINGS"
            )
            value = f"LEDs: {'On' if enable_leds else 'Off'}"
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
            freq(40000000 if new_pwr_save else 160000000)
        elif self.settings_index == 3:
            # Toggle LED status
            enable_leds = self.settings_handler.get_setting(
                "enable_leds", "DEVICE_SETTINGS"
            )
            new_enable_leds = not enable_leds
            self.settings_handler.update_setting(
                "enable_leds", new_enable_leds, "DEVICE_SETTINGS"
            )

        self.is_editing = not self.is_editing

    def display_map(self):
        lat = self.gps.gps_data.get("lat")
        lon = self.gps.gps_data.get("lon")
        fix = self.gps.gps_data.get("fix")

        if fix == "No Fix" or lat is None or lon is None:
            self.display.fill(0)
            self.display_text("No GPS data", "available")
            self.display.show()
            lightsleep(2000)
            # Transition to next screen so user can access other screens
            self.current_mode = (self.current_mode + 1) % len(self.MODES)
            return

        # Free up memory before rendering
        gc.collect()

        # Determine if we need to update the map
        # Minimum distance threshold for location update
        # is set in self.location_update_threshold in meters
        location_changed = False
        if self.prev_lat is None or self.prev_lon is None:
            location_changed = True
        else:
            distance = haversine(self.prev_lat, self.prev_lon, lat, lon)
            if distance > self.location_update_threshold:
                location_changed = True

        zoom_level_changed = self.zoom_level != self.prev_zoom_level

        if location_changed or zoom_level_changed:
            # Recalculate bbox based on current location and zoom level
            default_bbox = VectorMap.calculate_bbox_for_zoom(lat, lon, self.zoom_level)
            print(f"[DEBUG] Updated BBox: {default_bbox}")
            # Update the bbox in the existing VectorMap
            self.vector_map.update_bbox(default_bbox)
            # Update previous location and zoom level
            self.prev_lat = lat
            self.prev_lon = lon
            self.prev_zoom_level = self.zoom_level
            gc.collect()

        self.display.fill(0)
        # Render the map features
        self.vector_map.render()
        # Render the user's location
        self.vector_map.render_user_location(lat, lon)

        # Update the display __once__
        self.display.show()
        gc.collect()

        # Utility methods

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

    # Toggle display power and enter deep sleep
    def toggle_display_power(self, timer=None):
        print(f"[DEBUG] Toggling display power with timer: {timer}")
        if self.power_manager.state == "deep_sleep":
            # Debounce to avoid immediate wake-up
            utime.sleep_ms(500)
            self.power_manager.wake_from_deep_sleep()
        else:
            utime.sleep_ms(300)
            self.power_manager.enter_deep_sleep()

    # Cycle through modes
    def cycle_mode(self):
        self.current_mode = (self.current_mode + 1) % len(self.MODES)
        self.enter_mode(self.current_mode)

    # Handle navigation button per mode
    def handle_nav_button(self):
        if self.current_mode == 0:
            self.gps_second_display()
        elif self.current_mode == 1:
            self.update_map_zoom()
        elif self.current_mode == 3:
            self.settings_index = (self.settings_index + 1) % len(self.SETTINGS_OPTIONS)
            self.update_settings_display()
        elif self.current_mode == 4:
            self.display_device_storage()

    # Handle the SET button press per mode
    def handle_set_button(self):
        if self.current_mode == 1:
            self.set_distance_point()
        elif self.current_mode == 3:
            self.apply_setting_change()
        # SET button has no function on the main screen
        if not self.current_mode == 0:
            self.update_settings_display()
