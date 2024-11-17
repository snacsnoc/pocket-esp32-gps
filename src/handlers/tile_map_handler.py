# src/handlers/tile_map_handler.py

"""
This class is responsible for handling the mapping functionality of the device using pre-rendered map tiles.
It provides methods to display the map, calculate tile coordinates, and handle the display of the map.

This is mostly a placeholder for the future implementation of the map display, since I am using a monochrome display :(
The SSD1306 can handle rendering of said map tiles, but looks pretty bad.
"""

import gc
import time
import math
from framebuf import FrameBuffer, MONO_HLSB, MONO_VLSB


class TileMappingHandler:
    def __init__(self, display, gps, grayscale=True):
        self.display = display
        self.gps = gps
        self.GRAYSCALE = grayscale

    def display_map(self):
        lat = self.gps.gps_data.get("lat")
        lon = self.gps.gps_data.get("lon")

        if lat is None or lon is None:
            self.display.fill(0)
            self.display.text("No GPS Data", 0, 10)
            self.display.show()
            print(f"[DEBUG] No GPS data. Lat: {lat}, Lon: {lon}")
            return

        # Match zoom level to the tile size
        zoom = 15
        xtile, ytile = self.latlon_to_tile(lat, lon, zoom)

        max_tile = 2**zoom - 1
        xtile = max(0, min(xtile, max_tile))
        ytile = max(0, min(ytile, max_tile))
        print(f"[DEBUG] Current tile: {xtile}, {ytile}")

        # Load and display the tile
        tile_path = f"/tiles_grayscale_bmp/{zoom}/{xtile}/{ytile}.bmp"
        if not self.load_and_display_tile(tile_path):
            self.display.fill(0)
            self.display.text("Tile Not Found", 0, 10)
            self.display.show()
            return

        # Overlay user location on the tile
        self.overlay_user_location(lat, lon, zoom, xtile, ytile)

    def simulate_grayscale(self, buf, width, height, levels=16):
        # Validate buffer size
        if len(buf) != width * height:
            raise ValueError(
                f"Buffer size mismatch: len(buf)={len(buf)}, expected={width * height}"
            )

        print(f"[DEBUG] Simulating grayscale with levels={levels}")
        print(f"[DEBUG] Non-zero values in buffer: {sum(1 for b in buf if b > 0)}")

        # Find max brightness in the buffer for scaling
        max_brightness = max(buf)
        print(f"[DEBUG] Max brightness in buffer: {max_brightness}")

        if max_brightness == 0:
            print("[WARNING] Buffer is all zeros. Nothing to display.")
            return

        # Scale buffer values to levels
        scaled_buf = bytearray(
            int((pixel / max_brightness) * (levels - 1)) if pixel > 0 else 0
            for pixel in buf
        )
        # Temporal dithering cycles
        for cycle in range(levels):
            self.display.fill(0)
            for y in range(height):
                for x in range(width):
                    idx = y * width + x
                    if scaled_buf[idx] > cycle:
                        self.display.pixel(x, y, 1)
            self.display.show()
            # Short delay for persistence blending
            time.sleep(0.01)

    def load_and_display_tile(self, tile_path):
        try:
            with open(tile_path, "rb") as f:
                # Read BMP header
                header = f.read(54)
                if header[0:2] != b"BM":
                    print("[DEBUG] Not a valid BMP file")
                    return False

                offset = int.from_bytes(header[10:14], "little")
                width = int.from_bytes(header[18:22], "little")
                height = int.from_bytes(header[22:26], "little")
                bits_per_pixel = int.from_bytes(header[28:30], "little")

                if bits_per_pixel not in [8, 4]:
                    print("Only 8-bit or 4-bit BMP files are supported")
                    print(f"Bits per pixel: {bits_per_pixel}")
                    return False

                # Ensure dimensions match display size
                if width != 128 or height != 64:
                    print("Tile dimensions do not match display size (128x64)")
                    return False

                # Prepare framebuffer buffer for 1-bit per pixel
                # buf = bytearray(128 * 64 // 8)

                # Prepare buffer for 4-bit grayscale data
                # One byte per pixel (unpacked 4-bit)
                # buf = bytearray(128 * 64)
                buf = bytearray(width * height)

                f.seek(offset)

                if bits_per_pixel == 8:
                    # Process 8-bit BMP
                    row_size = width  # One byte per pixel
                    padding = (4 - (row_size % 4)) % 4

                    # Grayscale fix for a monochrome display
                    for y in range(height):
                        row = f.read(row_size)
                        for x in range(width):
                            # Normalize grayscale value to binary
                            pixel_value = 1 if row[x] > 127 else 0
                            buf[y * width + x] = pixel_value
                        f.read(padding)

                elif bits_per_pixel == 4:
                    # Process 4-bit BMP

                    # Two pixels per byte
                    row_size = (width + 1) // 2
                    padding = (4 - (row_size % 4)) % 4

                    for y in range(height):
                        row = f.read(row_size)
                        for x in range(width // 2):
                            byte = row[x]
                            # Scale high nibble
                            buf[y * width + (x * 2)] = (byte >> 4) * 17
                            # Scale low nibble
                            buf[y * width + (x * 2) + 1] = (byte & 0x0F) * 17
                        f.read(padding)

                # Purely for debugging
                if self.GRAYSCALE:
                    print(f"GRAY SCALE")

                    print(f"[DEBUG] First 100 bytes of buffer: {buf[:100]}")
                    print(
                        f"[DEBUG] Non-zero values in buffer: {sum(1 for b in buf if b > 0)}"
                    )
                    # test_buf = bytearray([i % 256 for i in range(128 * 64)])
                    self.simulate_grayscale(buf, 128, 64)

                else:
                    self.display.fill(0)
                    # Load framebuffer and display
                    # MONO_VLSB seemed to display better than MONO_HMSB
                    fb = FrameBuffer(buf, 128, 64, MONO_VLSB)
                    self.display.blit(fb, 0, 0)
                    self.display.show()

            return True
        except OSError as e:
            print(f"Error loading tile {tile_path}: {e}")
            return False
        finally:
            gc.collect()

    # Simple nearest-neighbor resize
    def resize_framebuffer(self, fb, src_width, src_height, dest_width, dest_height):

        src_buf = fb.buf
        dest_buf = bytearray(dest_width * dest_height)
        for y in range(dest_height):
            for x in range(dest_width):
                src_x = int(x * src_width / dest_width)
                src_y = int(y * src_height / dest_height)
                if src_x >= src_width:
                    src_x = src_width - 1
                if src_y >= src_height:
                    src_y = src_height - 1
                pixel = fb.pixel(src_x, src_y)
                dest_buf[y * dest_width + x] = pixel
        return FrameBuffer(dest_buf, dest_width, dest_height, MONO_HLSB)

    # Calculate pixel position within the tile
    def overlay_user_location(self, lat, lon, zoom, xtile, ytile):

        x, y = self.calculate_pixel_position(lat, lon, zoom, xtile, ytile)
        print(f"[DEBUG] User location pixel: ({x}, {y})")

        # Draw a small pixel to represent the user's location
        if 0 <= x < 128 and 0 <= y < 64:
            self.display.pixel(x, y, 1)
            self.display.show()

    # Calculate tile boundaries
    def calculate_pixel_position(self, lat, lon, zoom, xtile, ytile):

        n = 2**zoom
        tile_lon_min = xtile / n * 360.0 - 180.0
        tile_lon_max = (xtile + 1) / n * 360.0 - 180.0

        tile_lat_min = math.degrees(
            math.atan(math.sinh(math.pi * (1 - 2 * (ytile + 1) / n)))
        )
        tile_lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ytile / n))))

        # Calculate relative position within the tile
        x_ratio = (lon - tile_lon_min) / (tile_lon_max - tile_lon_min)
        y_ratio = (tile_lat_max - lat) / (tile_lat_max - tile_lat_min)

        # Clamp ratios between 0 and 1
        x_ratio = max(0, min(1, x_ratio))
        y_ratio = max(0, min(1, y_ratio))

        x_pixel = int(x_ratio * 128)
        y_pixel = int(y_ratio * 64)

        return x_pixel, y_pixel

    # Convert latitude and longitude to tile coordinates
    def latlon_to_tile(self, lat, lon, zoom):
        lat_rad = math.radians(lat)
        n = 2**zoom
        xtile = int((lon + 180) / 360 * n)
        ytile = int(
            (1 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)
            / 2
            * n
        )
        return xtile, ytile
