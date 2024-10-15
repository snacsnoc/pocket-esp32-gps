from machine import Pin, Timer
import time


class ButtonHandler:
    def __init__(self, gps, display_handler):
        self.gps = gps
        self.display_handler = display_handler
        self.DEBOUNCE_DELAY = 150
        self.debounce_timer = Timer(1)

        # Initialize buttons
        self.set_button = Pin(27, Pin.IN, Pin.PULL_UP)
        self.reset_mode_button = Pin(12, Pin.IN, Pin.PULL_UP)
        self.display_power_button = Pin(13, Pin.IN, Pin.PULL_UP)
        self.nav_button = Pin(14, Pin.IN, Pin.PULL_UP)

        # Attach interrupts
        self.set_button.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_set_button)
        self.reset_mode_button.irq(
            trigger=Pin.IRQ_FALLING, handler=self.handle_reset_button
        )
        self.display_power_button.irq(
            trigger=Pin.IRQ_FALLING, handler=self.handle_display_power
        )
        self.nav_button.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_nav_button)

        # Provide the display power button to the display handler
        self.display_handler.set_display_power_button(self.display_power_button)

    def handle_set_button(self, pin):
        time.sleep_ms(self.DEBOUNCE_DELAY)
        if not pin.value():
            self.display_handler.handle_set_button()

    def handle_reset_button(self, pin):
        time.sleep_ms(self.DEBOUNCE_DELAY)
        if not pin.value():
            print("[DEBUG] Button still pressed after debounce")
            self.display_handler.cycle_mode()

    # Handle the navigation button
    # Used to navigate within a menu
    def handle_nav_button(self, pin):
        time.sleep_ms(self.DEBOUNCE_DELAY)
        if not pin.value():
            self.display_handler.handle_nav_button()

    def handle_display_power(self, pin):
        time.sleep_ms(self.DEBOUNCE_DELAY)
        if not pin.value():
            self.display_handler.toggle_display_power()

    # Disable pull-up resistors for buttons
    # Saves power when not in use (before deep sleep)
    def disable_pullups(self):
        self.set_button.init(pull=None)
        self.reset_mode_button.init(pull=None)
        self.display_power_button.init(pull=None)
        self.nav_button.init(pull=None)
