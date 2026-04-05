import asyncio
import math
import os

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

from geo import DEFAULT_CONFIG, GeoAnalysisService
from geo.scoring import Violation
from congestion import CongestionScoringService, DEFAULT_CONGESTION_CONFIG
from congestion.scoring import CongestionBreakdown

load_dotenv()

app = FastAPI(title="GridScout API", version="5.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_openai_key  = os.getenv("OPENAI_KEY", "")
openai_client = OpenAI(api_key=_openai_key) if _openai_key else None

geo_service        = GeoAnalysisService(DEFAULT_CONFIG)
congestion_service = CongestionScoringService(DEFAULT_CONGESTION_CONFIG)

LINE_COST_EUR_PER_KM = 90_000.0

COUNTY_TO_ZONE: dict[str, str] = {
    "GALAȚI": "A1",  "GALATI": "A1",
    "BRĂILA": "A2",  "BRAILA": "A2",
    "TULCEA": "A3",
    "CONSTANȚA": "A4", "CONSTANTA": "A4",
    "IALOMIȚA": "A5", "IALOMITA": "A5",
    "CĂLĂRAȘI": "A5", "CALARASI": "A5",
    "BUCUREȘTI": "B3", "BUCURESTI": "B3",
    "ILFOV": "B3",
    "GIURGIU": "B2",
    "TELEORMAN": "B2",
    "ARGEȘ": "C3", "ARGES": "C3",
    "BUZĂU": "C1",  "BUZAU": "C1",
    "DÂMBOVIȚA": "C2", "DAMBOVITA": "C2",
    "PRAHOVA": "C1",
    "VÂLCEA": "C4",  "VALCEA": "C4",
    "DOLJ": "D1",
    "GORJ": "D2",
    "MEHEDINȚI": "D3/E3", "MEHEDINTI": "D3/E3",
    "OLT": "D1",
    "CARAȘ-SEVERIN": "E2", "CARAS-SEVERIN": "E2",
    "TIMIȘ": "E1",   "TIMIS": "E1",
    "ARAD": "F1",
    "HUNEDOARA": "F2",
    "ALBA": "G2-1",
    "BRAȘOV": "G1",  "BRASOV": "G1",
    "COVASNA": "G1",
    "SIBIU": "G2-2",
    "BIHOR": "H1",
    "BISTRIȚA-NĂSĂUD": "H4", "BISTRITA-NASAUD": "H4",
    "CLUJ": "H4",
    "MARAMUREȘ": "H3", "MARAMURES": "H3",
    "SĂLAJ": "H2",   "SALAJ": "H2",
    "SATU MARE": "H3",
    "MUREȘ": "I1",   "MURES": "I1",
    "HARGHITA": "I2",
    "IAȘI": "J3",    "IASI": "J3",
    "VASLUI": "J3",
    "NEAMȚ": "J2",   "NEAMT": "J2",
    "BACĂU": "J4",   "BACAU": "J4",
    "VRANCEA": "J4",
    "BOTOȘANI": "J1", "BOTOSANI": "J1",
    "SUCEAVA": "J1",
}

STATION_COORDS: dict[str, dict] = {
    "TATARASI":             {"lat": 47.1723, "lon": 27.6312, "judet": "IAȘI"},
    "TUTORA":               {"lat": 47.0312, "lon": 27.5234, "judet": "IAȘI"},
    "HAGIESTI 110/20 KV":  {"lat": 47.1901, "lon": 27.4823, "judet": "IAȘI"},
    "HAGIESTI":             {"lat": 47.1901, "lon": 27.4823, "judet": "IAȘI"},
    "LETCANI":              {"lat": 47.2001, "lon": 27.4123, "judet": "IAȘI"},
    "PASCANI":              {"lat": 47.2512, "lon": 26.7234, "judet": "IAȘI"},
    "IASI SUD":             {"lat": 47.1285, "lon": 27.5765, "judet": "IAȘI"},
    "IASI NORD":            {"lat": 47.1923, "lon": 27.5634, "judet": "IAȘI"},
    "IASI VEST":            {"lat": 47.1567, "lon": 27.5012, "judet": "IAȘI"},
    "TARGU FRUMOS":         {"lat": 47.2089, "lon": 26.9823, "judet": "IAȘI"},
    "HARLAU":               {"lat": 47.4234, "lon": 26.9012, "judet": "IAȘI"},
    "PODU ILOAIEI":         {"lat": 47.2145, "lon": 27.2765, "judet": "IAȘI"},
    "VATRA":                {"lat": 47.2156, "lon": 27.3901, "judet": "IAȘI"},
    "NEGRESTI":             {"lat": 46.8423, "lon": 27.4671, "judet": "VASLUI"},
    "BANCA":                {"lat": 46.5891, "lon": 27.8234, "judet": "VASLUI"},
    "VASLUI NORD":          {"lat": 46.6512, "lon": 27.7312, "judet": "VASLUI"},
    "BORZESTI":             {"lat": 46.3512, "lon": 26.7234, "judet": "BACĂU"},
    "BACAU SUD":            {"lat": 46.5234, "lon": 26.9012, "judet": "BACĂU"},
    "BACAU NORD":           {"lat": 46.6012, "lon": 26.9145, "judet": "BACĂU"},
    "ROMAN LAMINOR":        {"lat": 46.9201, "lon": 26.9312, "judet": "NEAMȚ"},
    "VATRA DORNEI":         {"lat": 47.3512, "lon": 25.3634, "judet": "SUCEAVA"},
    "SUCEAVA SUD":          {"lat": 47.6123, "lon": 26.2534, "judet": "SUCEAVA"},
    "RADAUTI":              {"lat": 47.8412, "lon": 25.9201, "judet": "SUCEAVA"},
    "HUDUM":                {"lat": 47.7512, "lon": 26.7123, "judet": "BOTOȘANI"},
    "ROMAN":                {"lat": 46.9201, "lon": 26.9212, "judet": "NEAMȚ"},
    "SMARDANUL":            {"lat": 45.3912, "lon": 28.0512, "judet": "GALAȚI"},
    "GALATI SUD":           {"lat": 45.4012, "lon": 28.0201, "judet": "GALAȚI"},
    "MEDGIDIA SUD":         {"lat": 44.2512, "lon": 28.2634, "judet": "CONSTANȚA"},
    "CONSTANTA NORD":       {"lat": 44.2012, "lon": 28.5234, "judet": "CONSTANȚA"},
    "BUCURESTI SUD":        {"lat": 44.3523, "lon": 26.1234, "judet": "BUCUREȘTI"},
    "PELICANU":             {"lat": 44.4512, "lon": 25.9801, "judet": "ILFOV"},
    "FUNDENI":              {"lat": 44.4601, "lon": 26.1923, "judet": "ILFOV"},
    "CALUGARENI":           {"lat": 43.9812, "lon": 25.8512, "judet": "GIURGIU"},
    "MOSTISTEA":            {"lat": 44.2312, "lon": 26.4712, "judet": "CĂLĂRAȘI"},
    "TARGOVISTE":           {"lat": 44.9312, "lon": 25.4501, "judet": "DÂMBOVIȚA"},
    "NICULESTI":            {"lat": 44.8712, "lon": 25.6312, "judet": "DÂMBOVIȚA"},
    "BUZAU SUD":            {"lat": 45.1312, "lon": 26.8512, "judet": "BUZĂU"},
    "URECHESTI":            {"lat": 44.9512, "lon": 23.6712, "judet": "GORJ"},
    "TIMISOARA":            {"lat": 45.7489, "lon": 21.2087, "judet": "TIMIȘ"},
    "SACALAZ":              {"lat": 45.7312, "lon": 21.1234, "judet": "TIMIȘ"},
    "NADAB":                {"lat": 46.5312, "lon": 21.5901, "judet": "ARAD"},
    "GRANICERI":            {"lat": 46.4123, "lon": 21.6234, "judet": "ARAD"},
    "ARAD":                 {"lat": 46.1866, "lon": 21.3123, "judet": "ARAD"},
    "CETATE":               {"lat": 46.0512, "lon": 21.2834, "judet": "ARAD"},
    "SEBIS":                {"lat": 46.3712, "lon": 22.1234, "judet": "ARAD"},
    "CET II ORADEA":        {"lat": 47.0712, "lon": 21.9012, "judet": "BIHOR"},
    "PALOTA":               {"lat": 47.1012, "lon": 21.8512, "judet": "BIHOR"},
    "UNGHENI":              {"lat": 46.5912, "lon": 24.7234, "judet": "MUREȘ"},
    "TARNAVENI":            {"lat": 46.3423, "lon": 24.2812, "judet": "MUREȘ"},
    "MINTIA":               {"lat": 45.8612, "lon": 22.9012, "judet": "HUNEDOARA"},
}

BASE_DIR        = os.path.dirname(__file__)
FORMULAR_PATH   = os.path.join(BASE_DIR, "Formular_pentru_schimbul_de_date_10_decembrie2024_2024_12_18_18-33-54.xlsx")
CAPACITATE_PATH = os.path.join(BASE_DIR, "Capacitate_de_racordare_conform_Ordin_ANRE_nr__137_2021_2026_03_10_15-30-43.xlsx")


def normalize_county(raw) -> str:
    if not isinstance(raw, str):
        return ""
    return raw.strip().upper()


def load_formular() -> pd.DataFrame:
    try:
        df = pd.read_excel(FORMULAR_PATH, sheet_name=0, header=0)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        print(f"[WARN] Could not load Formular Excel: {e}")
        return pd.DataFrame()


def load_zone_capacity() -> dict[str, dict]:
    try:
        df = pd.read_excel(CAPACITATE_PATH, sheet_name=0, header=0)
        df.columns = [str(c).strip() for c in df.columns]
        result: dict[str, dict] = {}
        for _, row in df.iterrows():
            zone = str(row.get("Zona", "")).strip()
            if not zone:
                continue
            try:
                total     = float(str(row.get("Capacitate totala (MW)", 0)).replace(",", "."))
                approved  = float(str(row.get("MW aprobat", 0)).replace(",", "."))
                remaining = max(0.0, total - approved)
                result[zone] = {
                    "mw_zona_totala":  round(total, 1),
                    "mw_zona_aprobat": round(approved, 1),
                    "mw_zona_ramasa":  round(remaining, 1),
                }
            except (ValueError, TypeError):
                continue
        return result
    except Exception as e:
        print(f"[WARN] Could not load Capacitate Excel: {e}")
        return {}


def build_station_stats(df: pd.DataFrame) -> dict[str, dict]:
    stats: dict[str, dict] = {}
    if df.empty:
        return stats
    for _, row in df.iterrows():
        name = str(row.get("Statie", "") or row.get("Stație", "")).strip().upper()
        if not name:
            continue
        try:
            mw_val = float(str(row.get("Putere aprobata (MW)", 0) or 0).replace(",", "."))
        except (ValueError, TypeError):
            mw_val = 0.0
        if name in stats:
            stats[name]["mw_aprobat"] += mw_val
            stats[name]["count"]      += 1
        else:
            judet_raw = row.get("Judet", row.get("Județ", ""))
            stats[name] = {
                "mw_aprobat": mw_val,
                "judet":      normalize_county(judet_raw),
                "count":      1,
            }
    return stats


FORMULAR_DF   = load_formular()
ZONE_CAPACITY = load_zone_capacity()
STATION_STATS = build_station_stats(FORMULAR_DF)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_closest_station(lat: float, lon: float) -> tuple[str, float, dict]:
    best_name   = ""
    best_dist   = float("inf")
    best_coords: dict = {}
    for name, coords in STATION_COORDS.items():
        d = haversine(lat, lon, coords["lat"], coords["lon"])
        if d < best_dist:
            best_dist   = d
            best_name   = name
            best_coords = coords
    return best_name, round(best_dist, 2), best_coords


def resolve_raw_inputs(station: str, station_coords: dict) -> dict:
    """
    Resolve administrative identifiers and raw ANRE numbers for a station.
    Returns only supply-side data — no derived capacity calculations.
    The CongestionScoringService handles all derivations.
    """
    raw_judet = station_coords.get("judet", "")
    judet     = normalize_county(raw_judet) if raw_judet else ""
    zona      = COUNTY_TO_ZONE.get(judet, "N/A")

    stats      = STATION_STATS.get(station, {})
    mw_aprobat = stats.get("mw_aprobat", 0.0)

    zone_data      = ZONE_CAPACITY.get(zona, {})
    mw_zona_totala = zone_data.get("mw_zona_totala", 500.0)
    mw_zona_ramasa = zone_data.get("mw_zona_ramasa", 200.0)

    return {
        "judet":          judet or raw_judet,
        "zona":           zona,
        "mw_aprobat":     round(mw_aprobat, 1),
        "mw_zona_totala": round(mw_zona_totala, 1),
        "mw_zona_ramasa": round(mw_zona_ramasa, 1),
    }


def estimate_capex(dist_km: float, requested_mw: float) -> tuple[float, float]:
    capex  = round(dist_km * LINE_COST_EUR_PER_KM, 2)
    per_mw = round(capex / max(requested_mw, 0.01), 2)
    return capex, per_mw


async def fetch_solar_irradiance(lat: float, lon: float) -> float:
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date=2023-01-01&end_date=2023-12-31"
        f"&daily=shortwave_radiation_sum&timezone=auto"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp   = await client.get(url)
            resp.raise_for_status()
            values = resp.json().get("daily", {}).get("shortwave_radiation_sum", [])
            valid  = [v for v in values if v is not None]
            return round(sum(valid), 1) if valid else 1250.0
    except Exception:
        return 1250.0


async def fetch_elevation(lat: float, lon: float) -> int:
    url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp    = await client.get(url)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return int(results[0].get("elevation", 0)) if results else 0
    except Exception:
        return 0


def _format_violations_for_prompt(violations: list[Violation]) -> str:
    if not violations:
        return "Nicio constrângere detectată."
    lines = []
    for v in violations:
        if v.category == "protected_area":
            ptype    = v.detail.get("protection_type", "zonă protejată")
            iucn     = v.detail.get("iucn_level", "")
            iucn_str = f" (IUCN {iucn})" if iucn and iucn != "unknown" else ""
            lines.append(f"  - {v.name}{iucn_str} [{ptype}]")
        else:
            lines.append(f"  - {v.name}")
    return "\n".join(lines)


def generate_insight(
    station:       str,
    dist_km:       float,
    breakdown:     CongestionBreakdown,
    env_flag:      bool,
    crossed_areas: list[str],
    violations:    list[Violation],
) -> str:
    env_block = ""
    if env_flag and crossed_areas:
        area_list = ", ".join(crossed_areas)
        env_block = (
            f"\n\nCRITIC — ZONE PROTEJATE: Traseul traversează: {area_list}. "
            "Poate fi necesară o Evaluare Adecvată (92/43/CEE). "
            "Consultați un specialist de mediu autorizat înainte de orice depunere."
        )

    violations_str = _format_violations_for_prompt(violations)
    cap            = breakdown.capacity
    loc            = breakdown.location
    route_str      = (
        f"{breakdown.route_score_input:.1f}/100"
        if breakdown.route_score_input is not None
        else "indisponibil"
    )

    comp_lines = "\n".join([
        f"  - {breakdown.station_saturation.label}: {breakdown.station_saturation.raw:.0%} (contribuție {breakdown.station_saturation.weighted*100:.1f}%)",
        f"  - {breakdown.zone_saturation.label}: {breakdown.zone_saturation.raw:.0%} (contribuție {breakdown.zone_saturation.weighted*100:.1f}%)",
        f"  - {breakdown.location_pressure.label}: {breakdown.location_pressure.raw:.0%} (contribuție {breakdown.location_pressure.weighted*100:.1f}%)",
        f"  - {breakdown.distance_penalty.label}: {breakdown.distance_penalty.raw:.0%} (contribuție {breakdown.distance_penalty.weighted*100:.1f}%)",
        f"  - {breakdown.route_constraint.label}: {breakdown.route_constraint.raw:.0%} (contribuție {breakdown.route_constraint.weighted*100:.1f}%)",
    ])

    prompt = f"""Acționați ca un consultant expert în interconectarea la rețeaua electrică din România.
Generați o evaluare profesională în exact 3 paragrafe, în limba română, fără titluri, liste sau marcatori.
Ton: expert B2B, precis, orientat spre acțiune. Adresați-vă direct investitorului.

DATE:
- Stație: {station} | Județ/Zonă: {cap.judet} / Zona {cap.zona}
- Distanță: {dist_km} km | Capacitate solicitată: {breakdown.requested_mw} MW
- Capacitate aprobată stație: {cap.mw_aprobat_statie} MW | Rămasă: {cap.mw_remaining} MW
- Capacitate totală zonă: {cap.mw_zona_totala} MW | Rămasă zonă: {cap.mw_zona_ramasa} MW
- Scor risc congestionare: {breakdown.total}% — {breakdown.risk_label}
- Componente risc:
{comp_lines}
- Locație: {loc.note}
- Viabilitate traseu geo: {route_str}
- Constrângeri: {violations_str}
{env_block}

STRUCTURĂ:
P1: Starea stației și a zonei de rețea față de amplasament.
P2: Analizați scorul {breakdown.total}% ({breakdown.risk_label}) cu detaliere pe cele mai importante componente.{' Prioritizați zonele protejate.' if env_flag else ''}
P3: Recomandare directă și acționabilă.

DOAR cele 3 paragrafe, separate de un rând liber."""

    if openai_client:
        try:
            resp = openai_client.responses.create(
                model="gpt-4o-mini",
                temperature=0.4,
                input= [{
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt
                    }
                ]
            }])
            
            return resp.output_text
        except Exception as e:
            print(f"[WARN] OpenAI error: {e}")

    print("FELL BACK")
    return _fallback_insight(station, dist_km, breakdown, crossed_areas)


