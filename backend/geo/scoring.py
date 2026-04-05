import math
from dataclasses import dataclass, field
from typing import List, Optional

from shapely.geometry import LineString, Polygon

from .config import ScoringConfig
from .constraints import ConstraintData, ProtectedArea


@dataclass
class Violation:
    category:    str   # "protected_area" | "railway" | "highway" | "waterway"
    name:        str
    penalty:     float
    detail:      dict  = field(default_factory=dict)


@dataclass
class RouteScore:
    total:                  float          # 0–100 viability score
    env_component:          float          # penalty contribution from environment
    distance_component:     float          # penalty contribution from distance
    infra_component:        float          # penalty contribution from infrastructure
    violations:             List[Violation]
    crossed_areas:          List[str]      # names of crossed protected areas
    env_flag:               bool           # True if any protected area crossed
    constraint_source:      str            # "overpass" | "cache" | "fallback"


def _area_radius_m(polygon: Polygon) -> float:
    minx, miny, maxx, maxy = polygon.bounds
    mid_lat_rad = math.radians((miny + maxy) / 2.0)
    lat_scale   = 111_000.0                          # m / degree latitude
    lon_scale   = 111_000.0 * math.cos(mid_lat_rad)  # m / degree longitude

    area_m2 = polygon.area * lat_scale * lon_scale
    radius  = math.sqrt(area_m2 / math.pi)
    return max(500.0, min(40_000.0, radius))



class ScoringEngine:

    def __init__(self, config: ScoringConfig) -> None:
        self._cfg = config

    def evaluate(
        self,
        path:          LineString,
        path_buffer:   Polygon,
        dist_km:       float,
        constraints:   ConstraintData,
    ) -> RouteScore:
        p = self._cfg.penalties
        w = self._cfg.weights

        violations:    List[Violation] = []
        crossed_areas: List[str]       = []

        raw_env = 0.0
        seen_area_ids: set[int] = set()

        for area in constraints.protected_areas:
            if area.geometry is None:
                continue
            if area.osm_id in seen_area_ids:
                continue
            if not path_buffer.intersects(area.geometry):
                continue

            seen_area_ids.add(area.osm_id)
            penalty = p.protected_area_base
            if area.protection_type == "national_park":
                penalty *= p.national_park_multiplier

            # Centroid for frontend map rendering (WGS84: x=lon, y=lat)
            centroid  = area.geometry.centroid
            radius_m  = _area_radius_m(area.geometry)

            violations.append(Violation(
                category="protected_area",
                name=area.name,
                penalty=round(penalty, 1),
                detail={
                    "protection_type": area.protection_type,
                    "iucn_level":      area.iucn_level or "unknown",
                    "centroid_lat":    round(centroid.y, 6),
                    "centroid_lon":    round(centroid.x, 6),
                    "display_radius_m": round(radius_m, 0),
                },
            ))
            crossed_areas.append(area.name)
            raw_env += penalty

        raw_env = min(raw_env, p.protected_area_cap)

        raw_infra = 0.0

        for line in constraints.infrastructure:
            if line.geometry is None:
                continue
   
            if not path.intersects(line.geometry):
                continue

            unit_penalty = {
                "railway":  p.railway_crossing,
                "highway":  p.highway_crossing,
                "waterway": p.waterway_crossing,
            }.get(line.infra_type, 0.0)

            if unit_penalty == 0.0:
                continue

            violations.append(Violation(
                category=line.infra_type,
                name=f"{line.infra_type.title()} crossing",
                penalty=unit_penalty,
                detail={"osm_id": line.osm_id},
            ))
            raw_infra += unit_penalty

        raw_infra = min(raw_infra, p.infrastructure_cap)

        excess_km = max(0.0, dist_km - p.distance_free_km)
        raw_dist  = min(excess_km * p.distance_per_km, p.distance_cap)

        env_component   = round(raw_env   * w.environment,    2)
        dist_component  = round(raw_dist  * w.distance,       2)
        infra_component = round(raw_infra * w.infrastructure, 2)

        total_penalty = env_component + dist_component + infra_component
        total_score   = round(max(0.0, min(100.0, 100.0 - total_penalty)), 1)

        return RouteScore(
            total=total_score,
            env_component=env_component,
            distance_component=dist_component,
            infra_component=infra_component,
            violations=violations,
            crossed_areas=crossed_areas,
            env_flag=len(crossed_areas) > 0,
            constraint_source=constraints.source,
        )
