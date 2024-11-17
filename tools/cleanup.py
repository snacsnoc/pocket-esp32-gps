# Delete a directory and all its contents recursively
# Use with mpremote
# mpremote connect /dev/tty.usbserial-0001 + run cleanup.py

import os


def cleanup(base):
    for entry in os.ilistdir(base):
        entry_path = f"{base}/{entry[0]}"
        if entry[1] & 0x4000:  # Directory
            cleanup(entry_path)
            os.rmdir(entry_path)
        else:
            os.remove(entry_path)


cleanup("tiles_grayscale_bmp")  # Replace with your directory
os.rmdir("tiles_optimized_bmp")
