from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

from .config import CongestionConfig, DEFAULT_CONGESTION_CONFIG


# ── Output type ────────────────────────────────────────────────────────────

@dataclass
class LocationAnalysis:
    """
    All location-derived inputs to the congestion score, exposed for
    transparency and auditability.
    """
    zona:                str    # ANRE zone code (e.g. "J3", "A4")
    zone_pressure:       float  # 0–1 from zone pressure map
    nearest_city:        str    # name of closest urban anchor
    nearest_city_dist_km: float # great-circle km to that anchor
    urban_pressure:      float  # 0–1 derived from urban proximity
    combined_pressure:   float  # 0–1 final location pressure score
    note:                str    # human-readable explanation


# ── Service ────────────────────────────────────────────────────────────────

class LocationAnalysisService:
    """
    Evaluates location pressure for a (lat, lon, zona) triplet.

    Usage:
        svc = LocationAnalysisService()              # uses DEFAULT_CONGESTION_CONFIG
        loc = svc.analyse(lat=47.15, lon=27.60, zona="J3")
        print(loc.combined_pressure)                 # e.g. 0.538
    """

    def __init__(self, config: CongestionConfig = DEFAULT_CONGESTION_CONFIG) -> None:
        self._cfg = config

    # ── Public API ─────────────────────────────────────────────────────────

    def analyse(self, lat: float, lon: float, zona: str) -> LocationAnalysis:
        """
        Return a LocationAnalysis for the given geographic point.

        Parameters
        ----------
        lat, lon : WGS84 coordinates of the project site
        zona     : ANRE network zone code (from COUNTY_TO_ZONE mapping)
        """
        t = self._cfg.thresholds

        # ── Sub-score 1: Zone pressure ─────────────────────────────────
        zone_pressure = self._cfg.zone_pressure_map.get(zona, 0.50)

        # ── Sub-score 2: Urban proximity ───────────────────────────────
        nearest_city, nearest_dist_km, urban_pressure = self._urban_proximity(lat, lon)

        # ── Combine ────────────────────────────────────────────────────
        uw = t.urban_proximity_weight
        combined = round(
            (1.0 - uw) * zone_pressure + uw * urban_pressure,
            4,
        )

        note = (
            f"Zonă ANRE {zona} (presiune de bază {zone_pressure:.0%}); "
            f"cel mai aproape centru urban: {nearest_city} la {nearest_dist_km:.1f} km "
            f"(presiune urbană {urban_pressure:.0%}). "
            f"Presiune combinată: {combined:.0%}."
        )

        return LocationAnalysis(
            zona=zona,
            zone_pressure=zone_pressure,
            nearest_city=nearest_city,
            nearest_city_dist_km=round(nearest_dist_km, 1),
            urban_pressure=round(urban_pressure, 4),
            combined_pressure=combined,
            note=note,
        )

    # ── Internal helpers ───────────────────────────────────────────────────

    def _urban_proximity(
        self, lat: float, lon: float
    ) -> tuple[str, float, float]:
        """
        Find the nearest urban anchor and compute a proximity pressure score.

        Returns (city_name, distance_km, urban_pressure_0_to_1).

        The pressure is 1.0 within `urban_full_pressure_km` and decays
        linearly to 0.0 at `urban_zero_pressure_km`.  This is a simple,
        explainable heuristic that any stakeholder can verify on a map.
        """
        t = self._cfg.thresholds

        best_city = "N/A"
        best_dist = float("inf")

        for anchor_lat, anchor_lon, city_name in self._cfg.urban_anchors:
            d = _haversine(lat, lon, anchor_lat, anchor_lon)
            if d < best_dist:
                best_dist = d
                best_city = city_name

        # Linear decay between full_pressure_km and zero_pressure_km
        if best_dist <= t.urban_full_pressure_km:
            urban_pressure = 1.0
        elif best_dist >= t.urban_zero_pressure_km:
            urban_pressure = 0.0
        else:
            span = t.urban_zero_pressure_km - t.urban_full_pressure_km
            urban_pressure = 1.0 - (best_dist - t.urban_full_pressure_km) / span

        return best_city, best_dist, round(urban_pressure, 4)


# ── Geometry helper (no external dependency) ──────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two WGS84 points."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))