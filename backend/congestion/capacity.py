
from __future__ import annotations

import math
from dataclasses import dataclass


# ── Output type ────────────────────────────────────────────────────────────

@dataclass
class StationCapacity:
    """
    All capacity-related metrics for a (station, requested_mw) pair.
    Every field is used in the congestion score or exposed in the API response.
    """
    # From ANRE data / Excel
    mw_aprobat_statie:   float   # Total approved MW already committed at this station
    mw_cap_estimated:    float   # Estimated technical ceiling of the station
    mw_remaining:        float   # Estimated remaining capacity (ceiling − approved)

    # Ratios
    station_saturation:  float   # requested_mw / mw_remaining  (0–∞, clamped to [0,1])
    station_utilisation: float   # mw_aprobat / mw_cap_estimated (0–1), current load

    # Zone-level
    mw_zona_totala:      float
    mw_zona_ramasa:      float
    zone_saturation:     float   # (totala − ramasa) / totala — how used the zone already is

    # Administrative
    judet:               str
    zona:                str

    # Derived: remaining after this project (for downstream display)
    mw_remaining_after:  float


# ── Estimator ──────────────────────────────────────────────────────────────

class GridCapacityEstimator:
    """
    Derives StationCapacity from raw ANRE data dicts.

    Usage:
        estimator = GridCapacityEstimator()
        cap = estimator.estimate(
            station="TATARASI",
            mw_aprobat=85.0,
            judet="IAȘI",
            zona="J3",
            requested_mw=20.0,
            mw_zona_totala=420.0,
            mw_zona_ramasa=185.0,
        )
    """

    # Station technical ceiling is estimated as:
    #   max(mw_aprobat × CEILING_MULTIPLIER, FLOOR_MW)
    # Only supply-side data. The requested_mw plays NO role in the denominator.
    CEILING_MULTIPLIER: float = 2.5
    FLOOR_MW:           float = 50.0

    def estimate(
        self,
        station:        str,
        mw_aprobat:     float,
        judet:          str,
        zona:           str,
        requested_mw:   float,
        mw_zona_totala: float,
        mw_zona_ramasa: float,
    ) -> StationCapacity:
        # ── Station ceiling: supply-side only (fixes the old bug) ──────
        mw_cap = max(mw_aprobat * self.CEILING_MULTIPLIER, self.FLOOR_MW)
        mw_remaining = max(0.0, mw_cap - mw_aprobat)

        # ── Station saturation (0–1) ───────────────────────────────────
        # requested_mw / available_remaining — the correct interpretation.
        # clamped at 1.0: even if over-requested, 1.0 is the max signal.
        if mw_remaining <= 0:
            station_saturation = 1.0
        else:
            station_saturation = min(1.0, requested_mw / mw_remaining)

        # ── Current station utilisation (informational) ────────────────
        station_utilisation = min(1.0, mw_aprobat / max(mw_cap, 1e-6))

        # ── Zone saturation (0–1) ──────────────────────────────────────
        # (total − remaining) / total = fraction already consumed.
        # No artificial 60% ceiling — fully saturated zone → 1.0.
        if mw_zona_totala <= 0:
            zone_saturation = 0.5   # data missing: neutral assumption
        else:
            consumed = max(0.0, mw_zona_totala - mw_zona_ramasa)
            zone_saturation = min(1.0, consumed / mw_zona_totala)

        mw_remaining_after = max(0.0, mw_remaining - requested_mw)

        return StationCapacity(
            mw_aprobat_statie=round(mw_aprobat, 1),
            mw_cap_estimated=round(mw_cap, 1),
            mw_remaining=round(mw_remaining, 1),
            station_saturation=round(station_saturation, 4),
            station_utilisation=round(station_utilisation, 4),
            mw_zona_totala=round(mw_zona_totala, 1),
            mw_zona_ramasa=round(mw_zona_ramasa, 1),
            zone_saturation=round(zone_saturation, 4),
            judet=judet,
            zona=zona,
            mw_remaining_after=round(mw_remaining_after, 1),
        )