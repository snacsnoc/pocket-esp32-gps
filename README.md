# ESP32 GPS Data Display

This project uses an ESP32 microcontroller to read data from a GPS module and display it on an OLED screen. 
It also calculates the distance between two set points using GPS coordinates.


## Hardware Requirements

- ESP32 development board
  - ESP8266 can be used but the UART RX pins must be reassigned
- GPS module (compatible with UART) - U7M module used
- SSD1306 OLED display
- Buttons for setting points and switching modes
- LEDs for status indication
- A smile on your face

## Pin Configuration

- GPS Module: RX on pin 16
- OLED Display: SCL on pin 22, SDA on pin 21
- Set Button: pin 13
- Reset/Mode Button: pin 14
- Mode LED: pin 12
- Success LED: pin 26
- Error LED: pin 27
- PPS (Pulse Per Second) from GPS module input: pin 4

## Usage

1. Connect the hardware components according to the pin configuration.
2. Upload the `main.py` and `gps_handler.py` files to your ESP32.
3. Power on the device.
4. Drink a glass of water to stay hydrated.
5. The device will start in GPS display mode, showing real-time GPS data.
6. Press the reset/mode button to switch to distance calculation mode.
7. In distance mode, press the set button to mark point A, then again to mark point B.
8. The device will display the calculated distance between the two points.

## Files

- `main.py`: Main program logic, display handling, and button interactions
- `gps_handler.py`: GPS data parsing and management

## Dependencies

- `machine`: For hardware control
- `ssd1306`: For OLED display control
- `math`: For distance calculations

## Note

The GPS module works best when you have a clear view of the sky.