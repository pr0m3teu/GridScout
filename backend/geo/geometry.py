import math
from typing import List, Optional, Tuple

from pyproj import Transformer
from shapely.geometry import LineString, Polygon
from shapely.ops import transform as shapely_transform
from shapely.validation import make_valid

# (lat, lon) named for clarity at call sites
Coord = Tuple[float, float]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two WGS84 points."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_path(start: Coord, end: Coord) -> LineString:
    return LineString([(start[1], start[0]), (end[1], end[0])])


def buffer_path_metric(line: LineString, metres: float, utm_epsg: int = 32635) -> Polygon:

    to_utm   = Transformer.from_crs("EPSG:4326", f"EPSG:{utm_epsg}", always_xy=True)
    from_utm = Transformer.from_crs(f"EPSG:{utm_epsg}", "EPSG:4326",  always_xy=True)

    line_utm     = shapely_transform(to_utm.transform,   line)
    buffered_utm = line_utm.buffer(metres, cap_style=2)  # flat caps
    return shapely_transform(from_utm.transform, buffered_utm)


def bbox_from_coords(coords: List[Coord], pad_deg: float = 0.05) -> Tuple[float, float, float, float]:
    """
    Axis-aligned bounding box (south, west, north, east) in WGS84 degrees,
    padded by `pad_deg` on all sides.
    """
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return (
        min(lats) - pad_deg,
        min(lons) - pad_deg,
        max(lats) + pad_deg,
        max(lons) + pad_deg,
    )


def polygon_from_nodes(nodes: List[dict]) -> Optional[Polygon]:
    if len(nodes) < 3:
        return None
    coords = [(n["lon"], n["lat"]) for n in nodes]
    # Close the ring if open
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    try:
        poly = Polygon(coords)
        if not poly.is_valid:
            poly = make_valid(poly)
        if poly.geom_type == "GeometryCollection":
            polys = [g for g in poly.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
            if not polys:
                return None
            poly = polys[0]
        return poly if poly.is_valid else None
    except Exception:
        return None


def linestring_from_nodes(nodes: List[dict]) -> Optional[LineString]:
    """Build a Shapely LineString from Overpass geometry nodes."""
    if len(nodes) < 2:
        return None
    coords = [(n["lon"], n["lat"]) for n in nodes]
    try:
        return LineString(coords)
    except Exception:
        return None