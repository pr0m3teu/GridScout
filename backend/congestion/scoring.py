
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .capacity import GridCapacityEstimator, StationCapacity
from .config import CongestionConfig, DEFAULT_CONGESTION_CONFIG
from .location import LocationAnalysis, LocationAnalysisService


# ── Output types ───────────────────────────────────────────────────────────

@dataclass
class ComponentScore:
    """One factor's contribution to the overall congestion risk."""
    raw:       float   # normalised 0–1 value before weighting
    weight:    float   # configured weight for this component
    weighted:  float   # raw × weight  (contribution to final score)
    label:     str     # human-readable factor name


@dataclass
class CongestionBreakdown:
    """
    Full, auditable decomposition of the congestion risk score.
    Every number here is traceable to a specific input or config value.
    Expose this via the API to give investors a clear explanation.
    """
    # ── Final score (0–100) ────────────────────────────────────────────
    total: float

    # ── Component scores ───────────────────────────────────────────────
    station_saturation: ComponentScore
    zone_saturation:    ComponentScore
    location_pressure:  ComponentScore
    distance_penalty:   ComponentScore
    route_constraint:   ComponentScore

    # ── Input echoes (for display / AI prompt) ─────────────────────────
    requested_mw:       float
    dist_km:            float
    zona:               str
    judet:              str

    # ── Capacity snapshot ──────────────────────────────────────────────
    capacity:           StationCapacity

    # ── Location analysis ──────────────────────────────────────────────
    location:           LocationAnalysis

    # ── Route signal (may be None if geo unavailable) ──────────────────
    route_score_input:  Optional[float]   # 0–100 viability score from geo module
    route_data_source:  str               # "overpass" | "cache" | "fallback" | "unavailable"

    # ── Risk band ─────────────────────────────────────────────────────
    risk_label:         str   # "Risc Scăzut" | "Risc Moderat" | "Risc Ridicat"


# ── Service ────────────────────────────────────────────────────────────────

class CongestionScoringService:
    """
    Orchestrates all sub-services and produces a CongestionBreakdown.

    Usage:
        svc = CongestionScoringService()
        breakdown = svc.score(
            lat=47.15, lon=27.60,
            zona="J3", judet="IAȘI",
            station="TATARASI",
            requested_mw=20.0,
            dist_km=8.4,
            mw_aprobat=85.0,
            mw_zona_totala=420.0,
            mw_zona_ramasa=185.0,
            route_score=72.0,           # from GeoAnalysisService, or None
            route_source="overpass",
        )
        print(breakdown.total)          # e.g. 54.3
        print(breakdown.station_saturation.weighted)  # e.g. 7.2
    """

    def __init__(self, config: CongestionConfig = DEFAULT_CONGESTION_CONFIG) -> None:
        self._cfg       = config
        self._capacity  = GridCapacityEstimator()
        self._location  = LocationAnalysisService(config)

    # ── Public API ─────────────────────────────────────────────────────────

    def score(
        self,
        *,
        lat:             float,
        lon:             float,
        zona:            str,
        judet:           str,
        station:         str,
        requested_mw:    float,
        dist_km:         float,
        mw_aprobat:      float,
        mw_zona_totala:  float,
        mw_zona_ramasa:  float,
        route_score:     Optional[float] = None,
        route_source:    str = "unavailable",
    ) -> CongestionBreakdown:
        """
        Compute the multi-factor congestion risk score.

        Parameters
        ----------
        lat, lon        : WGS84 coordinates of the project site
        zona            : ANRE network zone code
        judet           : Romanian county name (uppercase, diacritics optional)
        station         : Substation name
        requested_mw    : Capacity the applicant wants to connect (MW)
        dist_km         : Haversine distance site → nearest substation (km)
        mw_aprobat      : Already approved MW at the station (from ANRE data)
        mw_zona_totala  : Total zone capacity (MW) per ANRE Order 137/2021
        mw_zona_ramasa  : Remaining zone capacity (MW)
        route_score     : 0–100 viability from GeoAnalysisService; None if unavailable
        route_source    : Data provenance tag from geo module
        """
        w = self._cfg.weights
        t = self._cfg.thresholds

        # ── 1. Capacity estimation (fixed denominator logic) ───────────
        cap = self._capacity.estimate(
            station=station,
            mw_aprobat=mw_aprobat,
            judet=judet,
            zona=zona,
            requested_mw=requested_mw,
            mw_zona_totala=mw_zona_totala,
            mw_zona_ramasa=mw_zona_ramasa,
        )

        # ── 2. Location analysis ───────────────────────────────────────
        loc = self._location.analyse(lat=lat, lon=lon, zona=zona)

        # ── 3. Component: station saturation ──────────────────────────
        # Power curve: slow rise initially, accelerates near full saturation.
        # Exponent < 1 → concave-up shape (penalises requests > remaining heavily).
        raw_station = _power_clamp(cap.station_saturation, t.saturation_exponent)
        comp_station = ComponentScore(
            raw=raw_station,
            weight=w.station_saturation,
            weighted=round(raw_station * w.station_saturation, 4),
            label="Saturare stație",
        )

        # ── 4. Component: zone saturation ─────────────────────────────
        # Direct: fraction of zone capacity already consumed.
        # No arbitrary ceiling — 100% consumed → 1.0 risk contribution.
        raw_zone = cap.zone_saturation
        comp_zone = ComponentScore(
            raw=raw_zone,
            weight=w.zone_saturation,
            weighted=round(raw_zone * w.zone_saturation, 4),
            label="Saturare zonă ANRE",
        )

        # ── 5. Component: location pressure ───────────────────────────
        raw_location = loc.combined_pressure
        comp_location = ComponentScore(
            raw=raw_location,
            weight=w.location_pressure,
            weighted=round(raw_location * w.location_pressure, 4),
            label="Presiune geografică",
        )

        # ── 6. Component: distance penalty ────────────────────────────
        raw_distance = _distance_score(
            dist_km=dist_km,
            free_km=t.distance_free_km,
            max_km=t.distance_max_km,
            exponent=t.distance_exponent,
        )
        comp_distance = ComponentScore(
            raw=raw_distance,
            weight=w.distance_penalty,
            weighted=round(raw_distance * w.distance_penalty, 4),
            label="Penalizare distanță",
        )

        # ── 7. Component: route constraint ────────────────────────────
        raw_route = _route_constraint_score(
            route_score=route_score,
            source=route_source,
            fallback=t.route_fallback,
        )
        comp_route = ComponentScore(
            raw=raw_route,
            weight=w.route_constraint,
            weighted=round(raw_route * w.route_constraint, 4),
            label="Constrângeri traseu",
        )

        # ── 8. Aggregate ───────────────────────────────────────────────
        total_weighted = (
            comp_station.weighted
            + comp_zone.weighted
            + comp_location.weighted
            + comp_distance.weighted
            + comp_route.weighted
        )
        total_score = round(min(100.0, max(0.0, total_weighted * 100.0)), 1)

        risk_label = _risk_label(total_score)

        return CongestionBreakdown(
            total=total_score,
            station_saturation=comp_station,
            zone_saturation=comp_zone,
            location_pressure=comp_location,
            distance_penalty=comp_distance,
            route_constraint=comp_route,
            requested_mw=requested_mw,
            dist_km=dist_km,
            zona=zona,
            judet=judet,
            capacity=cap,
            location=loc,
            route_score_input=route_score,
            route_data_source=route_source,
            risk_label=risk_label,
        )


