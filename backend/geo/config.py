"""
Scoring configuration — all weights and thresholds live here.

To tune the model: adjust these dataclasses only.
No constants are scattered across business logic.

Extending to other countries:
  - Adjust path_buffer_meters for denser/sparser grids
  - Adjust utm_epsg to match the country's UTM zone
  - Override penalty values via environment config or a config file
"""

from dataclasses import dataclass, field


@dataclass
class OverpassConfig:
    endpoint:      str = "https://overpass-api.de/api/interpreter"
    timeout_s:     int = 25
    cache_ttl_h:   int = 24
    max_bbox_deg:  float = 2.0   # abort if bbox side exceeds this (prevents runaway queries)


@dataclass
class PenaltyConfig:
    # Protected area penalties (raw, before weight application)
    protected_area_base:           float = 70.0
    national_park_multiplier:      float = 1.5   # applied on top of base
    protected_area_cap:            float = 100.0  # ceiling after accumulation

    # Distance penalties
    distance_per_km:               float = 3.0
    distance_free_km:              float = 5.0   # no penalty below this
    distance_cap:                  float = 50.0

    # Infrastructure crossing penalties (per crossing)
    railway_crossing:              float = 5.0
    highway_crossing:              float = 3.0
    waterway_crossing:             float = 8.0
    infrastructure_cap:            float = 40.0  # ceiling on total infra penalty


@dataclass
class WeightConfig:
    """
    Weights must sum to 1.0.
    environment:    proximity/crossing of protected zones
    distance:       length of required grid connection
    infrastructure: crossings of major infrastructure
    """
    environment:    float = 0.45
    distance:       float = 0.35
    infrastructure: float = 0.20

    def __post_init__(self) -> None:
        total = self.environment + self.distance + self.infrastructure
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total:.4f}")


@dataclass
class ScoringConfig:
    weights:            WeightConfig  = field(default_factory=WeightConfig)
    penalties:          PenaltyConfig = field(default_factory=PenaltyConfig)
    overpass:           OverpassConfig = field(default_factory=OverpassConfig)

    # Width of the path corridor used for intersection checks (metres)
    path_buffer_m:      float = 200.0

    # UTM zone EPSG used for metric buffering.
    # EPSG:32635 = WGS 84 / UTM zone 35N — covers Romania (24–36°E).
    # Change to 32634 for central Europe, 32636 for further east, etc.
    utm_epsg:           int   = 32635


DEFAULT_CONFIG = ScoringConfig()