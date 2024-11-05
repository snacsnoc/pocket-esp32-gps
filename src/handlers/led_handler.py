from machine import Pin
import utime


class LEDHandler:
    def __init__(self):
        self.mode_led = Pin(23, Pin.OUT)
        self.warning_led = Pin(18, Pin.OUT)
        self.success_led = Pin(19, Pin.OUT)
        self.error_led = Pin(5, Pin.OUT)
        # self.built_in_led = Pin(2, Pin.OUT)
        # Initialize all LEDs to off
        self.mode_led.value(0)
        self.warning_led.value(0)
        self.success_led.value(0)
        self.error_led.value(0)
        # self.built_in_led.value(0)

    def set_mode_led(self, value):
        self.mode_led.value(value)

    def toggle_mode_led(self):
        self.mode_led.value(not self.mode_led.value())

    def set_warning_led(self, value):
        self.warning_led.value(value)

    def set_success_led(self, value):
        self.success_led.value(value)

    def set_error_led(self, value):
        self.error_led.value(value)

    def blink_led(self, led, times=1, on_time=100, off_time=100):
        for _ in range(times):
            led.value(1)
            utime.sleep_ms(on_time)
            led.value(0)
            utime.sleep_ms(off_time)
