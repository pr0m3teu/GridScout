
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


# ── Weight configuration ───────────────────────────────────────────────────

@dataclass
class WeightConfig:
    """
    Five components whose weights must sum exactly to 1.0.

    Rationale for defaults (Romanian grid context):
      station_saturation  0.30  — single most decisive factor: if the chosen
                                   substation has no room, nothing else matters.
      zone_saturation     0.22  — ANRE zone-level capacity is the regulatory
                                   ceiling; it gates the STN study.
      location_pressure   0.20  — intrinsic regional grid load independent of
                                   this project (Dobrogea wind cluster,
                                   Bucharest ring are structurally congested).
      distance_penalty    0.15  — longer lines → higher cost, voltage drop,
                                   protection complexity, and approval risk.
      route_constraint    0.13  — environmental / infrastructure obstacles;
                                   real but secondary to capacity fundamentals.
    """
    station_saturation: float = 0.30
    zone_saturation:    float = 0.22
    location_pressure:  float = 0.20
    distance_penalty:   float = 0.15
    route_constraint:   float = 0.13

    def __post_init__(self) -> None:
        total = (
            self.station_saturation
            + self.zone_saturation
            + self.location_pressure
            + self.distance_penalty
            + self.route_constraint
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"CongestionConfig weights must sum to 1.0, got {total:.6f}. "
                "Adjust WeightConfig fields to restore balance."
            )


# ── Threshold configuration ────────────────────────────────────────────────

@dataclass
class ThresholdConfig:
    """
    Configurable thresholds for each scoring component.
    Change these to tune sensitivity without touching business logic.
    """

    # ── Station saturation curve ──────────────────────────────────────────
    # Power curve exponent: < 1 makes the curve concave-up (slow rise early,
    # steep near saturation). 0.65 gives a realistic "soft cap" shape.
    saturation_exponent: float = 0.65

    # ── Distance penalty ──────────────────────────────────────────────────
    # Connection distance (km) below which no penalty is applied.
    distance_free_km:    float = 5.0
    # Distance (km) at which the penalty reaches its maximum (1.0 normalised).
    distance_max_km:     float = 80.0
    # Shape exponent: 0.8 → mild super-linearity (longer lines penalised more
    # than proportionally, but not as harshly as quadratic).
    distance_exponent:   float = 0.8

    # ── Route constraint fallback ─────────────────────────────────────────
    # Used when geo analysis is unavailable (source = "unavailable").
    # 0.30 = modest uncertainty penalty — acknowledge missing data without
    # over-penalising projects that simply had an Overpass timeout.
    route_fallback:      float = 0.30

    # ── Location pressure sub-weights ─────────────────────────────────────
    # Fraction of location_pressure that comes from urban-proximity.
    # The remainder (1 − urban_weight) comes from the zone pressure map.
    urban_proximity_weight:    float = 0.35
    # Distance (km) from a major urban anchor below which full pressure applies.
    urban_full_pressure_km:    float = 20.0
    # Distance (km) beyond which the urban anchor has zero influence.
    urban_zero_pressure_km:    float = 120.0


# ── Zone pressure map ──────────────────────────────────────────────────────