def _fallback_insight(
    station:       str,
    dist_km:       float,
    breakdown:     CongestionBreakdown,
    crossed_areas: list[str],
) -> str:
    cap      = breakdown.capacity
    risk     = breakdown.total
    risk_lvl = breakdown.risk_label
    zona     = cap.zona
    route_str = (
        f"{breakdown.route_score_input:.1f}/100"
        if breakdown.route_score_input is not None
        else "indisponibil"
    )

    p1 = (
        f"Stația {station} (Zona ANRE {zona}) are o capacitate reziduală estimată de "
        f"{cap.mw_remaining:.1f} MW, la {dist_km:.1f} km de amplasamentul propus de "
        f"{breakdown.requested_mw:.1f} MW."
    )
    p2 = (
        f"Scorul de risc este {risk:.1f}% ({risk_lvl}), determinat de: saturare stație "
        f"{breakdown.station_saturation.raw:.0%}, saturare zonă "
        f"{breakdown.zone_saturation.raw:.0%}, presiune geografică "
        f"{breakdown.location_pressure.raw:.0%}, penalizare distanță "
        f"{breakdown.distance_penalty.raw:.0%} și constrângeri traseu "
        f"{breakdown.route_constraint.raw:.0%} (viabilitate geo: {route_str})."
    )

    if crossed_areas:
        area_list = ", ".join(crossed_areas)
        p3 = (
            f"CRITIC: Traseul traversează zone protejate: {area_list}. "
            "Contactați urgent un consultant de mediu. "
            "Procedura de Evaluare Adecvată poate dura 12–18 luni."
        )
    elif risk >= 70:
        p3 = (
            "Racordarea necesită studiu de soluție și negocieri cu OD; "
            "estimați 6–12 luni pentru avizul de acces, posibil cu lucrări de întărire."
        )
    else:
        p3 = (
            "Condiții favorabile. Inițiați cererea ANRE de acces la rețea imediat; "
            "estimat 3–6 luni pentru opinie favorabilă."
        )
    return f"{p1}\n\n{p2}\n\n{p3}"


