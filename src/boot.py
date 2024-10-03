# boot.py

from machine import (
    Pin,
    I2C,
    freq,
    ADC,
    lightsleep,
    reset_cause,
    DEEPSLEEP_RESET,
    RTC,
    Timer,
)

import lib.ssd1306 as ssd1306
from handlers.gps_handler import GPSHandler
from handlers.settings_handler import SettingsHandler
from handlers.button_handler import ButtonHandler
from handlers.display_handler import DisplayHandler
from handlers.led_handler import LEDHandler


# Initialize I2C and display
i2c = I2C(scl=Pin(22), sda=Pin(21))
led_handler = LEDHandler()
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# Initialize Settings Handler
settings_handler = SettingsHandler()
# Initialize GPS module handler
gps = GPSHandler(led_handler)
gps.init_gps()

# Initialize Display Handler
display_handler = DisplayHandler(gps, i2c, led_handler, settings_handler)

# Initialize Button Handler
button_handler = ButtonHandler(gps, display_handler)

# Get boot cycle count from RTC memory
rtc = RTC()
boot_count = rtc.memory()

if boot_count is None or len(boot_count) == 0:
    # First boot
    boot_count = 1
else:
    boot_count = int(boot_count.decode()) + 1

# Store the new boot count in RTC memory
rtc.memory(str(boot_count).encode())

print(f"Boot cycle: {boot_count}")


# Boot into power save mode instead of showing initial splash screen
if settings_handler.get_setting("pwr_save_boot", "DEVICE_SETTINGS"):
    # Set CPU frequency to 40MHz for power saving
    freq(40000000)
    # ADC power down
    adc = ADC(0)
    adc.atten(ADC.ATTN_0DB)
    adc.width(ADC.WIDTH_9BIT)

    # Delay turning on display upon boot for 5 seconds
    display.poweroff()
    display.contrast(1)
    lightsleep(5000)
    display.poweron()

# Show boot screen only on the first boot, not on wake from deep sleep
elif reset_cause() != DEEPSLEEP_RESET:
    display_handler.display_boot_screen()

if reset_cause() == DEEPSLEEP_RESET:
    print("Woke from deep sleep")
    lightsleep(500)
    display_on = True
    gps.init_gps()
    display.poweron()


# Built-in ESP32 LED
builtin_led = Pin(2, Pin.OUT)
builtin_led.value(0)

disp_timeout_timer = Timer(2)

# Screen timeout timer
disp_timeout_timer.init(
    mode=Timer.ONE_SHOT,
    period=settings_handler.get_setting("screen_timeout", "DEVICE_SETTINGS"),
    callback=display_handler.toggle_display_power,
)

while True:
    try:
        gps_data = gps.read_gps()
        if gps_data:
            display_handler.enter_mode(display_handler.current_mode)
        else:
            print("No GPS data received")
        lightsleep(100)
    except Exception as e:
        print(f"Error in main loop: {e}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error args: {e.args}")
