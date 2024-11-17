# Convert BMP images to PNG format
from PIL import Image
import os


def convert_bmp_to_png(input_dir, output_dir):
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".bmp"):
                bmp_path = os.path.join(root, file)
                img = Image.open(bmp_path)

                rel_path = os.path.relpath(root, input_dir)

                png_dir = os.path.join(output_dir, rel_path)

                os.makedirs(png_dir, exist_ok=True)
                png_path = os.path.join(png_dir, file.replace(".bmp", ".png"))

                img.save(png_path, "PNG")
                print(f"Converted {bmp_path} to {png_path}")


input_dir = "tiles"
output_dir = "tiles_png"

convert_bmp_to_png(input_dir, output_dir)
