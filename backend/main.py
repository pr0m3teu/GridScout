import math
import os

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="GridScout API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_openai_key    = os.getenv("OPENAI_KEY", "")
openai_client  = OpenAI(api_key=_openai_key) if _openai_key else None

BARNOVA_LAT       = 47.05
BARNOVA_LON       = 27.63
BARNOVA_RADIUS_KM = 4.0
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

COUNTY_CENTROIDS: dict[str, dict] = {
    "IAȘI":     {"lat": 47.1585, "lon": 27.6014},
    "VASLUI":   {"lat": 46.6401, "lon": 27.7298},
    "BACĂU":    {"lat": 46.5670, "lon": 26.9146},
    "NEAMȚ":    {"lat": 46.9767, "lon": 26.3814},
    "SUCEAVA":  {"lat": 47.6333, "lon": 26.2500},
    "BOTOȘANI": {"lat": 47.7500, "lon": 26.6667},
    "VRANCEA":  {"lat": 45.6896, "lon": 27.0651},
    "GALAȚI":   {"lat": 45.4353, "lon": 28.0074},
    "BRĂILA":   {"lat": 45.2692, "lon": 27.9574},
    "CONSTANȚA":{"lat": 44.1598, "lon": 28.6348},
    "IALOMIȚA": {"lat": 44.5633, "lon": 27.3697},
    "CĂLĂRAȘI": {"lat": 44.2011, "lon": 27.3318},
    "BUCUREȘTI":{"lat": 44.4268, "lon": 26.1025},
    "ILFOV":    {"lat": 44.5000, "lon": 26.2000},
    "GIURGIU":  {"lat": 43.9037, "lon": 25.9699},
    "TELEORMAN":{"lat": 44.0000, "lon": 25.0000},
    "ARGEȘ":    {"lat": 44.8565, "lon": 24.8700},
    "BUZĂU":    {"lat": 45.1500, "lon": 26.8200},
    "DÂMBOVIȚA":{"lat": 44.9300, "lon": 25.4577},
    "PRAHOVA":  {"lat": 44.9500, "lon": 26.0200},
    "VÂLCEA":   {"lat": 45.1019, "lon": 24.3698},
    "DOLJ":     {"lat": 44.3170, "lon": 23.7960},
    "GORJ":     {"lat": 44.9500, "lon": 23.3500},
    "OLT":      {"lat": 44.2700, "lon": 24.4200},
    "TIMIȘ":    {"lat": 45.7489, "lon": 21.2087},
    "ARAD":     {"lat": 46.1866, "lon": 21.3123},
    "HUNEDOARA":{"lat": 45.7500, "lon": 22.9000},
    "ALBA":     {"lat": 46.0700, "lon": 23.5700},
    "BRAȘOV":   {"lat": 45.6427, "lon": 25.5887},
    "SIBIU":    {"lat": 45.7983, "lon": 24.1256},
    "BIHOR":    {"lat": 47.0469, "lon": 22.0000},
    "CLUJ":     {"lat": 46.7712, "lon": 23.6236},
    "MUREȘ":    {"lat": 46.5500, "lon": 24.6000},
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
        df  = pd.read_excel(CAPACITATE_PATH, sheet_name=0, header=0)
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
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ      = math.radians(lat2 - lat1)
    dλ      = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_closest_station(lat: float, lon: float) -> tuple[str, float, dict]:
    best_name  = ""
    best_dist  = float("inf")
    best_coords: dict = {}

    for name, coords in STATION_COORDS.items():
        d = haversine(lat, lon, coords["lat"], coords["lon"])
        if d < best_dist:
            best_dist   = d
            best_name   = name
            best_coords = coords

    return best_name, round(best_dist, 2), best_coords


def get_capacity_data(station: str, station_coords: dict, requested_mw: float) -> dict:
    raw_judet = station_coords.get("judet", "")
    judet     = normalize_county(raw_judet) if raw_judet else ""
    zona      = COUNTY_TO_ZONE.get(judet, "N/A")

    stats         = STATION_STATS.get(station, {})
    mw_aprobat    = stats.get("mw_aprobat", 0.0)
    cap_standard  = max(mw_aprobat * 2.5, requested_mw * 3, 50.0)
    cap_remaining = max(0.0, cap_standard - mw_aprobat)

    zone_data      = ZONE_CAPACITY.get(zona, {})
    mw_zona_totala = zone_data.get("mw_zona_totala",  500.0)
    mw_zona_ramasa = zone_data.get("mw_zona_ramasa",  200.0)

    return {
        "judet":             judet or raw_judet,
        "zona":              zona,
        "mw_aprobat_statie": round(mw_aprobat, 1),
        "cap_standard":      round(cap_standard, 1),
        "cap_ramasa_statie": round(cap_remaining, 1),
        "mw_zona_totala":    round(mw_zona_totala, 1),
        "mw_zona_ramasa":    round(mw_zona_ramasa, 1),
    }


def compute_risk_score(requested_mw: float, cap: dict) -> float:
    cap_s  = cap["cap_standard"]
    cap_r  = cap["cap_ramasa_statie"]
    zona_r = cap["mw_zona_ramasa"]

    if requested_mw >= cap_r:
        station_risk = 100.0
    else:
        station_risk = min(99.9, (requested_mw / cap_s) * 100 * (1 + (requested_mw / max(cap_r, 0.01)) * 0.5))

    zone_risk = min(100.0, (requested_mw / max(zona_r, 1)) * 60.0)

    return round(min(100.0, max(0.0, 0.7 * station_risk + 0.3 * zone_risk)), 1)


def is_natura_2000(lat: float, lon: float) -> bool:
    return haversine(lat, lon, BARNOVA_LAT, BARNOVA_LON) < BARNOVA_RADIUS_KM


def estimate_capex(dist_km: float, requested_mw: float) -> tuple[float, float]:
    capex     = round(dist_km * LINE_COST_EUR_PER_KM, 2)
    per_mw    = round(capex / max(requested_mw, 0.01), 2)
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


def generate_insight(
    station: str, dist_km: float, cap: dict,
    risk: float, mw: float, env_flag: bool,
) -> str:
    natura_note = ""
    if env_flag:
        natura_note = (
            "\n\nCRITICAL — NATURA 2000: The project site falls within 4 km of Bârnova Forest "
            "(ROSCI0256). You must explicitly warn the investor that an Appropriate Assessment "
            "(AA) procedure under Habitats Directive 92/43/EEC may be required, that construction "
            "may be prohibited or subject to severe conditions from the Iași Environmental Protection "
            "Agency, and that the environmental procedure can take more than 18 months. "
            "Strongly recommend consulting an environmental specialist before any technical steps."
        )

    prompt = f"""You are an expert consultant in Romanian electrical grid interconnection.
Generate a professional assessment in exactly 3 paragraphs, in English, with no titles, lists, or bullets.
Tone: expert B2B, precise, actionable. Address the investor directly ("your project", "your site").
Base your analysis strictly on the data below.

ANALYSIS DATA:
- Identified interconnection substation: {station}
- County / ANRE network zone: {cap.get('judet')} / Zone {cap.get('zona')}
- Distance from site to substation: {dist_km} km
- Requested capacity: {mw} MW
- Approved capacity at substation (ANRE data): {cap.get('mw_aprobat_statie')} MW
- Estimated substation capacity: {cap.get('cap_standard')} MW
- Remaining substation capacity: {cap.get('cap_ramasa_statie')} MW
- Total zone capacity — Zone {cap.get('zona')} (ANRE Order 137/2021): {cap.get('mw_zona_totala')} MW
- Remaining zone capacity: {cap.get('mw_zona_ramasa')} MW
- GridScout congestion risk score: {risk}%
- Natura 2000 protected area overlap (Bârnova): {'YES — HIGH ENVIRONMENTAL RISK' if env_flag else 'No'}
{natura_note}

REQUIRED STRUCTURE:
Paragraph 1: Describe the current state of the substation and network zone relative to the distance from the chosen site.
Paragraph 2: Analyse the {risk}% risk score and clearly explain the implications for a {mw} MW request.{' Prominently integrate the Natura 2000 warning.' if env_flag else ''}
Paragraph 3: Provide a direct, actionable recommendation (grid access request, solution study, procedural risks, or whether an alternative site should be sought).

Respond ONLY with the 3 paragraphs separated by a blank line. No other text."""

    if openai_client:
        try:
            resp = openai_client.responses.create(
                model="gpt-4o-mini",
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
            )
            return resp.output_text
        except Exception as e:
            print(f"[WARN] OpenAI error: {e}")

    return _fallback_insight(station, dist_km, cap, risk, mw, env_flag)


def _fallback_insight(
    station: str, dist_km: float, cap: dict,
    risk: float, mw: float, env_flag: bool,
) -> str:
    level  = "High" if risk >= 80 else ("Moderate" if risk >= 40 else "Low")
    zona   = cap.get("zona", "N/A")
    cap_r  = cap.get("cap_ramasa_statie", 0)
    zona_r = cap.get("mw_zona_ramasa", 0)

    p1 = (
        f"The {station} substation (ANRE Zone {zona}) has an estimated residual capacity "
        f"of {cap_r:.1f} MW, located {dist_km:.1f} km from your proposed {mw:.1f} MW project site."
    )
    p2 = (
        f"The congestion risk score of {risk:.1f}% ({level} Risk) reflects cumulative pressure "
        f"at both the substation and zone levels; the remaining zone capacity in Zone {zona} "
        f"is {zona_r:.1f} MW per ANRE Order 137/2021."
    )
    if env_flag:
        p3 = (
            "CRITICAL: Your site overlaps with the Natura 2000 protected area — Bârnova Forest "
            "(ROSCI0256). Before any technical steps, consult an environmental specialist. "
            "The Appropriate Assessment procedure may take 12–18 months and could block the project "
            "entirely. We strongly recommend identifying an alternative site immediately."
        )
    elif risk >= 40:
        p3 = (
            "Grid connection will require a detailed solution study and negotiations with the DSO; "
            "expect 6–12 months to obtain the grid access certificate, with possible network "
            "reinforcement works required."
        )
    else:
        p3 = (
            "Grid conditions are favourable. We recommend initiating the standard ANRE grid "
            "access request immediately, with an estimated 3–6 months to receive a positive opinion."
        )
    return f"{p1}\n\n{p2}\n\n{p3}"


class EvaluateRequest(BaseModel):
    lat:           float
    lon:           float
    requested_mw:  float


@app.post("/api/evaluate-risk")
async def evaluate_risk(req: EvaluateRequest):
    if req.requested_mw <= 0:
        raise HTTPException(400, detail="Requested capacity must be a positive value.")

    station_name, dist_km, station_coords = find_closest_station(req.lat, req.lon)
    cap  = get_capacity_data(station_name, station_coords, req.requested_mw)
    risk = compute_risk_score(req.requested_mw, cap)

    env_flag             = is_natura_2000(req.lat, req.lon)
    capex_eur, capex_per_mw = estimate_capex(dist_km, req.requested_mw)
    solar_irradiance     = await fetch_solar_irradiance(req.lat, req.lon)
    elevation            = await fetch_elevation(req.lat, req.lon)

    insight = generate_insight(
        station=station_name, dist_km=dist_km, cap=cap,
        risk=risk, mw=req.requested_mw, env_flag=env_flag,
    )

    return {
        "closest_station":    station_name,
        "distance_km":        dist_km,
        "capacity_left":      cap["cap_ramasa_statie"],
        "risk_score":         risk,
        "ai_insight":         insight,
        "station_lat":        station_coords["lat"],
        "station_lon":        station_coords["lon"],
        "zona_retea":         cap["zona"],
        "judet_statie":       cap["judet"],
        "mw_aprobat_statie":  cap["mw_aprobat_statie"],
        "mw_zona_ramasa":     cap["mw_zona_ramasa"],
        "mw_zona_totala":     cap["mw_zona_totala"],
        "env_flag":           env_flag,
        "capex_eur":          capex_eur,
        "capex_per_mw":       capex_per_mw,
        "resource_efficiency": solar_irradiance,
        "elevation_meters":   elevation,
    }


@app.get("/health")
async def health():
    return {
        "status":         "ok",
        "excel_loaded":   not FORMULAR_DF.empty,
        "zones_loaded":   len(ZONE_CAPACITY),
        "stations_known": len(STATION_STATS),
        "ai_enabled":     openai_client is not None,
        "version":        "3.0.0",
    }