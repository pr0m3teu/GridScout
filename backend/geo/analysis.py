"""
GeoAnalysisService — orchestrates constraint fetching and route scoring.

Usage:
    service = GeoAnalysisService()           # uses DEFAULT_CONFIG
    result  = await service.evaluate_route(
        site_lat=47.15, site_lon=27.60,
        station_lat=47.17, station_lon=27.63,
        dist_km=3.2,
    )
    print(result.total)          # e.g. 74.5
    print(result.crossed_areas)  # e.g. ["Bârnova Forest"]

Extending to other countries:
    - Instantiate with a custom ScoringConfig (different utm_epsg, weights, penalties)
    - Override ConstraintProvider with a country-specific data source if needed
"""

from .config import DEFAULT_CONFIG, ScoringConfig
from .constraints import ConstraintProvider
from .geometry import bbox_from_coords, buffer_path_metric, build_path
from .scoring import RouteScore, ScoringEngine


class GeoAnalysisService:
    """
    Singleton-safe: instantiate once at application startup and reuse.
    The embedded ConstraintProvider holds the in-memory cache.
    """

    def __init__(self, config: ScoringConfig = DEFAULT_CONFIG) -> None:
        self._config      = config
        self._constraints = ConstraintProvider(config.overpass)
        self._scoring     = ScoringEngine(config)

    async def evaluate_route(
        self,
        site_lat:    float,
        site_lon:    float,
        station_lat: float,
        station_lon: float,
        dist_km:     float,
    ) -> RouteScore:
        """
        Evaluate a proposed grid connection path from site to substation.

        Parameters
        ----------
        site_lat / site_lon:       WGS84 coordinates of the project site
        station_lat / station_lon: WGS84 coordinates of the nearest substation
        dist_km:                   Haversine distance (pre-computed, reused here)

        Returns
        -------
        RouteScore with total viability score, component breakdown, and violations.
        """
        coords = [(site_lat, site_lon), (station_lat, station_lon)]
        bbox   = bbox_from_coords(coords, pad_deg=0.05)

        # Guard: refuse unreasonably large bboxes (mistyped coordinates, etc.)
        s, w, n, e = bbox
        if (n - s) > self._config.overpass.max_bbox_deg or \
           (e - w) > self._config.overpass.max_bbox_deg:
            raise ValueError(
                f"Bounding box ({n-s:.2f}° × {e-w:.2f}°) exceeds the configured "
                f"limit of {self._config.overpass.max_bbox_deg}°. "
                "Check that site and station coordinates are correct."
            )

        path        = build_path(coords[0], coords[1])
        path_buffer = buffer_path_metric(path, self._config.path_buffer_m, self._config.utm_epsg)

        constraints = await self._constraints.get_constraints(bbox)

        return self._scoring.evaluate(
            path=path,
            path_buffer=path_buffer,
            dist_km=dist_km,
            constraints=constraints,
        )