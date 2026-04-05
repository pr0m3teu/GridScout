from .config import DEFAULT_CONFIG, ScoringConfig
from .constraints import ConstraintProvider
from .geometry import bbox_from_coords, buffer_path_metric, build_path
from .scoring import RouteScore, ScoringEngine


class GeoAnalysisService:
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
        
        coords = [(site_lat, site_lon), (station_lat, station_lon)]
        bbox   = bbox_from_coords(coords, pad_deg=0.05)

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