# ── Pure scoring functions (testable in isolation) ─────────────────────────

def _power_clamp(x: float, exponent: float) -> float:
    """
    Apply a power curve to x ∈ [0, 1] → [0, 1].

    exponent < 1:  concave-up (rises slowly at start, steeply at end)
    exponent = 1:  linear (no change)
    exponent > 1:  concave-down (rises quickly at start, flattens)

    The saturation component uses exponent=0.65 to model real-world substation
    dynamics: a project consuming 30% of remaining capacity has moderate risk,
    but consuming 90% creates disproportionately high connection risk.
    """
    return round(min(1.0, max(0.0, x) ** exponent), 6)


def _distance_score(
    dist_km:  float,
    free_km:  float,
    max_km:   float,
    exponent: float,
) -> float:
    """
    Normalised distance penalty ∈ [0, 1].

    - Below free_km      → 0.0 (no penalty)
    - Between free and max → linear interpolation raised to `exponent`
    - Above max_km       → 1.0 (maximum penalty)

    exponent=0.8 gives mild super-linearity: each additional km beyond the
    free zone adds slightly more penalty than the one before it.
    """
    if dist_km <= free_km:
        return 0.0
    if dist_km >= max_km:
        return 1.0
    span = max_km - free_km
    normalised = (dist_km - free_km) / span
    return round(normalised ** exponent, 6)


def _route_constraint_score(
    route_score: Optional[float],
    source:      str,
    fallback:    float,
) -> float:
    """
    Convert the GeoAnalysisService route_score (0–100, higher = more viable)
    into a risk component (0–1, higher = more constrained).

    Inversion: a route with score 80 (good) → constraint 0.20 (low risk).
    A route with score 20 (bad) → constraint 0.80 (high risk).

    If route_score is None (geo service unavailable), use the configured
    fallback — a moderate 0.30 that acknowledges uncertainty without
    catastrophising.
    """
    if route_score is None or source == "unavailable":
        return fallback
    return round(max(0.0, min(1.0, (100.0 - route_score) / 100.0)), 6)


def _risk_label(score: float) -> str:
    """Map numeric score to a Romanian risk label for display."""
    if score >= 70:
        return "Risc Ridicat"
    if score >= 40:
        return "Risc Moderat"
    return "Risc Scăzut"