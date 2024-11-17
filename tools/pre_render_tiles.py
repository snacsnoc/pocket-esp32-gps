# Pre-render tiles for a map

import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from PIL import Image, ImageDraw
import mercantile
import json
import os

# Load hillshade raster
hillshade = rasterio.open("kootenay maps/viz.USGS30m_hillshade.tif")

# Load GeoJSON vector data
# Use mapshaper.org to simplify the GeoJSON file
with open("kootenay maps/gray_creek_simple_export.geojson") as f:
    geojson = json.load(f)


ZOOM = 15
# Tile size in pixels
TILE_SIZE = 256


def get_tile_image_rgb(tile):
    bbox = mercantile.bounds(tile)
    try:
        window = from_bounds(
            bbox.west, bbox.south, bbox.east, bbox.north, transform=hillshade.transform
        )
        data = hillshade.read(
            1,
            window=window,
            out_shape=(TILE_SIZE, TILE_SIZE),
            resampling=Resampling.bilinear,
        )
        # Normalize data to 0-255
        data_min = data.min()
        data_max = data.max()
        if data_max - data_min > 0:
            data = ((data - data_min) / (data_max - data_min) * 255).astype("uint8")
        else:
            data = ((data - data_min) * 255).astype("uint8")
        img = Image.fromarray(data, mode="L").convert("RGB")
        return img
    except Exception as e:
        # Hillshade data is not available
        print(f"Warning: Could not read hillshade data for tile {tile}: {e}")
        img = Image.new("RGB", (TILE_SIZE, TILE_SIZE), "white")
        return img


def get_tile_image(tile):
    bbox = mercantile.bounds(tile)
    try:
        window = from_bounds(
            bbox.west, bbox.south, bbox.east, bbox.north, transform=hillshade.transform
        )
        data = hillshade.read(
            1,
            window=window,
            out_shape=(TILE_SIZE, TILE_SIZE),
            resampling=Resampling.bilinear,
        )
        # Normalize data to 0-255
        data_min = data.min()
        data_max = data.max()
        if data_max - data_min > 0:
            data = ((data - data_min) / (data_max - data_min) * 255).astype("uint8")
        else:
            data = ((data - data_min) * 255).astype("uint8")
        # Convert to monochrome (1-bit)
        img = Image.fromarray(data, mode="L").convert("1")
        return img
    except Exception as e:
        print(f"Warning: Could not read hillshade data for tile {tile}: {e}")
        img = Image.new("1", (TILE_SIZE, TILE_SIZE), "white")
        return img


def draw_features(img, tile):
    draw = ImageDraw.Draw(img)
    bbox = mercantile.bounds(tile)
    min_lon, min_lat, max_lon, max_lat = bbox.west, bbox.south, bbox.east, bbox.north

    def lonlat_to_pixel(lon, lat):
        x = int((lon - min_lon) / (max_lon - min_lon) * TILE_SIZE)
        y = int((max_lat - lat) / (max_lat - min_lat) * TILE_SIZE)
        return x, y

    for feature in geojson["features"]:
        geom = feature["geometry"]
        geom_type = geom["type"]
        coords = geom["coordinates"]
        props = feature.get("properties", {})

        if geom_type == "Point":
            lon, lat = coords
            x, y = lonlat_to_pixel(lon, lat)
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill="red")

        elif geom_type == "LineString":
            pixel_coords = []
            for lon, lat in coords:
                x, y = lonlat_to_pixel(lon, lat)
                pixel_coords.append((x, y))
            if len(pixel_coords) > 1:
                draw.line(pixel_coords, fill="blue", width=2)

        elif geom_type == "Polygon":
            for ring in coords:
                pixel_coords = []
                for lon, lat in ring:
                    x, y = lonlat_to_pixel(lon, lat)
                    pixel_coords.append((x, y))
                fill_color = "lightgreen"
                if props.get("natural") == "water":
                    fill_color = "lightblue"
                draw.polygon(pixel_coords, outline="green", fill=fill_color)

        elif geom_type == "MultiLineString":
            for line in coords:
                pixel_coords = []
                for lon, lat in line:
                    x, y = lonlat_to_pixel(lon, lat)
                    pixel_coords.append((x, y))
                if len(pixel_coords) > 1:
                    draw.line(pixel_coords, fill="blue", width=2)

        elif geom_type == "MultiPolygon":
            for polygon in coords:
                for ring in polygon:
                    pixel_coords = []
                    for lon, lat in ring:
                        x, y = lonlat_to_pixel(lon, lat)
                        pixel_coords.append((x, y))
                    fill_color = "lightgreen"
                    if props.get("natural") == "water":
                        fill_color = "lightblue"
                    draw.polygon(pixel_coords, outline="green", fill=fill_color)


# Determine tiles covering the area based on GeoJSON features
tiles = set()


def add_tile(lon, lat):
    tile = mercantile.tile(lon, lat, ZOOM)
    tiles.add((tile.x, tile.y, tile.z))


for feature in geojson["features"]:
    geom = feature["geometry"]
    geom_type = geom["type"]
    coords = geom["coordinates"]

    if geom_type == "Point":
        lon, lat = coords
        add_tile(lon, lat)

    elif geom_type == "LineString":
        for lon, lat in coords:
            add_tile(lon, lat)

    elif geom_type == "Polygon":
        for ring in coords:
            for lon, lat in ring:
                add_tile(lon, lat)

    elif geom_type == "MultiLineString":
        for line in coords:
            for lon, lat in line:
                add_tile(lon, lat)

    elif geom_type == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                for lon, lat in ring:
                    add_tile(lon, lat)

print(f"Total tiles to generate: {len(tiles)}")

# Generate and save tiles
for tile_tuple in tiles:
    x, y, z = tile_tuple
    tile = mercantile.Tile(x, y, z)
    img = get_tile_image(tile)
    draw_features(img, tile)
    tile_dir = f"tiles/{z}/{x}"
    os.makedirs(tile_dir, exist_ok=True)
    tile_path = f"{tile_dir}/{y}.bmp"
    img.save(tile_path)
    print(f"Saved tile: {tile_path}")
