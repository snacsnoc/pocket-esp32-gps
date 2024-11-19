# src/handlers/power_management.py


from machine import Timer, deepsleep
import esp32


class PowerManager:
    def __init__(self, display, gps, settings_handler, led_handler):
        self.display = display
        self.gps = gps
        self.settings_handler = settings_handler
        self.led_handler = led_handler  # Not used

        self.state = "active"
        self.idle_timeout = self.settings_handler.get_setting(
            "screen_timeout", "DEVICE_SETTINGS"
        )
        self.inactivity_timer = Timer(-1)
        self.prolonged_inactivity_timer = Timer(-1)

        # Wake from deep sleep button
        self.display_power_button = None

        self.init_timers()

    def init_timers(self):
        self.reset_inactivity_timer()

    def reset_inactivity_timer(self):
        if self.inactivity_timer:
            self.inactivity_timer.deinit()
        print(f"[DEBUG] Resetting inactivity timer. Timeout: {self.idle_timeout} ms")
        self.inactivity_timer.init(
            period=self.idle_timeout,
            mode=Timer.ONE_SHOT,
            callback=lambda t: self.enter_idle_mode(),
        )

    def reset_prolonged_inactivity_timer(self):
        if self.prolonged_inactivity_timer:
            self.prolonged_inactivity_timer.deinit()
        self.prolonged_inactivity_timer.init(
            period=300000,  # 5 minutes
            mode=Timer.ONE_SHOT,
            callback=lambda t: self.enter_deep_sleep(),
        )

    def enter_idle_mode(self):
        if self.state != "active":
            return
        print("[DEBUG] Entering Idle Mode")
        self.state = "idle"
        self.display.poweroff()
        self.gps.set_update_interval(30000)  # 30 seconds
        self.reset_prolonged_inactivity_timer()

    def exit_idle_mode(self):
        print("[DEBUG] Exiting Idle Mode")
        self.state = "active"
        self.display.poweron()
        self.gps.set_update_interval(1000)  # 1 second
        self.reset_inactivity_timer()
        if self.prolonged_inactivity_timer:
            self.prolonged_inactivity_timer.deinit()

    def enter_deep_sleep(self):
        print("[DEBUG] Entering Deep Sleep Mode")
        self.state = "deep_sleep"
        self.display.poweroff()
        self.gps.poweroff()
        esp32.wake_on_ext0(pin=self.display_power_button, level=0)
        deepsleep()

    def handle_user_interaction(self):
        print(f"[DEBUG] User interaction detected. State: {self.state}")
        if self.state == "idle":
            self.exit_idle_mode()
        else:
            self.reset_inactivity_timer()

    def set_display_power_button(self, button):
        self.display_power_button = button