# ANRE network zone → base congestion pressure (0.0–1.0).
# Values derived from:
#   • ANRE Ordin 137/2021 approved-vs-remaining capacity tables
#   • Historical grid congestion patterns (Dobrogea renewable cluster,
#     Bucharest load centre, Banat industrial belt)
#   • Public Transelectrica and DSO quarterly reports (2023–2025)
#
# These are calibrated heuristics — replace with live SCADA/ANRE API when
# available by swapping the zone_pressure_map in CongestionConfig.
ZONE_PRESSURE_MAP: Dict[str, float] = {
    # ── Dobrogea / Black Sea coast — highest renewable density, grid at limit
    "A1":    0.82,  # Galați — port industrial + wind overflow from Dobrogea
    "A2":    0.78,  # Brăila — wind corridor, cross-Danube constraints
    "A3":    0.85,  # Tulcea — Dobrogea wind/solar cluster, structurally saturated
    "A4":    0.88,  # Constanța — coastal wind + solar, consistently congested
    "A5":    0.72,  # Ialomița/Călărași — south-east plains, moderate solar

    # ── Muntenia / București ring
    "B2":    0.68,  # Giurgiu/Teleorman — agricultural, cross-border Bulgaria
    "B3":    0.84,  # București/Ilfov — highest urban load density in Romania

    # ── Prahova / Dâmbovița oil & gas belt
    "C1":    0.75,  # Buzău/Prahova — oil refining, petrochemical load
    "C2":    0.70,  # Dâmbovița — moderate industrial
    "C3":    0.65,  # Argeș — Pitești automotive, growing renewable
    "C4":    0.60,  # Vâlcea — hydro-rich, some grid export capacity

    # ── Oltenia / South-west
    "D1":    0.62,  # Dolj/Olt — Craiova industrial, spare capacity available
    "D2":    0.58,  # Gorj — coal transition zone, declining load
    "D3/E3": 0.55,  # Mehedinți — sparsely populated, cross-border Danube

    # ── Banat
    "E1":    0.70,  # Timiș — Timișoara industrial belt, growing renewable
    "E2":    0.52,  # Caraș-Severin — mountainous, low load density

    # ── Crișana
    "F1":    0.67,  # Arad — industrial, cross-border Hungary
    "F2":    0.58,  # Hunedoara — legacy steel, some peak congestion

    # ── Centru / Transilvania
    "G1":    0.65,  # Brașov/Covasna — tourism + light industry
    "G2-1":  0.60,  # Alba — moderate
    "G2-2":  0.62,  # Sibiu — growing industrial park

    # ── Nord-Vest
    "H1":    0.68,  # Bihor — Oradea industrial, cross-border Hungary
    "H2":    0.52,  # Sălaj — low density
    "H3":    0.55,  # Maramureș/Satu Mare — rural, some wind development
    "H4":    0.60,  # Bistrița-Năsăud/Cluj — Cluj-Napoca tech hub growing

    # ── Mureș / Harghita
    "I1":    0.55,  # Mureș — Târgu Mureș chemical, moderate
    "I2":    0.45,  # Harghita — low density, mountainous

    # ── Moldova / North-East (least congested macro-region)
    "J1":    0.48,  # Botoșani/Suceava — rural, low industrial load
    "J2":    0.50,  # Neamț — some industry, moderate
    "J3":    0.55,  # Iași/Vaslui — Iași university city, growing fast
    "J4":    0.52,  # Bacău/Vrancea — moderate industrial

    # Fallback for zones not yet mapped
    "N/A":   0.50,
}


# ── Urban load-center anchors ──────────────────────────────────────────────

# Major Romanian cities used as proximity anchors for the urban-pressure
# sub-score within location_pressure.
# Format: (lat, lon, city_name)
URBAN_ANCHOR_POINTS: Tuple[Tuple[float, float, str], ...] = (
    (44.4268, 26.1025, "București"),
    (46.7712, 23.6236, "Cluj-Napoca"),
    (45.7489, 21.2087, "Timișoara"),
    (46.1866, 21.3123, "Arad"),
    (47.1585, 27.6014, "Iași"),
    (46.5670, 26.9146, "Bacău"),
    (45.6427, 25.5887, "Brașov"),
    (45.7983, 24.1256, "Sibiu"),
    (47.0469, 22.0000, "Oradea"),
    (44.1598, 28.6348, "Constanța"),
    (45.4353, 28.0074, "Galați"),
    (45.2692, 27.9574, "Brăila"),
    (46.9767, 26.3814, "Piatra Neamț"),
    (44.9500, 26.0200, "Ploiești"),
    (44.8565, 24.8700, "Pitești"),
)


# ── Top-level config ───────────────────────────────────────────────────────

@dataclass
class CongestionConfig:
    """
    Complete configuration for the multi-factor congestion risk engine.
    Pass a custom instance to CongestionScoringService to override any defaults.
    """
    weights:           WeightConfig    = field(default_factory=WeightConfig)
    thresholds:        ThresholdConfig = field(default_factory=ThresholdConfig)
    zone_pressure_map: Dict[str, float] = field(
        default_factory=lambda: dict(ZONE_PRESSURE_MAP)
    )
    urban_anchors: tuple = field(
        default_factory=lambda: URBAN_ANCHOR_POINTS
    )


DEFAULT_CONGESTION_CONFIG = CongestionConfig()