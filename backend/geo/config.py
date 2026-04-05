from dataclasses import dataclass, field


@dataclass
class OverpassConfig:
    endpoint:      str = "https://overpass-api.de/api/interpreter"
    timeout_s:     int = 25
    cache_ttl_h:   int = 24
    max_bbox_deg:  float = 2.0   


@dataclass
class PenaltyConfig:

    protected_area_base:           float = 70.0
    national_park_multiplier:      float = 1.5   
    protected_area_cap:            float = 100.0  

    distance_per_km:               float = 3.0
    distance_free_km:              float = 5.0   
    distance_cap:                  float = 50.0

    railway_crossing:              float = 5.0
    highway_crossing:              float = 3.0
    waterway_crossing:             float = 8.0
    infrastructure_cap:            float = 40.0  

@dataclass
class WeightConfig:
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

    path_buffer_m:      float = 200.0

    utm_epsg:           int   = 32635


DEFAULT_CONFIG = ScoringConfig()