class EvaluateRequest(BaseModel):
    lat:          float
    lon:          float
    requested_mw: float


@app.post("/api/evaluate-risk")
async def evaluate_risk(req: EvaluateRequest):
    if req.requested_mw <= 0:
        raise HTTPException(400, detail="Capacitatea solicitată trebuie să fie pozitivă.")

    station_name, dist_km, station_coords = find_closest_station(req.lat, req.lon)
    raw = resolve_raw_inputs(station_name, station_coords)
    capex_eur, capex_per_mw = estimate_capex(dist_km, req.requested_mw)

    geo_task       = geo_service.evaluate_route(
        site_lat=req.lat, site_lon=req.lon,
        station_lat=station_coords["lat"], station_lon=station_coords["lon"],
        dist_km=dist_km,
    )
    solar_task     = fetch_solar_irradiance(req.lat, req.lon)
    elevation_task = fetch_elevation(req.lat, req.lon)

    results = await asyncio.gather(geo_task, solar_task, elevation_task, return_exceptions=True)
    geo_result, solar_irradiance, elevation = results

    if isinstance(geo_result, Exception):
        print(f"[WARN] Geo analysis failed: {geo_result}")
        env_flag, route_score, crossed_areas = False, None, []
        route_violations, constraint_source  = [], "unavailable"
        violations_for_insight: list[Violation] = []
    else:
        env_flag          = geo_result.env_flag
        route_score       = geo_result.total
        crossed_areas     = geo_result.crossed_areas
        route_violations  = [
            {"category": v.category, "name": v.name, "penalty": v.penalty, "detail": v.detail}
            for v in geo_result.violations
        ]
        constraint_source       = geo_result.constraint_source
        violations_for_insight  = geo_result.violations

    if isinstance(solar_irradiance, Exception):
        solar_irradiance = 1250.0
    if isinstance(elevation, Exception):
        elevation = 0

    # ── Multi-factor congestion risk (route_score now INTEGRATED) ──────
    breakdown: CongestionBreakdown = congestion_service.score(
        lat=req.lat,
        lon=req.lon,
        zona=raw["zona"],
        judet=raw["judet"],
        station=station_name,
        requested_mw=req.requested_mw,
        dist_km=dist_km,
        mw_aprobat=raw["mw_aprobat"],
        mw_zona_totala=raw["mw_zona_totala"],
        mw_zona_ramasa=raw["mw_zona_ramasa"],
        route_score=route_score,
        route_source=constraint_source,
    )

    insight = generate_insight(
        station=station_name,
        dist_km=dist_km,
        breakdown=breakdown,
        env_flag=env_flag,
        crossed_areas=crossed_areas,
        violations=violations_for_insight,
    )

    return {
        "closest_station":    station_name,
        "station_lat":        station_coords["lat"],
        "station_lon":        station_coords["lon"],
        "judet_statie":       breakdown.capacity.judet,
        "zona_retea":         breakdown.capacity.zona,
        "distance_km":        dist_km,

        # Risk (multi-factor v5)
        "risk_score":         breakdown.total,
        "risk_label":         breakdown.risk_label,
        "risk_breakdown": {
            "station_saturation": {
                "raw":     round(breakdown.station_saturation.raw * 100, 1),
                "weighted": round(breakdown.station_saturation.weighted * 100, 1),
                "label":   breakdown.station_saturation.label,
            },
            "zone_saturation": {
                "raw":     round(breakdown.zone_saturation.raw * 100, 1),
                "weighted": round(breakdown.zone_saturation.weighted * 100, 1),
                "label":   breakdown.zone_saturation.label,
            },
            "location_pressure": {
                "raw":              round(breakdown.location_pressure.raw * 100, 1),
                "weighted":         round(breakdown.location_pressure.weighted * 100, 1),
                "label":            breakdown.location_pressure.label,
                "nearest_city":     breakdown.location.nearest_city,
                "nearest_city_km":  breakdown.location.nearest_city_dist_km,
            },
            "distance_penalty": {
                "raw":     round(breakdown.distance_penalty.raw * 100, 1),
                "weighted": round(breakdown.distance_penalty.weighted * 100, 1),
                "label":   breakdown.distance_penalty.label,
            },
            "route_constraint": {
                "raw":     round(breakdown.route_constraint.raw * 100, 1),
                "weighted": round(breakdown.route_constraint.weighted * 100, 1),
                "label":   breakdown.route_constraint.label,
                "source":  constraint_source,
            },
        },

        # Capacity
        "mw_aprobat_statie":  breakdown.capacity.mw_aprobat_statie,
        "mw_cap_estimated":   breakdown.capacity.mw_cap_estimated,
        "capacity_left":      breakdown.capacity.mw_remaining,
        "mw_zona_totala":     breakdown.capacity.mw_zona_totala,
        "mw_zona_ramasa":     breakdown.capacity.mw_zona_ramasa,

        # Geo
        "env_flag":           env_flag,
        "route_score":        route_score,
        "crossed_areas":      crossed_areas,
        "route_violations":   route_violations,
        "constraint_source":  constraint_source,

        # Commercial
        "capex_eur":          capex_eur,
        "capex_per_mw":       capex_per_mw,
        "resource_efficiency": solar_irradiance,
        "elevation_meters":   elevation,

        "ai_insight":         insight,
    }


@app.get("/health")
async def health():
    return {
        "status":            "ok",
        "excel_loaded":      not FORMULAR_DF.empty,
        "zones_loaded":      len(ZONE_CAPACITY),
        "stations_known":    len(STATION_STATS),
        "ai_enabled":        openai_client is not None,
        "geo_cache_entries": len(geo_service._constraints._cache),
        "version":           "5.0.0",
    }