"""
ConstraintProvider — fetches geospatial constraint data from the Overpass API
and caches results in memory (per bounding-box key, with a configurable TTL).

To swap the data source (e.g. to a PostGIS database, a national GIS service,
or a local GeoJSON file), replace `_fetch_protected_areas` and
`_fetch_infrastructure` with your new provider — the rest of the pipeline
(scoring, caching, geometry) stays unchanged.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import httpx
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import unary_union

from .config import OverpassConfig
from .geometry import linestring_from_nodes, polygon_from_nodes


# ── Domain types ──────────────────────────────────────────────────────────────

@dataclass
class ProtectedArea:
    osm_id:          int
    name:            str
    protection_type: str   # "national_park" | "nature_reserve" | "protected_area"
    iucn_level:      str   # e.g. "II", "IV", "" when unknown
    geometry:        Optional[Polygon]


@dataclass
class InfrastructureLine:
    osm_id:     int
    infra_type: str   # "railway" | "highway" | "waterway"
    geometry:   Optional[LineString]


@dataclass
class ConstraintData:
    protected_areas: List[ProtectedArea]
    infrastructure:  List[InfrastructureLine]
    source:          str   # "overpass" | "cache" | "fallback"
    fetched_at:      float = field(default_factory=time.time)


# ── Overpass query templates ──────────────────────────────────────────────────

_PROTECTED_QUERY = """
[out:json][timeout:{timeout}][maxsize:33554432];
(
  way["boundary"="protected_area"]({bbox});
  relation["boundary"="protected_area"]({bbox});
  way["leisure"="nature_reserve"]({bbox});
  relation["leisure"="nature_reserve"]({bbox});
  way["boundary"="national_park"]({bbox});
  relation["boundary"="national_park"]({bbox});
);
out geom;
""".strip()

_INFRASTRUCTURE_QUERY = """
[out:json][timeout:{timeout}][maxsize:16777216];
(
  way["railway"~"^(rail|light_rail|narrow_gauge)$"]({bbox});
  way["highway"~"^(motorway|trunk|primary)$"]({bbox});
  way["waterway"~"^(river|canal)$"]({bbox});
);
out geom;
""".strip()



class ConstraintProvider:
    """
    Fetches and caches protected-area and infrastructure constraints.

    Cache key: bbox rounded to 2 decimal degrees (~1 km precision).
    Cache TTL: configurable in OverpassConfig (default 24 h).
    """

    def __init__(self, config: OverpassConfig) -> None:
        self._cfg   = config
        self._cache: dict[str, ConstraintData] = {}

    async def get_constraints(
        self,
        bbox: Tuple[float, float, float, float],
    ) -> ConstraintData:
        """
        Return constraint data for the given bounding box.
        Hits the cache if a valid entry exists; otherwise queries Overpass.
        """
        key = self._cache_key(bbox)

        if key in self._cache and self._cache_valid(self._cache[key]):
            cached = self._cache[key]
            return ConstraintData(
                protected_areas=cached.protected_areas,
                infrastructure=cached.infrastructure,
                source="cache",
                fetched_at=cached.fetched_at,
            )

        protected, infra = await asyncio.gather(
            self._fetch_protected_areas(bbox),
            self._fetch_infrastructure(bbox),
            return_exceptions=True,
        )
        if isinstance(protected, Exception):
            print(f"[WARN] Protected area fetch error: {protected}")
            protected = []
        if isinstance(infra, Exception):
            print(f"[WARN] Infrastructure fetch error: {infra}")
            infra = []

        source = "overpass" if (protected or infra) else "fallback"
        data   = ConstraintData(
            protected_areas=protected,
            infrastructure=infra,
            source=source,
        )
        self._cache[key] = data
        return data

    def _cache_key(self, bbox: Tuple[float, float, float, float]) -> str:
        s, w, n, e = bbox
        return f"{s:.2f},{w:.2f},{n:.2f},{e:.2f}"

    def _cache_valid(self, data: ConstraintData) -> bool:
        return (time.time() - data.fetched_at) < self._cfg.cache_ttl_h * 3600

    async def _fetch_protected_areas(
        self, bbox: Tuple[float, float, float, float]
    ) -> List[ProtectedArea]:
        bbox_str = "{},{},{},{}".format(*bbox)
        query    = _PROTECTED_QUERY.format(timeout=self._cfg.timeout_s, bbox=bbox_str)
        elements = await self._query(query)
        return self._parse_protected(elements)

    async def _fetch_infrastructure(
        self, bbox: Tuple[float, float, float, float]
    ) -> List[InfrastructureLine]:
        bbox_str = "{},{},{},{}".format(*bbox)
        query    = _INFRASTRUCTURE_QUERY.format(timeout=self._cfg.timeout_s, bbox=bbox_str)
        elements = await self._query(query)
        return self._parse_infrastructure(elements)

    async def _query(self, query: str) -> list:
        async with httpx.AsyncClient(timeout=self._cfg.timeout_s + 5) as client:
            resp = await client.post(
                self._cfg.endpoint,
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            return resp.json().get("elements", [])

    def _parse_protected(self, elements: list) -> List[ProtectedArea]:
        seen: set[int] = set()
        areas: List[ProtectedArea] = []

        for el in elements:
            osm_id = el.get("id")
            if osm_id in seen:
                continue
            seen.add(osm_id)

            tags = el.get("tags", {})
            name = (
                tags.get("name:en")
                or tags.get("name")
                or f"Protected Area {osm_id}"
            )
            ptype = (
                "national_park"   if tags.get("boundary") == "national_park"
                else "nature_reserve" if tags.get("leisure") == "nature_reserve"
                else "protected_area"
            )
            iucn  = tags.get("iucn_level", "")
            geom  = self._element_to_polygon(el)

            if geom is not None:
                areas.append(ProtectedArea(
                    osm_id=osm_id,
                    name=name,
                    protection_type=ptype,
                    iucn_level=iucn,
                    geometry=geom,
                ))

        return areas

    def _parse_infrastructure(self, elements: list) -> List[InfrastructureLine]:
        lines: List[InfrastructureLine] = []

        for el in elements:
            if el.get("type") != "way":
                continue
            tags  = el.get("tags", {})
            nodes = el.get("geometry", [])
            geom  = linestring_from_nodes(nodes)
            if geom is None:
                continue

            if "railway" in tags:
                itype = "railway"
            elif "highway" in tags:
                itype = "highway"
            elif "waterway" in tags:
                itype = "waterway"
            else:
                continue

            lines.append(InfrastructureLine(
                osm_id=el["id"],
                infra_type=itype,
                geometry=geom,
            ))

        return lines


    def _element_to_polygon(self, el: dict) -> Optional[Polygon]:
        el_type = el.get("type")

        if el_type == "way":
            return polygon_from_nodes(el.get("geometry", []))

        if el_type == "relation":
            outer_rings: List[Polygon] = []
            for member in el.get("members", []):
                if member.get("role") != "outer":
                    continue
                nodes = member.get("geometry", [])
                poly  = polygon_from_nodes(nodes)
                if poly is not None:
                    outer_rings.append(poly)

            if not outer_rings:
                return None
            if len(outer_rings) == 1:
                return outer_rings[0]

            merged = unary_union(outer_rings)
            if merged.geom_type == "Polygon":
                return merged
            if merged.geom_type == "MultiPolygon":
                return max(merged.geoms, key=lambda g: g.area)
            return None

        return None