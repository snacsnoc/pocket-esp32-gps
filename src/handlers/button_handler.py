from machine import Pin, lightsleep


class ButtonHandler:
    def __init__(self, gps, display_handler):
        self.gps = gps
        self.display_handler = display_handler
        self.DEBOUNCE_DELAY = 100

        # Initialize buttons
        self.set_button = Pin(27, Pin.IN, Pin.PULL_UP)
        self.reset_mode_button = Pin(12, Pin.IN, Pin.PULL_UP)
        self.display_power_button = Pin(13, Pin.IN, Pin.PULL_UP)
        self.nav_button = Pin(14, Pin.IN, Pin.PULL_UP)

        # Attach interrupts
        self.set_button.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_any_button)
        self.reset_mode_button.irq(
            trigger=Pin.IRQ_FALLING, handler=self.handle_any_button
        )
        self.display_power_button.irq(
            trigger=Pin.IRQ_FALLING, handler=self.handle_any_button
        )
        self.nav_button.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_any_button)

        # Provide the display power button to the display handler
        self.display_handler.set_display_power_button(self.display_power_button)

    def handle_set_button(self, pin):
        self.display_handler.handle_set_button()

    def handle_mode_button(self, pin):
        self.display_handler.cycle_mode()

    # Handle the navigation button
    # Used to navigate within a menu
    def handle_nav_button(self, pin):
        self.display_handler.handle_nav_button()

    def handle_display_power(self, pin):
        self.display_handler.toggle_display_power()

    def handle_any_button(self, pin):
        lightsleep(self.DEBOUNCE_DELAY)
        if not pin.value():
            # Handle any button press for power management
            self.display_handler.handle_user_interaction()
            # Then handle the buttons normally
            if pin == self.set_button:
                self.handle_set_button(pin)
            elif pin == self.reset_mode_button:
                self.handle_mode_button(pin)
            elif pin == self.nav_button:
                self.handle_nav_button(pin)
            elif pin == self.display_power_button:
                self.handle_display_power(pin)

    # Disable pull-up resistors for buttons
    # Saves power when not in use (before deep sleep)
    def disable_pullups(self):
        self.set_button.init(pull=None)
        self.reset_mode_button.init(pull=None)
        self.display_power_button.init(pull=None)
        self.nav_button.init(pull=None)
