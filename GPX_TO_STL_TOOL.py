import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import gpxpy
import requests
from shapely.geometry import Point, Polygon
import math
import time
from stl import mesh
from mpl_toolkits.mplot3d import Axes3D
import argparse
import os
import sys
class TerrainGenerator:
    def __init__(self, gpx_file_path, resolution=40, shape="octagon", size=100, 
                 elevation_multiplier=1.0, track_color="red", track_width=2,
                 base_thickness=2, output_dir="output", verbose=True,
                 export_track_stl=False):
        """
        Initialize the terrain generator with user settings.
        Args:
            gpx_file_path: Path to the GPX file
            resolution: Number of points along each axis (higher = more detailed but slower)
            shape: Shape of the terrain ("hexagon", "circle", "rectangle")
            size: Size of the model in mm
            elevation_multiplier: Factor to multiply elevation values
            track_color: Color of the track line
            track_width: Width of the track line
            base_thickness: Minimum thickness of the base in mm
            output_dir: Directory to save output files
            verbose: Whether to print progress messages
            export_track_stl: Whether to export the track as a STL file
        """
        self.gpx_file_path = gpx_file_path
        self.resolution = resolution
        self.shape = shape
        self.size = size
        self.elevation_multiplier = elevation_multiplier
        self.track_color = track_color
        self.track_width = track_width
        self.base_thickness = base_thickness
        self.output_dir = output_dir
        self.verbose = verbose
        self.export_track_stl = export_track_stl
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        self.track_points = []
        self.terrain_points = []
        self.elevation_data = []
        self.terrain_mesh = None
        self.min_lat = float('inf')
        self.max_lat = float('-inf')
        self.min_lon = float('inf')
        self.max_lon = float('-inf')
        self.min_ele = float('inf')
        self.max_ele = float('-inf')
    def log(self, message):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    def read_gpx(self):
        """Read and parse the GPX file to extract track points."""
        self.log(f"Reading GPX file: {self.gpx_file_path}")
        if not os.path.exists(self.gpx_file_path):
            raise FileNotFoundError(f"GPX file not found: {self.gpx_file_path}")
        with open(self.gpx_file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        lat = point.latitude
                        lon = point.longitude
                        ele = point.elevation if point.elevation is not None else 0
                        self.min_lat = min(self.min_lat, lat)
                        self.max_lat = max(self.max_lat, lat)
                        self.min_lon = min(self.min_lon, lon)
                        self.max_lon = max(self.max_lon, lon)
                        self.min_ele = min(self.min_ele, ele)
                        self.max_ele = max(self.max_ele, ele)
                        self.track_points.append((lat, lon, ele))
        if not self.track_points:
            raise ValueError("No track points found in the GPX file")
        self.log(f"Loaded {len(self.track_points)} track points")
        self.log(f"Latitude range: {self.min_lat:.6f} to {self.max_lat:.6f}")
        self.log(f"Longitude range: {self.min_lon:.6f} to {self.max_lon:.6f}")
        self.log(f"Elevation range: {self.min_ele:.2f}m to {self.max_ele:.2f}m")
    def generate_boundary_shape(self):
        """Generate the boundary shape around the track."""
        self.log(f"Generating {self.shape} boundary with resolution {self.resolution}...")
        center_lat = (self.min_lat + self.max_lat) / 2
        center_lon = (self.min_lon + self.max_lon) / 2
        lat_radius = (self.max_lat - self.min_lat) / 2 * 1.2
        lon_radius = (self.max_lon - self.min_lon) / 2 * 1.2
        radius = max(lat_radius, lon_radius)
        if self.shape == "octagon":
            vertices = []
            for i in range(8):
                angle = 2 * math.pi * i / 8
                lat = center_lat + radius * math.cos(angle)
                lon = center_lon + radius * math.sin(angle)
                vertices.append((lat, lon))
            self._generate_grid_in_polygon(vertices)
        elif self.shape == "hexagon":
            vertices = []
            for i in range(6):
                angle = 2 * math.pi * i / 6
                lat = center_lat + radius * math.cos(angle)
                lon = center_lon + radius * math.sin(angle)
                vertices.append((lat, lon))
            self._generate_grid_in_polygon(vertices)
        elif self.shape == "circle":
            self.terrain_points = []
            step = radius / self.resolution
            for i in range(-self.resolution, self.resolution + 1):
                for j in range(-self.resolution, self.resolution + 1):
                    lat = center_lat + i * step
                    lon = center_lon + j * step
                    if ((lat - center_lat) / lat_radius) ** 2 + ((lon - center_lon) / lon_radius) ** 2 <= 1:
                        self.terrain_points.append((lat, lon))
        elif self.shape == "rectangle":
            self.terrain_points = []
            lat_step = 2 * lat_radius / self.resolution
            lon_step = 2 * lon_radius / self.resolution
            for i in range(self.resolution + 1):
                for j in range(self.resolution + 1):
                    lat = self.min_lat - lat_radius * 0.2 + i * lat_step
                    lon = self.min_lon - lon_radius * 0.2 + j * lon_step
                    self.terrain_points.append((lat, lon))
        else:
            raise ValueError(f"Unsupported shape: {self.shape}")
        self.log(f"Generated {len(self.terrain_points)} terrain points")
    def _generate_grid_in_polygon(self, vertices):
        """Generate a grid of points within a polygon defined by vertices."""
        polygon = Polygon(vertices)
        min_lat = min(v[0] for v in vertices)
        max_lat = max(v[0] for v in vertices)
        min_lon = min(v[1] for v in vertices)
        max_lon = max(v[1] for v in vertices)
        step_lat = (max_lat - min_lat) / (self.resolution - 1)
        step_lon = (max_lon - min_lon) / (self.resolution - 1)
        for i in range(self.resolution):
            for j in range(self.resolution):
                lat = min_lat + step_lat * i
                lon = min_lon + step_lon * j
                point = Point(lat, lon)
                if polygon.contains(point):
                    self.terrain_points.append((lat, lon))
    def fetch_elevation_data(self):
        """Fetch elevation data for all terrain points."""
        self.log("Fetching elevation data...")
        batch_size = 100
        for i in range(0, len(self.terrain_points), batch_size):
            batch = self.terrain_points[i:i+batch_size]
            locations = "|".join([f"{lat},{lon}" for lat, lon in batch])
            url = f"https://api.opentopodata.org/v1/srtm30m?locations={locations}"
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    self.log(f"API error: {response.status_code} - {response.text}")
                    for j, (lat, lon) in enumerate(batch):
                        nearest_point = min(self.track_points, 
                                           key=lambda p: (p[0]-lat)**2 + (p[1]-lon)**2)
                        elevation = nearest_point[2]
                        self.elevation_data.append((lat, lon, elevation))
                    continue
                data = response.json()
                for j, result in enumerate(data['results']):
                    elevation = result['elevation']
                    lat, lon = batch[j]
                    self.elevation_data.append((lat, lon, elevation))
                    if elevation is not None:
                        self.min_ele = min(self.min_ele, elevation)
                        self.max_ele = max(self.max_ele, elevation)
                self.log(f"Fetched {len(batch)} points ({i+len(batch)}/{len(self.terrain_points)})")
                time.sleep(1)
            except Exception as e:
                self.log(f"Error fetching elevation data: {e}")
                for j, (lat, lon) in enumerate(batch):
                    nearest_point = min(self.track_points, 
                                       key=lambda p: (p[0]-lat)**2 + (p[1]-lon)**2)
                    elevation = nearest_point[2]
                    self.elevation_data.append((lat, lon, elevation))
        self.log(f"Fetched elevation data for {len(self.elevation_data)} points")
        self.log(f"Elevation range: {self.min_ele:.2f}m to {self.max_ele:.2f}m")
    def generate_3d_model(self):
        """Generate a 3D model from the elevation data."""
        self.log("Generating 3D model...")
        x_values = [self._lon_to_x(lon) for _, lon, _ in self.elevation_data]
        y_values = [self._lat_to_y(lat) for lat, _, _ in self.elevation_data]
        z_values = [ele * self.elevation_multiplier for _, _, ele in self.elevation_data]
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)
        z_min, z_max = min(z_values), max(z_values)
        scale_xy = self.size / max(x_max - x_min, y_max - y_min)
        x_scaled = [(x - x_min) * scale_xy for x in x_values]
        y_scaled = [(y - y_min) * scale_xy for y in y_values]
        scale_z = self.size / 10
        z_scaled = [self.base_thickness + (z - z_min) * scale_z for z in z_values]
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(x_scaled, y_scaled, z_scaled, 
                       c=z_scaled, cmap='terrain', 
                       s=20, alpha=0.8)
        cbar = fig.colorbar(scatter, ax=ax, label='Elevation (mm)')
        if self.track_points:
            track_x = [(self._lon_to_x(lon) - x_min) * scale_xy for _, lon, _ in self.track_points]
            track_y = [(self._lat_to_y(lat) - y_min) * scale_xy for lat, _, _ in self.track_points]
            track_z = [self.base_thickness + (ele - z_min) * scale_z for _, _, ele in self.track_points]
            ax.plot(track_x, track_y, track_z, color=self.track_color, 
                    linewidth=self.track_width, label='Track')
            ax.legend()
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title('3D Terrain Model')
        base_filename = os.path.splitext(os.path.basename(self.gpx_file_path))[0]
        output_file = os.path.join(self.output_dir, f"{base_filename}_terrain_preview.png")
        plt.savefig(output_file, dpi=300)
        plt.close()
        self.log(f"3D model preview saved as {output_file}")
        self._create_2d_heatmap(x_scaled, y_scaled, z_scaled, base_filename)
        self._create_stl_file(x_scaled, y_scaled, z_scaled, base_filename)
        if self.export_track_stl and self.track_points:
            self._create_track_stl_file(x_scaled, y_scaled, z_scaled, 
                                    track_x, track_y, track_z, base_filename)
    def _create_2d_heatmap(self, x_scaled, y_scaled, z_scaled, base_filename):
        """Create a 2D heatmap showing elevation with top-down view."""
        fig, ax = plt.subplots(figsize=(10, 8))
        scatter = ax.scatter(x_scaled, y_scaled, c=z_scaled, cmap='terrain', s=20, alpha=0.8)
        cbar = fig.colorbar(scatter, ax=ax, label='Elevation (mm)')
        if self.track_points:
            x_min = min([self._lon_to_x(lon) for _, lon, _ in self.elevation_data])
            y_min = min([self._lat_to_y(lat) for lat, _, _ in self.elevation_data])
            scale_xy = self.size / max(
                max([self._lon_to_x(lon) for _, lon, _ in self.elevation_data]) - x_min,
                max([self._lat_to_y(lat) for lat, _, _ in self.elevation_data]) - y_min
            )
            track_x = [(self._lon_to_x(lon) - x_min) * scale_xy for _, lon, _ in self.track_points]
            track_y = [(self._lat_to_y(lat) - y_min) * scale_xy for lat, _, _ in self.track_points]
            ax.plot(track_x, track_y, color=self.track_color, 
                    linewidth=self.track_width, label='Track')
            ax.legend()
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_title('Terrain Elevation Heatmap')
        ax.set_aspect('equal')
        output_file = os.path.join(self.output_dir, f"{base_filename}_terrain_heatmap.png")
        plt.savefig(output_file, dpi=300)
        plt.close()
        self.log(f"2D heatmap saved as {output_file}")
    def _create_stl_file(self, x_scaled, y_scaled, z_scaled, base_filename):
        """Create an STL file for 3D printing with proper terrain scaling."""
        self.log("Generating STL file with realistic terrain heights...")
        try:
            grid_size = 150
            min_x, max_x = min(x_scaled), max(x_scaled)
            min_y, max_y = min(y_scaled), max(y_scaled)
            x_grid = np.linspace(min_x, max_x, grid_size)
            y_grid = np.linspace(min_y, max_y, grid_size)
            X, Y = np.meshgrid(x_grid, y_grid)
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            width = max_x - min_x
            height = max_y - min_y
            radius = max(width, height) / 2 * 1.15
            if self.shape == "octagon":
                vertices = []
                for i in range(8):
                    angle = 2 * math.pi * i / 8
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                    vertices.append((x, y))
                boundary_polygon = Polygon(vertices)
            elif self.shape == "hexagon":
                vertices = []
                for i in range(6):
                    angle = 2 * math.pi * i / 6
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                    vertices.append((x, y))
                boundary_polygon = Polygon(vertices)
            elif self.shape == "circle":
                vertices = []
                for i in range(32):
                    angle = 2 * math.pi * i / 32
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                    vertices.append((x, y))
                boundary_polygon = Polygon(vertices)
            else:
                margin_x = width * 0.075
                margin_y = height * 0.075
                vertices = [
                    (min_x - margin_x, min_y - margin_y), 
                    (max_x + margin_x, min_y - margin_y),
                    (max_x + margin_x, max_y + margin_y), 
                    (min_x - margin_x, max_y + margin_y)
                ]
                boundary_polygon = Polygon(vertices)
            track_x = [self._lon_to_x(lon) for _, lon, _ in self.track_points]
            track_y = [self._lat_to_y(lat) for lat, _, _ in self.track_points]
            track_x_scaled = [(x - self._lon_to_x(self.min_lon)) / 
                            (self._lon_to_x(self.max_lon) - self._lon_to_x(self.min_lon)) * width + min_x 
                            for x in track_x]
            track_y_scaled = [(y - self._lat_to_y(self.min_lat)) / 
                            (self._lat_to_y(self.max_lat) - self._lat_to_y(self.min_lat)) * height + min_y 
                            for y in track_y]
            points_outside = False
            for tx, ty in zip(track_x_scaled, track_y_scaled):
                if not boundary_polygon.contains(Point(tx, ty)):
                    points_outside = True
                    break
            if points_outside:
                self.log("Track extends beyond initial boundary shape. Increasing boundary size.")
                radius *= 1.25
                if self.shape == "octagon":
                    vertices = []
                    for i in range(8):
                        angle = 2 * math.pi * i / 8
                        x = center_x + radius * math.cos(angle)
                        y = center_y + radius * math.sin(angle)
                        vertices.append((x, y))
                    boundary_polygon = Polygon(vertices)
                elif self.shape == "hexagon":
                    vertices = []
                    for i in range(6):
                        angle = 2 * math.pi * i / 6
                        x = center_x + radius * math.cos(angle)
                        y = center_y + radius * math.sin(angle)
                        vertices.append((x, y))
                    boundary_polygon = Polygon(vertices)
                elif self.shape == "circle":
                    vertices = []
                    for i in range(32):
                        angle = 2 * math.pi * i / 32
                        x = center_x + radius * math.cos(angle)
                        y = center_y + radius * math.sin(angle)
                        vertices.append((x, y))
                    boundary_polygon = Polygon(vertices)
                else:
                    margin_x = width * 0.15
                    margin_y = height * 0.15
                    vertices = [
                        (min_x - margin_x, min_y - margin_y), 
                        (max_x + margin_x, min_y - margin_y),
                        (max_x + margin_x, max_y + margin_y), 
                        (min_x - margin_x, max_y + margin_y)
                    ]
                    boundary_polygon = Polygon(vertices)
            inside_mask = np.zeros((grid_size, grid_size), dtype=bool)
            for i in range(grid_size):
                for j in range(grid_size):
                    inside_mask[i, j] = boundary_polygon.contains(Point(X[i, j], Y[i, j]))
            from scipy.interpolate import griddata
            points = np.column_stack((x_scaled, y_scaled))
            min_z = min(z_scaled)
            max_z = max(z_scaled)
            z_range = max_z - min_z
            scaled_z_values = [self.base_thickness + (z - min_z) * (self.size * 0.10 / z_range) for z in z_scaled]
            Z = griddata(points, scaled_z_values, (X, Y), method='linear')
            if np.isnan(Z).any():
                Z_nearest = griddata(points, scaled_z_values, (X, Y), method='nearest')
                Z[np.isnan(Z)] = Z_nearest[np.isnan(Z)]
            from scipy.ndimage import gaussian_filter
            Z = gaussian_filter(Z, sigma=0.5)
            track_width = width / 40
            track_height = 0.8
            if not self.export_track_stl:
                for i in range(grid_size):
                    for j in range(grid_size):
                        if inside_mask[i, j]:
                            min_dist = float('inf')
                            for tx, ty in zip(track_x_scaled, track_y_scaled):
                                dist = np.sqrt((X[i, j] - tx)**2 + (Y[i, j] - ty)**2)
                                min_dist = min(min_dist, dist)
                            if min_dist < track_width:
                                Z[i, j] += track_height * (1 - min_dist / track_width)
            vertices = []
            faces = []
            vertex_indices = np.full((grid_size, grid_size), -1)
            vertex_count = 0
            for i in range(grid_size):
                for j in range(grid_size):
                    if inside_mask[i, j]:
                        vertices.append([X[i, j], Y[i, j], Z[i, j]])
                        vertex_indices[i, j] = vertex_count
                        vertex_count += 1
            bottom_offset = vertex_count
            for i in range(grid_size):
                for j in range(grid_size):
                    if inside_mask[i, j]:
                        vertices.append([X[i, j], Y[i, j], 0])
                        vertex_count += 1
            for i in range(grid_size - 1):
                for j in range(grid_size - 1):
                    if (inside_mask[i, j] and inside_mask[i+1, j] and 
                        inside_mask[i, j+1] and inside_mask[i+1, j+1]):
                        v1 = vertex_indices[i, j]
                        v2 = vertex_indices[i, j+1]
                        v3 = vertex_indices[i+1, j]
                        v4 = vertex_indices[i+1, j+1]
                        faces.append([v1, v2, v3])
                        faces.append([v3, v2, v4])
            for i in range(grid_size - 1):
                for j in range(grid_size - 1):
                    if (inside_mask[i, j] and inside_mask[i+1, j] and 
                        inside_mask[i, j+1] and inside_mask[i+1, j+1]):
                        v1 = bottom_offset + vertex_indices[i, j]
                        v2 = bottom_offset + vertex_indices[i, j+1]
                        v3 = bottom_offset + vertex_indices[i+1, j]
                        v4 = bottom_offset + vertex_indices[i+1, j+1]
                        faces.append([v1, v3, v2])
                        faces.append([v3, v4, v2])
            edge_points = []
            for i in range(grid_size):
                for j in range(grid_size):
                    if inside_mask[i, j]:
                        is_edge = False
                        for ni, nj in [(i+1,j), (i-1,j), (i,j+1), (i,j-1)]:
                            if (ni < 0 or ni >= grid_size or nj < 0 or nj >= grid_size or 
                                not inside_mask[ni, nj]):
                                is_edge = True
                                break
                        if is_edge:
                            edge_points.append((i, j))
            for i, j in edge_points:
                top_vertex = vertex_indices[i, j]
                bottom_vertex = bottom_offset + top_vertex
                for ni, nj in [(i+1,j), (i,j+1), (i-1,j), (i,j-1)]:
                    if (0 <= ni < grid_size and 0 <= nj < grid_size and 
                        inside_mask[ni, nj]):
                        top_neighbor = vertex_indices[ni, nj]
                        bottom_neighbor = bottom_offset + top_neighbor
                        if ni > i or (ni == i and nj > j):
                            faces.append([top_vertex, top_neighbor, bottom_vertex])
                            faces.append([bottom_vertex, top_neighbor, bottom_neighbor])
                        else:
                            faces.append([top_vertex, bottom_vertex, top_neighbor])
                            faces.append([bottom_vertex, bottom_neighbor, top_neighbor])
            vertices = np.array(vertices)
            faces = np.array(faces)
            self.log(f"Creating STL mesh with {len(vertices)} vertices and {len(faces)} faces")
            terrain_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
            for i, face in enumerate(faces):
                for j in range(3):
                    terrain_mesh.vectors[i][j] = vertices[face[j]]
            output_file = os.path.join(self.output_dir, f"{base_filename}_terrain_model.stl")
            terrain_mesh.save(output_file)
            self.log(f"STL file saved as {output_file}")
        except Exception as e:
            self.log(f"Error creating STL file: {e}")
            import traceback
            self.log(traceback.format_exc())
            self.log("Falling back to simplified terrain model...")
            try:
                grid_size = 20
                x_range = max(x_scaled) - min(x_scaled)
                y_range = max(y_scaled) - min(y_scaled)
                x_min, y_min = min(x_scaled), min(y_scaled)
                X = np.array([[x_min + i * x_range / (grid_size-1) for j in range(grid_size)] 
                            for i in range(grid_size)])
                Y = np.array([[y_min + j * y_range / (grid_size-1) for j in range(grid_size)] 
                            for i in range(grid_size)])
                Z = np.ones((grid_size, grid_size)) * self.base_thickness
                for i in range(grid_size):
                    for j in range(grid_size):
                        dist = ((i - grid_size/2)**2 + (j - grid_size/2)**2) / ((grid_size/2)**2)
                        if dist < 1:
                            Z[i, j] += (1 - dist) * self.size / 10
                vertices = []
                faces = []
                for i in range(grid_size):
                    for j in range(grid_size):
                        vertices.append([X[i, j], Y[i, j], Z[i, j]])
                for i in range(grid_size):
                    for j in range(grid_size):
                        vertices.append([X[i, j], Y[i, j], 0])
                for i in range(grid_size - 1):
                    for j in range(grid_size - 1):
                        v1 = i * grid_size + j
                        v2 = i * grid_size + (j + 1)
                        v3 = (i + 1) * grid_size + j
                        faces.append([v1, v2, v3])
                        v1 = (i + 1) * grid_size + j
                        v2 = i * grid_size + (j + 1)
                        v3 = (i + 1) * grid_size + (j + 1)
                        faces.append([v1, v2, v3])
                offset = grid_size * grid_size
                for i in range(grid_size - 1):
                    for j in range(grid_size - 1):
                        v1 = offset + i * grid_size + j
                        v2 = offset + (i + 1) * grid_size + j
                        v3 = offset + i * grid_size + (j + 1)
                        faces.append([v1, v2, v3])
                        v1 = offset + i * grid_size + (j + 1)
                        v2 = offset + (i + 1) * grid_size + j
                        v3 = offset + (i + 1) * grid_size + (j + 1)
                        faces.append([v1, v2, v3])
                for i in range(grid_size - 1):
                    v1 = (grid_size - 1) * grid_size + i
                    v2 = (grid_size - 1) * grid_size + (i + 1)
                    v3 = offset + (grid_size - 1) * grid_size + i
                    v4 = offset + (grid_size - 1) * grid_size + (i + 1)
                    faces.append([v1, v2, v3])
                    faces.append([v2, v4, v3])
                    v1 = i
                    v2 = i + 1
                    v3 = offset + i
                    v4 = offset + (i + 1)
                    faces.append([v1, v3, v2])
                    faces.append([v2, v3, v4])
                    v1 = i * grid_size + (grid_size - 1)
                    v2 = (i + 1) * grid_size + (grid_size - 1)
                    v3 = offset + i * grid_size + (grid_size - 1)
                    v4 = offset + (i + 1) * grid_size + (grid_size - 1)
                    faces.append([v1, v3, v2])
                    faces.append([v2, v3, v4])
                    v1 = i * grid_size
                    v2 = (i + 1) * grid_size
                    v3 = offset + i * grid_size
                    v4 = offset + (i + 1) * grid_size
                    faces.append([v1, v2, v3])
                    faces.append([v2, v4, v3])
                vertices = np.array(vertices)
                faces = np.array(faces)
                terrain_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
                for i, face in enumerate(faces):
                    for j in range(3):
                        terrain_mesh.vectors[i][j] = vertices[face[j]]
                output_file = os.path.join(self.output_dir, f"{base_filename}_terrain_model.stl")
                terrain_mesh.save(output_file)
                self.log(f"Simplified STL file saved as {output_file}")
            except Exception as e:
                self.log(f"Error creating simplified STL file: {e}")
                import traceback
                self.log(traceback.format_exc())
    def _create_track_stl_file(self, x_scaled, y_scaled, z_scaled, track_x, track_y, track_z, base_filename):
        """Create a separate STL file for just the track."""
        self.log("Generating track-only STL file...")
        try:
            from stl import mesh
            import numpy as np
            tube_radius = self.track_width * 0.2
            tube_segments = 8
            track_elevation = 0.2
            min_z = min(z_scaled)
            max_z = max(z_scaled)
            z_range = max_z - min_z
            scaled_track_z = [self.base_thickness + (z - min_z) * (self.size * 0.10 / z_range) + track_elevation 
                            for z in track_z]
            vertices = []
            faces = []
            vertex_count = 0
            if len(track_x) < 2:
                self.log("Not enough track points to create a track STL")
                return
            for i in range(len(track_x) - 1):
                p1 = np.array([track_x[i], track_y[i], scaled_track_z[i]])
                p2 = np.array([track_x[i+1], track_y[i+1], scaled_track_z[i+1]])
                if np.linalg.norm(p2 - p1) < 0.01:
                    continue
                forward = p2 - p1
                forward = forward / np.linalg.norm(forward)
                if abs(forward[0]) < abs(forward[1]):
                    right = np.cross(forward, [1, 0, 0])
                else:
                    right = np.cross(forward, [0, 1, 0])
                right = right / np.linalg.norm(right)
                up = np.cross(right, forward)
                up = up / np.linalg.norm(up)
                for t, point in [(0, p1), (1, p2)]:
                    for j in range(tube_segments):
                        angle = 2 * math.pi * j / tube_segments
                        circle_point = point + (right * math.cos(angle) + up * math.sin(angle)) * tube_radius
                        vertices.append(circle_point.tolist())
                for j in range(tube_segments):
                    j_next = (j + 1) % tube_segments
                    v1 = vertex_count + j
                    v2 = vertex_count + j_next
                    v3 = vertex_count + tube_segments + j
                    v4 = vertex_count + tube_segments + j_next
                    faces.append([v1, v2, v3])
                    faces.append([v2, v4, v3])
                vertex_count += tube_segments * 2
            center_first = np.array([track_x[0], track_y[0], scaled_track_z[0]])
            vertices.append(center_first.tolist())
            center_first_idx = len(vertices) - 1
            for j in range(tube_segments):
                j_next = (j + 1) % tube_segments
                faces.append([center_first_idx, j_next, j])
            center_last = np.array([track_x[-1], track_y[-1], scaled_track_z[-1]])
            vertices.append(center_last.tolist())
            center_last_idx = len(vertices) - 1
            last_circle_start = vertex_count - tube_segments
            for j in range(tube_segments):
                j_next = (j + 1) % tube_segments
                faces.append([center_last_idx, last_circle_start + j, last_circle_start + j_next])
            vertices = np.array(vertices)
            faces = np.array(faces)
            self.log(f"Creating track STL mesh with {len(vertices)} vertices and {len(faces)} faces")
            track_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
            for i, face in enumerate(faces):
                for j in range(3):
                    track_mesh.vectors[i][j] = vertices[face[j]]
            output_file = os.path.join(self.output_dir, f"{base_filename}_track.stl")
            track_mesh.save(output_file)
            self.log(f"Track STL file saved as {output_file}")
        except Exception as e:
            self.log(f"Error creating track STL file: {e}")
            import traceback
            self.log(traceback.format_exc())     
    def _lat_to_y(self, lat):
        """Convert latitude to y-coordinate (assuming flat Earth approximation)."""
        return lat * 111000
    def _lon_to_x(self, lon):
        """Convert longitude to x-coordinate (assuming flat Earth approximation)."""
        avg_lat = (self.min_lat + self.max_lat) / 2
        return lon * 111000 * math.cos(math.radians(avg_lat))
    def generate_terrain(self):
        """Execute the full terrain generation process."""
        try:
            self.read_gpx()
            self.generate_boundary_shape()
            self.fetch_elevation_data()
            self.generate_3d_model()
            self.log("Terrain generation complete!")
            return True
        except Exception as e:
            self.log(f"Error generating terrain: {e}")
            return False
