# boot.py

from machine import (
    Pin,
    I2C,
    freq,
    ADC,
    lightsleep,
    reset_cause,
    DEEPSLEEP_RESET,
)
import lib.ssd1306 as ssd1306
from handlers.gps_handler import GPSHandler
from handlers.button_handler import ButtonHandler
from handlers.display_handler import DisplayHandler
from handlers.led_handler import LEDHandler

POWERSAVE_BOOT = False

# Initialize I2C and display
i2c = I2C(scl=Pin(22), sda=Pin(21))
led_handler = LEDHandler()
display = ssd1306.SSD1306_I2C(128, 64, i2c)

gps = GPSHandler(led_handler)
gps.init_gps()
# Initialize Display Handler
display_handler = DisplayHandler(gps, i2c, led_handler)

# Initialize Button Handler
button_handler = ButtonHandler(gps, display_handler)


if POWERSAVE_BOOT:
    # Set CPU frequency to 80MHz for power saving
    freq(80000000)
    # ADC power down
    adc = ADC(0)
    adc.atten(ADC.ATTN_0DB)
    adc.width(ADC.WIDTH_9BIT)

    # Delay turning on display upon boot for 5 seconds
    display.poweroff()
    display.contrast(1)
    lightsleep(5000)
    display.poweron()


if reset_cause() == DEEPSLEEP_RESET:
    print("Woke from deep sleep")
    lightsleep(500)
    display_on = True
    gps.init_gps()
    display.poweron()


# Built-in ESP32 LED
builtin_led = Pin(2, Pin.OUT)
builtin_led.value(0)


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
