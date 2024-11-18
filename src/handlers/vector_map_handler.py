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

        # Re-render the map with the new zoom level
        self.render()

    # Project latitude and longitude to display coordinates
    def project_coordinates(self, lat, lon):

        x = (lon - self.bbox[0]) / (self.bbox[2] - self.bbox[0]) * self.display.width
        y = (
            1 - (lat - self.bbox[1]) / (self.bbox[3] - self.bbox[1])
        ) * self.display.height

        # Apply zoom and clamp to display boundaries
        x = int(x * self.zoom_level)
        y = int(y * self.zoom_level)

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

    # Render all map features with the current zoom level
    def render(self):
        self.display.fill(0)
        for feature in self.features:
            if self.is_within_bounds(
                feature, self.bbox
            ):  # Filter features within bounds
                self.render_feature(feature)
        self.display.show()

    # Render the user's location on the map
    def render_user_location(self, lat, lon):
        x, y = self.project_coordinates(lat, lon)
        if 0 <= x < self.display.width and 0 <= y < self.display.height:
            # Draw a small triangle manually
            self.display.line(x, y - 2, x - 2, y + 2, 1)  # Left side
            self.display.line(x - 2, y + 2, x + 2, y + 2, 1)  # Base
            self.display.line(x + 2, y + 2, x, y - 2, 1)  # Right side
        self.display.show()

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