def main():
    """Main function to handle command line arguments and execute the terrain generation."""
    parser = argparse.ArgumentParser(
        description="Generate 3D terrain models from GPX files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("gpx_file", help="Path to the GPX file")
    parser.add_argument("--resolution", type=int, default=40,
                        help="Resolution of the terrain model (higher = more detailed but slower)")
    parser.add_argument("--shape", choices=["octagon", "hexagon", "circle", "rectangle"], default="octagon",
                        help="Shape of the terrain model")
    parser.add_argument("--size", type=float, default=100,
                        help="Size of the model in mm")
    parser.add_argument("--elevation-multiplier", type=float, default=1.0,
                        help="Factor to multiply elevation values")
    parser.add_argument("--track-color", default="red",
                        help="Color of the track line")
    parser.add_argument("--track-width", type=float, default=2,
                        help="Width of the track line")
    parser.add_argument("--base-thickness", type=float, default=2,
                        help="Minimum thickness of the base in mm")
    parser.add_argument("--output-dir", default="output",
                        help="Directory to save output files")
    parser.add_argument("--quiet", action="store_true",
                        help="Run in quiet mode (no progress messages)")
    parser.add_argument("--export-track-stl", action="store_true",
                        help="Export the track as a separate STL file")
    args = parser.parse_args()
    generator = TerrainGenerator(
        gpx_file_path=args.gpx_file,
        resolution=args.resolution,
        shape=args.shape,
        size=args.size,
        elevation_multiplier=args.elevation_multiplier,
        track_color=args.track_color,
        track_width=args.track_width,
        base_thickness=args.base_thickness,
        output_dir=args.output_dir,
        verbose=not args.quiet,
        export_track_stl=args.export_track_stl
    )
    success = generator.generate_terrain()
    return 0 if success else 1
if __name__ == "__main__":
    sys.exit(main())