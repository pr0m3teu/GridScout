"""
ScoringEngine — computes a route viability score (0–100, higher = more viable).

Score interpretation:
  90–100  Excellent: short, clean route, no constraints
  70–89   Good: minor issues, straightforward to resolve
  50–69   Moderate: notable concerns requiring mitigation
  30–49   Poor: significant regulatory or cost burden
   0–29   Critical: likely blocked by protected area or severe constraints

The score is the inverse of accumulated weighted penalties:
  score = max(0, 100 − (env_component + distance_component + infra_component))

Each component = raw_penalty × its weight.
Raw penalties are capped individually before weighting.
"""

from dataclasses import dataclass, field
from typing import List

from shapely.geometry import LineString, Polygon

from .config import ScoringConfig
from .constraints import ConstraintData, ProtectedArea


# ── Output types ──────────────────────────────────────────────────────────────

@dataclass
class Violation:
    category:    str   # "protected_area" | "railway" | "highway" | "waterway"
    name:        str
    penalty:     float
    detail:      dict  = field(default_factory=dict)


@dataclass
class RouteScore:
    """
    Complete scoring result for a proposed grid connection route.

    `total` is the primary signal; components explain the breakdown.
    `env_flag` is True when any protected area is crossed — kept for
    backward compatibility with the API response schema.
    """
    total:                  float          # 0–100 viability score
    env_component:          float          # penalty contribution from environment
    distance_component:     float          # penalty contribution from distance
    infra_component:        float          # penalty contribution from infrastructure
    violations:             List[Violation]
    crossed_areas:          List[str]      # names of crossed protected areas
    env_flag:               bool           # True if any protected area crossed
    constraint_source:      str            # "overpass" | "cache" | "fallback"


# ── Engine ────────────────────────────────────────────────────────────────────

class ScoringEngine:
    """
    Pure function engine — takes geometry and constraint data, returns RouteScore.
    No I/O, no side effects.
    """

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

        # ── Environment: protected area crossings ──────────────────────────
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

            violations.append(Violation(
                category="protected_area",
                name=area.name,
                penalty=round(penalty, 1),
                detail={
                    "protection_type": area.protection_type,
                    "iucn_level":      area.iucn_level or "unknown",
                },
            ))
            crossed_areas.append(area.name)
            raw_env += penalty

        raw_env = min(raw_env, p.protected_area_cap)

        # ── Infrastructure: line crossings ────────────────────────────────
        raw_infra = 0.0

        for line in constraints.infrastructure:
            if line.geometry is None:
                continue
            # Use `intersects` rather than `crosses`: a path that touches
            # but doesn't cleanly cross (e.g., runs parallel then dips in)
            # still incurs an infrastructure constraint cost.
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

        # ── Distance ───────────────────────────────────────────────────────
        excess_km = max(0.0, dist_km - p.distance_free_km)
        raw_dist  = min(excess_km * p.distance_per_km, p.distance_cap)

        # ── Weighted components ────────────────────────────────────────────
        env_component  = round(raw_env   * w.environment,    2)
        dist_component = round(raw_dist  * w.distance,       2)
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