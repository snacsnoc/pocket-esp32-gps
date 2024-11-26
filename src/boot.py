# boot.py

from machine import (
    Pin,
    freq,
    ADC,
    lightsleep,
    reset_cause,
    DEEPSLEEP_RESET,
    RTC,
    Timer,
)


from handlers.gps_handler import GPSHandler
from handlers.settings_handler import SettingsHandler
from handlers.button_handler import ButtonHandler
from handlers.display_handler import DisplayHandler
from handlers.led_handler import LEDHandler


def initialize_handlers():
    settings_handler = SettingsHandler()
    led_handler = LEDHandler(settings_handler)
    gps = GPSHandler(led_handler)
    gps.init_gps()
    display_handler = DisplayHandler(gps, led_handler, settings_handler)
    button_handler = ButtonHandler(gps, display_handler)
    return settings_handler, led_handler, gps, display_handler, button_handler


def manage_boot_cycle():
    # Get boot cycle count from RTC memory
    rtc = RTC()
    boot_count = rtc.memory()
    if not boot_count:
        boot_count = 1
    else:
        boot_count = int(boot_count.decode()) + 1
    # Store the new boot count in RTC memory
    rtc.memory(str(boot_count).encode())
    print(f"[DEBUG] Boot cycle: {boot_count}")
    return boot_count


# Boot into power save mode instead of showing initial splash screen
def enter_power_save_mode(settings_handler, display):
    if settings_handler.get_setting("pwr_save_boot", "DEVICE_SETTINGS"):
        # Set CPU frequency to 40MHz for power saving
        freq(40000000)
        # ADC power down
        adc = ADC(0)
        adc.atten(ADC.ATTN_0DB)
        adc.width(ADC.WIDTH_9BIT)
        display.poweroff()
        display.contrast(1)
        # Delay turning on display upon boot for 5 seconds
        lightsleep(5000)
        display.poweron()


# Show boot screen only on the first boot, not on wake from deep sleep
def handle_boot_screen(display_handler):
    if reset_cause() != DEEPSLEEP_RESET:
        display_handler.display_boot_screen()


def handle_deep_sleep(power_manager):
    if reset_cause() == DEEPSLEEP_RESET:
        print("[DEBUG] Waking from deep sleep")
        power_manager.wake_from_deep_sleep()


# Built-in ESP32 LED
def initialize_builtin_led():
    builtin_led = Pin(2, Pin.OUT)
    builtin_led.value(0)
    return builtin_led


def setup_screen_timeout(settings_handler, power_manager):
    disp_timer = Timer(2)
    disp_timer.init(
        mode=Timer.ONE_SHOT,
        period=settings_handler.get_setting("screen_timeout_ms", "DEVICE_SETTINGS"),
        callback=lambda t: power_manager.enter_idle_mode(),
    )
    return disp_timer


def main():
    (
        settings_handler,
        led_handler,
        gps,
        display_handler,
        button_handler,
    ) = initialize_handlers()

    power_manager = display_handler.power_manager
    manage_boot_cycle()
    enter_power_save_mode(settings_handler, display_handler)

    handle_deep_sleep(power_manager)

    handle_boot_screen(display_handler)
    initialize_builtin_led()
    setup_screen_timeout(settings_handler, power_manager)

    while True:
        try:
            display_handler.enter_mode(display_handler.current_mode)
            if display_handler.current_mode in [0, 1, 2]:  # Modes requiring GPS
                gps.read_gps()
            lightsleep(110)
        except Exception as e:
            print(f"Error: {e} ({type(e).__name__})")


if __name__ == "__main__":
    main()
