# src/handlers/vector_map_handler.py
# Used for vector map display

import ujson as json


class VectorMap:
    def __init__(self, display, geojson_file, bbox=None):
        self.display = display
        self.geojson_file = geojson_file
        self.bbox = bbox or [-180, -90, 180, 90]
        self.features = self.load_geojson()
        self.zoom_level = 1.0

    # Load the GeoJSON file and return features
    def load_geojson(self):
        try:
            with open(self.geojson_file, "r") as f:
                data = json.load(f)
            return data.get("features", [])
        except Exception as e:
            print(f"[ERROR] Failed to load GeoJSON: {e}")
            return []

    # Render the map at the current zoom level
    def set_zoom(self, zoom_level):
        # Clamp zoom level
        self.zoom_level = max(0.1, min(zoom_level, 10.0))

    # Project latitude and longitude to display coordinates
    def project_coordinates(self, lat, lon):

        # Calculate the fraction of the coordinate within the bounding box
        frac_x = (lon - self.bbox[0]) / (self.bbox[2] - self.bbox[0])
        frac_y = (lat - self.bbox[1]) / (self.bbox[3] - self.bbox[1])

        # Invert y-axis because display coordinates go from top to bottom
        frac_y = 1 - frac_y

        x = int(frac_x * self.display.width)
        y = int(frac_y * self.display.height)

        x = max(0, min(self.display.width - 1, x))
        y = max(0, min(self.display.height - 1, y))

        return x, y

    # Render a single GeoJSON feature
    def render_feature(self, feature):

        geom = feature.get("geometry", {})
        if not geom or "type" not in geom or "coordinates" not in geom:
            return

        coords = geom["coordinates"]
        geom_type = geom["type"]

        if geom_type == "Polygon":
            for ring in coords:
                self.render_line(ring)
        elif geom_type == "MultiPolygon":
            for polygon in coords:
                for ring in polygon:
                    self.render_line(ring)
        elif geom_type == "LineString":
            self.render_line(coords)
        elif geom_type == "MultiLineString":
            for line in coords:
                self.render_line(line)

    # Render a line based on a series of coordinates
    def render_line(self, coords):
        projected_points = [self.project_coordinates(lat, lon) for lon, lat in coords]
        for i in range(len(projected_points) - 1):
            x1, y1 = projected_points[i]
            x2, y2 = projected_points[i + 1]
            self.display.line(x1, y1, x2, y2, 1)  # Draw line on display
        # This saves 2KB of RAM
        projected_points.clear()

    # Render all map features with the current zoom level
    def render(self):
        self.display.fill(0)
        for feature in self.features:
            if self.is_within_bounds(
                feature, self.bbox
            ):  # Filter features within bounds
                self.render_feature(feature)
        # self.display.show() is called implicitly in the display_map() method in DisplayHandler

    def draw_filled_circle(self, x0, y0, radius, color):
        for y in range(-radius, radius + 1):
            for x in range(-radius, radius + 1):
                if x * x + y * y <= radius * radius:
                    self.display.pixel(x0 + x, y0 + y, color)

    # Update the bounding box for the map
    def update_bbox(self, bbox):
        self.bbox = bbox

    # Render the user's location on the map
    def render_user_location(self, lat, lon):
        x, y = self.project_coordinates(lat, lon)
        if 0 <= x < self.display.width and 0 <= y < self.display.height:

            # Draw a small triangle manually
            self.display.line(x, y - 2, x - 2, y + 2, 1)  # Left side
            self.display.line(x - 2, y + 2, x + 2, y + 2, 1)  # Base
            self.display.line(x + 2, y + 2, x, y - 2, 1)  # Right side

    # self.display.show() is called implicitly in the display_map() method in DisplayHandler

    # Check if a feature's coordinates are within display bounds
    def is_within_bounds(self, feature, bounds):
        try:
            geometry = feature.get("geometry", {})
            geom_type = geometry.get("type", "")
            coordinates = geometry.get("coordinates", [])

            if geom_type in ["Polygon", "MultiPolygon"]:
                for polygon in coordinates:
                    rings = polygon if geom_type == "MultiPolygon" else [polygon]
                    for ring in rings:
                        for lon, lat in ring:
                            if (
                                bounds[0] <= lon <= bounds[2]
                                and bounds[1] <= lat <= bounds[3]
                            ):
                                return True

            elif geom_type in ["LineString", "MultiLineString"]:
                lines = coordinates if geom_type == "MultiLineString" else [coordinates]
                for line in lines:
                    for lon, lat in line:
                        if (
                            bounds[0] <= lon <= bounds[2]
                            and bounds[1] <= lat <= bounds[3]
                        ):
                            return True

            elif geom_type == "Point":
                lon, lat = coordinates
                return bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]

        except Exception as e:
            print(f"[ERROR] Failed to check bounds for feature: {e}")

        return False

    # Calculate a default bounding box around the user's location.
    @staticmethod
    def calculate_default_bbox(user_lat, user_lon):
        lat_delta = 0.05  # ~5 km north/south
        lon_delta = 0.05  # ~4-5 km east/west depending on latitude

        # Calculate the bounding box
        min_lat = user_lat - lat_delta
        max_lat = user_lat + lat_delta
        min_lon = user_lon - lon_delta
        max_lon = user_lon + lon_delta

        bbox = [min_lon, min_lat, max_lon, max_lat]

        return bbox

    @staticmethod
    def calculate_bbox_for_zoom(lat, lon, zoom_level):
        # Define a base size for the bbox (in degrees)
        base_size = 0.1  # Adjust this value as needed
        # Adjust the size based on the zoom level
        size = base_size / zoom_level
        min_lat = lat - size / 2
        max_lat = lat + size / 2
        min_lon = lon - size / 2
        max_lon = lon + size / 2
        return [min_lon, min_lat, max_lon, max_lat]
