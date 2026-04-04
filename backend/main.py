"""
GridScout — Backend FastAPI v3.0
+ env_flag (Natura 2000 / Pădurea Bârnova)
+ capex_eur / capex_per_mw
+ resource_efficiency (Open-Meteo API real)
+ elevation_meters (Open-Elevation API real)
"""

import math
import os
import re

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# App & CORS
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="GridScout API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# OpenAI client
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()
OPENAI_KEY    = os.getenv("OPENAI_KEY", "")
openai_client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# ─────────────────────────────────────────────────────────────────────────────
# Constante mediu
# ─────────────────────────────────────────────────────────────────────────────
# Coordonate Pădurea Bârnova (arie protejată Natura 2000, jud. Iași)
BARNOVA_LAT = 47.05
BARNOVA_LON = 27.63
BARNOVA_RADIUS_KM = 4.0

# Cost estimat linie electrică (EUR/km)
COST_EUR_PER_KM = 90_000.0

# ─────────────────────────────────────────────────────────────────────────────
# Mapping județ → zonă ANRE (Ordin 137/2021) — NESCHIMBAT
# ─────────────────────────────────────────────────────────────────────────────
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
    "BOTOȘANI": "J1","BOTOSANI": "J1",
    "SUCEAVA": "J1",
}

# ─────────────────────────────────────────────────────────────────────────────
# GPS stații — NESCHIMBAT
# ─────────────────────────────────────────────────────────────────────────────
STATION_COORDS: dict[str, dict] = {
    # ── Iași / Vaslui (J3) ──────────────────────────────────────────────────
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
    # ── Bacău / Vrancea (J4) ────────────────────────────────────────────────
    "BORZESTI":             {"lat": 46.3512, "lon": 26.7234, "judet": "BACĂU"},
    "BACAU SUD":            {"lat": 46.5234, "lon": 26.9012, "judet": "BACĂU"},
    "BACAU NORD":           {"lat": 46.6012, "lon": 26.9145, "judet": "BACĂU"},
    "ROMAN LAMINOR":        {"lat": 46.9201, "lon": 26.9312, "judet": "NEAMȚ"},
    # ── Suceava / Botoșani (J1) ─────────────────────────────────────────────
    "VATRA DORNEI":         {"lat": 47.3512, "lon": 25.3634, "judet": "SUCEAVA"},
    "SUCEAVA SUD":          {"lat": 47.6123, "lon": 26.2534, "judet": "SUCEAVA"},
    "RADAUTI":              {"lat": 47.8412, "lon": 25.9201, "judet": "SUCEAVA"},
    "HUDUM":                {"lat": 47.7512, "lon": 26.7123, "judet": "BOTOȘANI"},
    # ── Neamț (J2) ──────────────────────────────────────────────────────────
    "ROMAN":                {"lat": 46.9201, "lon": 26.9212, "judet": "NEAMȚ"},
    # ── Galați (A1) ─────────────────────────────────────────────────────────
    "SMARDANUL":            {"lat": 45.3912, "lon": 28.0512, "judet": "GALAȚI"},
    "GALATI SUD":           {"lat": 45.4012, "lon": 28.0201, "judet": "GALAȚI"},
    # ── Constanța (A4) ──────────────────────────────────────────────────────
    "MEDGIDIA SUD":         {"lat": 44.2512, "lon": 28.2634, "judet": "CONSTANȚA"},
    "CONSTANTA NORD":       {"lat": 44.2012, "lon": 28.5234, "judet": "CONSTANȚA"},
    # ── București / Ilfov (B3) ──────────────────────────────────────────────
    "BUCURESTI SUD":        {"lat": 44.3523, "lon": 26.1234, "judet": "BUCUREȘTI"},
    "PELICANU":             {"lat": 44.4512, "lon": 25.9801, "judet": "ILFOV"},
    "FUNDENI":              {"lat": 44.4601, "lon": 26.1923, "judet": "ILFOV"},
    # ── Giurgiu (B2) ────────────────────────────────────────────────────────
    "CALUGARENI":           {"lat": 43.9812, "lon": 25.8512, "judet": "GIURGIU"},
    "MOSTISTEA":            {"lat": 44.2312, "lon": 26.4712, "judet": "CĂLĂRAȘI"},
    # ── Dâmbovița / Prahova (C) ─────────────────────────────────────────────
    "TARGOVISTE":           {"lat": 44.9312, "lon": 25.4501, "judet": "DÂMBOVIȚA"},
    "NICULESTI":            {"lat": 44.8712, "lon": 25.6312, "judet": "DÂMBOVIȚA"},
    "BUZAU SUD":            {"lat": 45.1312, "lon": 26.8512, "judet": "BUZĂU"},
    # ── Gorj / Dolj (D) ─────────────────────────────────────────────────────
    "URECHESTI":            {"lat": 44.9512, "lon": 23.6712, "judet": "GORJ"},
    # ── Timiș (E1) ──────────────────────────────────────────────────────────
    "TIMISOARA":            {"lat": 45.7489, "lon": 21.2087, "judet": "TIMIȘ"},
    "SACALAZ":              {"lat": 45.7312, "lon": 21.1234, "judet": "TIMIȘ"},
    # ── Arad (F1) ───────────────────────────────────────────────────────────
    "NADAB":                {"lat": 46.5312, "lon": 21.5901, "judet": "ARAD"},
    "GRANICERI":            {"lat": 46.4123, "lon": 21.6234, "judet": "ARAD"},
    "ARAD":                 {"lat": 46.1866, "lon": 21.3123, "judet": "ARAD"},
    "CETATE":               {"lat": 46.0512, "lon": 21.2834, "judet": "ARAD"},
    "SEBIS":                {"lat": 46.3712, "lon": 22.1234, "judet": "ARAD"},
    # ── Bihor (H1) ──────────────────────────────────────────────────────────
    "CET II ORADEA":        {"lat": 47.0712, "lon": 21.9012, "judet": "BIHOR"},
    "PALOTA":               {"lat": 47.1012, "lon": 21.8512, "judet": "BIHOR"},
    # ── Mureș (I1) ──────────────────────────────────────────────────────────
    "UNGHENI":              {"lat": 46.5912, "lon": 24.7234, "judet": "MUREȘ"},
    "TARNAVENI":            {"lat": 46.3423, "lon": 24.2812, "judet": "MUREȘ"},
    # ── Hunedoara (F2) ──────────────────────────────────────────────────────
    "MINTIA":               {"lat": 45.8612, "lon": 22.9012, "judet": "HUNEDOARA"},
}

# Centroide județe (fallback GPS) — NESCHIMBAT
COUNTY_CENTROIDS: dict[str, dict] = {
    "IAȘI":    {"lat": 47.1585, "lon": 27.6014},
    "VASLUI":  {"lat": 46.6401, "lon": 27.7298},
    "BACĂU":   {"lat": 46.5670, "lon": 26.9146},
    "NEAMȚ":   {"lat": 46.9767, "lon": 26.3814},
    "SUCEAVA": {"lat": 47.6333, "lon": 26.2500},
    "BOTOȘANI":{"lat": 47.7500, "lon": 26.6667},
    "VRANCEA": {"lat": 45.6896, "lon": 27.0651},
    "GALAȚI":  {"lat": 45.4353, "lon": 28.0074},
    "BRĂILA":  {"lat": 45.2692, "lon": 27.9574},
    "CONSTANȚA":{"lat":44.1598,"lon": 28.6348},
    "IALOMIȚA":{"lat": 44.5633, "lon": 27.3697},
    "CĂLĂRAȘI":{"lat": 44.2011, "lon": 27.3318},
    "BUCUREȘTI":{"lat":44.4268, "lon": 26.1025},
    "ILFOV":   {"lat": 44.5000, "lon": 26.2000},
    "GIURGIU": {"lat": 43.9037, "lon": 25.9699},
    "TELEORMAN":{"lat":44.0000,"lon": 25.0000},
    "ARGEȘ":   {"lat": 44.8565, "lon": 24.8700},
    "BUZĂU":   {"lat": 45.1500, "lon": 26.8200},
    "DÂMBOVIȚA":{"lat":44.9300,"lon": 25.4577},
    "PRAHOVA": {"lat": 44.9500, "lon": 26.0200},
    "VÂLCEA":  {"lat": 45.1019, "lon": 24.3698},
    "DOLJ":    {"lat": 44.3170, "lon": 23.7960},
    "GORJ":    {"lat": 44.9500, "lon": 23.3500},
    "OLT":     {"lat": 44.2700, "lon": 24.4200},
    "TIMIȘ":   {"lat": 45.7489, "lon": 21.2087},
    "ARAD":    {"lat": 46.1866, "lon": 21.3123},
    "HUNEDOARA":{"lat":45.7500,"lon": 22.9000},
    "ALBA":    {"lat": 46.0700, "lon": 23.5700},
    "BRAȘOV":  {"lat": 45.6427, "lon": 25.5887},
    "SIBIU":   {"lat": 45.7983, "lon": 24.1256},
    "BIHOR":   {"lat": 47.0469, "lon": 22.0000},
    "CLUJ":    {"lat": 46.7712, "lon": 23.6236},
    "MUREȘ":   {"lat": 46.5500, "lon": 24.6000},
}

# ─────────────────────────────────────────────────────────────────────────────
# Căi fișiere Excel — NESCHIMBAT
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(__file__)
FORMULAR_PATH   = os.path.join(BASE_DIR, "Formular_pentru_schimbul_de_date_10_decembrie2024_2024_12_18_18-33-54.xlsx")
CAPACITATE_PATH = os.path.join(BASE_DIR, "Capacitate_de_racordare_conform_Ordin_ANRE_nr__137_2021_2026_03_10_15-30-43.xlsx")


# ─────────────────────────────────────────────────────────────────────────────
# Funcții de citire Excel — NESCHIMBATE (Regula de Aur)
# ─────────────────────────────────────────────────────────────────────────────
def normalize_county(raw) -> str:
    return str(raw).strip().upper() if raw and str(raw) != "nan" else ""


def load_formular_data() -> pd.DataFrame:
    if not os.path.exists(FORMULAR_PATH):
        print("[WARN] Formular Excel lipsă – se continuă fără date ATR.")
        return pd.DataFrame(columns=["Județ", "Stație", "MW_Aprobat"])

    frames = []
    sheets_hdr13 = ["Fotovoltaic", "Hidro", "Cogenerare", "Biomasa", "Biogaz"]
    sheets_hdr15 = ["Eolian"]

    for sheet, hdr in [(s, 13) for s in sheets_hdr13] + [(s, 15) for s in sheets_hdr15]:
        try:
            df = pd.read_excel(FORMULAR_PATH, sheet_name=sheet, header=hdr)
            df.columns = [str(c).strip() for c in df.columns]
            cols_needed = ["Județul", "Staţia de racord", "Puterea aprobată [MW]"]
            if all(c in df.columns for c in cols_needed):
                sub = df[cols_needed].copy()
                sub.columns = ["Județ", "Stație", "MW_Aprobat"]
                sub = sub.dropna(subset=["Stație"])
                sub["MW_Aprobat"] = pd.to_numeric(sub["MW_Aprobat"], errors="coerce").fillna(0.0)
                sub["Județ"] = sub["Județ"].apply(normalize_county)
                sub["Stație"] = sub["Stație"].apply(lambda x: re.sub(r"\s+", " ", str(x).strip()))
                frames.append(sub)
        except Exception as e:
            print(f"[WARN] Sheet '{sheet}': {e}")

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["Județ", "Stație", "MW_Aprobat"])


def load_zone_capacity() -> dict[str, dict]:
    if not os.path.exists(CAPACITATE_PATH):
        print("[WARN] Fișier Capacitate lipsă.")
        return {}

    df = pd.read_excel(CAPACITATE_PATH, sheet_name="Capacitate de racordare", header=0)
    df.columns = [str(c).strip() for c in df.columns]

    zone_col    = df.columns[0]
    cap_col     = df.columns[1]
    aprobat_col = df.columns[2]
    stocare_col = df.columns[3]

    result: dict[str, dict] = {}
    for _, row in df.iterrows():
        zona = str(row[zone_col]).strip()
        if not zona or zona.lower().startswith("not") or zona == "nan":
            continue
        try:
            cap_totala  = float(row[cap_col])
            aprobat_nec = float(row[aprobat_col]) if pd.notna(row[aprobat_col]) else 0.0
            stocare_nec = float(row[stocare_col]) if pd.notna(row[stocare_col]) else 0.0
            ramasa = max(0.0, cap_totala - aprobat_nec - stocare_nec)
            result[zona] = {
                "cap_totala":  round(cap_totala, 3),
                "aprobat_nec": round(aprobat_nec, 3),
                "stocare_nec": round(stocare_nec, 3),
                "cap_ramasa":  round(ramasa, 3),
            }
        except (ValueError, TypeError):
            continue
    return result


# ── Încărcare la startup ──────────────────────────────────────────────────────
print("[INFO] Se încarcă datele Excel ANRE...")
FORMULAR_DF   = load_formular_data()
ZONE_CAPACITY = load_zone_capacity()

STATION_STATS: pd.DataFrame = pd.DataFrame(columns=["Stație", "Județ", "MW_Total"])
if not FORMULAR_DF.empty:
    STATION_STATS = (
        FORMULAR_DF.groupby(["Stație", "Județ"])
        .agg(MW_Total=("MW_Aprobat", "sum"))
        .reset_index()
    )

print(f"[INFO] {len(STATION_STATS)} stații unice | {len(ZONE_CAPACITY)} zone ANRE | OpenAI: {'DA' if openai_client else 'NU'}")


# ─────────────────────────────────────────────────────────────────────────────
# Haversine — NESCHIMBAT
# ─────────────────────────────────────────────────────────────────────────────
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─────────────────────────────────────────────────────────────────────────────
# Logică rețea — NESCHIMBATĂ (Regula de Aur)
# ─────────────────────────────────────────────────────────────────────────────
def find_closest_station(lat: float, lon: float) -> tuple[str, float, dict]:
    best_name, best_dist, best_coords = "", float("inf"), {}
    for name, coords in STATION_COORDS.items():
        d = haversine(lat, lon, coords["lat"], coords["lon"])
        if d < best_dist:
            best_dist, best_name, best_coords = d, name, coords
    return best_name, round(best_dist, 2), best_coords


def get_capacity_data(station_name: str, station_coords: dict, requested_mw: float) -> dict:
    judet = normalize_county(station_coords.get("judet", ""))
    zona  = COUNTY_TO_ZONE.get(judet, "J3")

    norm = re.sub(r"\s+", " ", station_name.upper().strip())
    match_rows = STATION_STATS[
        STATION_STATS["Stație"].apply(lambda x: re.sub(r"\s+", " ", x.upper().strip())) == norm
    ]
    mw_aprobat_statie = float(match_rows["MW_Total"].sum()) if not match_rows.empty else 0.0

    zone_data      = ZONE_CAPACITY.get(zona, {})
    mw_zona_totala = zone_data.get("cap_totala", 500.0)
    mw_zona_ramasa = zone_data.get("cap_ramasa",  200.0)

    nr_statii_judet = len(STATION_STATS[STATION_STATS["Județ"] == judet]) if not STATION_STATS.empty else 5
    nr_statii_judet = max(nr_statii_judet, 1)
    cap_standard = max(50.0, mw_zona_totala / max(nr_statii_judet, 1))

    cap_ramasa_statie = max(0.0, cap_standard - mw_aprobat_statie)

    return {
        "zona":               zona,
        "judet":              judet,
        "mw_aprobat_statie":  round(mw_aprobat_statie, 2),
        "cap_standard":       round(cap_standard, 2),
        "cap_ramasa_statie":  round(cap_ramasa_statie, 2),
        "mw_zona_totala":     round(mw_zona_totala, 2),
        "mw_zona_ramasa":     round(mw_zona_ramasa, 2),
    }


def compute_risk_score(requested_mw: float, cap: dict) -> float:
    # ─── FUNCȚIE PROTEJATĂ — NU SE MODIFICĂ ──────────────────────────────────
    cap_r  = cap["cap_ramasa_statie"]
    cap_s  = cap["cap_standard"]
    zona_r = cap["mw_zona_ramasa"]

    if cap_r <= 0 or zona_r <= 0:
        return 100.0

    # Risc stație
    if requested_mw >= cap_r:
        risc_statie = 100.0
    else:
        risc_statie = min(99.9, (requested_mw / cap_s) * 100 * (1 + (requested_mw / max(cap_r, 0.01)) * 0.5))

    # Risc zonă
    risc_zona = min(100.0, (requested_mw / max(zona_r, 1)) * 60.0)

    return round(min(100.0, max(0.0, 0.7 * risc_statie + 0.3 * risc_zona)), 1)
    # ─────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# NOU: Module de fezabilitate tehnico-economică
# ─────────────────────────────────────────────────────────────────────────────

def check_env_flag(lat: float, lon: float) -> bool:
    """
    Returnează True dacă locația se află la mai puțin de 4 km față de
    Pădurea Bârnova (arie protejată Natura 2000, coordonate: 47.05N, 27.63E).
    """
    dist = haversine(lat, lon, BARNOVA_LAT, BARNOVA_LON)
    return dist < BARNOVA_RADIUS_KM


def compute_capex(dist_km: float, requested_mw: float) -> tuple[float, float]:
    """
    Estimează CAPEX linie electrică:
    - capex_eur    = dist_km * 90.000 EUR/km
    - capex_per_mw = capex_eur / requested_mw
    """
    capex_eur    = round(dist_km * COST_EUR_PER_KM, 2)
    capex_per_mw = round(capex_eur / max(requested_mw, 0.01), 2)
    return capex_eur, capex_per_mw


async def fetch_solar_radiation(lat: float, lon: float) -> float:
    """
    Interogă Open-Meteo Archive API pentru media anuală a radiației solare
    (shortwave_radiation_sum, kWh/m²/an) pentru anul 2023.
    Fallback: 1250.0 kWh/m²/an dacă API-ul eșuează.
    """
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date=2023-01-01&end_date=2023-12-31"
        f"&daily=shortwave_radiation_sum&timezone=auto"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data   = resp.json()
            values = data.get("daily", {}).get("shortwave_radiation_sum", [])
            # Filtrăm None-urile și calculăm media
            valid  = [v for v in values if v is not None]
            if not valid:
                print("[WARN] Open-Meteo: niciun datum valid — folosesc fallback 1250.0")
                return 1250.0
            media = round(sum(valid) / len(valid), 2)
            print(f"[INFO] Open-Meteo: {len(valid)} zile, medie radiație = {media} kWh/m²/zi → {round(media * 365, 1)} kWh/m²/an")
            # API-ul returnează valori zilnice (kWh/m²/zi); suma anuală e mai relevantă
            return round(sum(valid), 1)
    except httpx.TimeoutException:
        print("[WARN] Open-Meteo: timeout — fallback 1250.0")
        return 1250.0
    except Exception as exc:
        print(f"[WARN] Open-Meteo error: {exc} — fallback 1250.0")
        return 1250.0


async def fetch_elevation(lat: float, lon: float) -> int:
    """
    Interogă Open-Elevation API pentru elevația terenului la coordonatele date.
    Fallback: 0 metri dacă API-ul eșuează.
    """
    url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data    = resp.json()
            results = data.get("results", [])
            if results:
                elevation = int(results[0].get("elevation", 0))
                print(f"[INFO] Open-Elevation: {elevation} m la ({lat}, {lon})")
                return elevation
            print("[WARN] Open-Elevation: răspuns gol — fallback 0")
            return 0
    except httpx.TimeoutException:
        print("[WARN] Open-Elevation: timeout — fallback 0")
        return 0
    except Exception as exc:
        print(f"[WARN] Open-Elevation error: {exc} — fallback 0")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI insight — actualizat cu env_flag și date fezabilitate
# ─────────────────────────────────────────────────────────────────────────────
def generate_ai_insight(
    station: str,
    dist_km: float,
    cap: dict,
    risk: float,
    mw: float,
    env_flag: bool = False,
) -> str:
    # Directivă suplimentară dacă locația se suprapune cu aria protejată
    natura_2000_directive = ""
    if env_flag:
        natura_2000_directive = (
            "\n\nATENȚIE OBLIGATORIE — NATURA 2000: Locația proiectului se află în perimetrul de "
            "4 km față de Pădurea Bârnova, sit Natura 2000 (ROSCI0256). "
            "Trebuie să avertizezi EXPLICIT investitorul că proiectul poate fi supus procedurii "
            "de evaluare adecvată (EA) conform Directivei Habitate 92/43/CEE, că poate exista "
            "INTERDICȚIE DE CONSTRUIRE sau condiționări severe din partea Agenției pentru Protecția "
            "Mediului Iași, și că termenul procedurii de mediu poate depăși 18 luni. "
            "Recomandă consultarea unui expert de mediu ÎNAINTE de orice demers tehnic."
        )

    prompt = f"""Ești un consultant expert în rețele electrice din România.
Generează un raport profesional de EXACT 3 paragrafe, în limba română, fără titluri, fără liste, fără bullets.
Tonul: expert B2B, precis, acționabil. ADRESEAZĂ-TE DIRECT investitorului (pronume pers. a II-a: "proiectul tău", "solicitarea ta"). Bazează-te STRICT pe datele de mai jos.

DATE DE ANALIZĂ:
- Stație racordare identificată: {station}
- Județ / Zonă rețea ANRE: {cap.get('judet')} / Zona {cap.get('zona')}
- Distanță locația ta → stație: {dist_km} km
- Putere solicitată: {mw} MW
- MW deja aprobat la stație (date ANRE): {cap.get('mw_aprobat_statie')} MW
- Capacitate estimată stație: {cap.get('cap_standard')} MW
- Capacitate reziduală stație: {cap.get('cap_ramasa_statie')} MW
- Capacitate totală zonă {cap.get('zona')} (Ordin ANRE 137/2021): {cap.get('mw_zona_totala')} MW
- Capacitate rămasă în zonă: {cap.get('mw_zona_ramasa')} MW
- Scor risc congestionare GridScout: {risk}%
- Suprapunere arie protejată Natura 2000 (Bârnova): {'DA — RISC MAJOR DE MEDIU' if env_flag else 'Nu'}
{natura_2000_directive}

STRUCTURA OBLIGATORIE:
Paragraful 1: Explică starea actuală a stației și zonei de rețea, raportat la distanța față de locația aleasă.
Paragraful 2: Analizează scorul de risc de {risk}% și explică-i clar implicațiile pentru solicitarea de {mw} MW.{'  Integrează avertismentul Natura 2000 în mod proeminent dacă env_flag este True.' if env_flag else ''}
Paragraful 3: Oferă o recomandare directă și acționabilă (ATR, studiu de soluție, riscuri procedurale, sau dacă trebuie căutată altă locație).

Răspunde DOAR cu cele 3 paragrafe separate de un rând liber. Fără alt text."""

    try:
        resp = openai_client.responses.create(
            model="gpt-4o-mini",
            input=[{
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}]
            }]
        )
        return resp.output_text
    except Exception as e:
        print(f"[WARN] OpenAI API error: {e}")
        return _fallback_insight(station, dist_km, cap, risk, mw, env_flag)


def _fallback_insight(
    station: str, dist_km: float, cap: dict,
    risk: float, mw: float, env_flag: bool
) -> str:
    nivel = "RIDICAT" if risk >= 80 else ("MODERAT" if risk >= 40 else "SCĂZUT")
    zona  = cap.get("zona", "N/A")
    cap_r = cap.get("cap_ramasa_statie", 0)
    mw_zr = cap.get("mw_zona_ramasa", 0)

    p1 = (f"Stația {station} (zona ANRE {zona}) prezintă o capacitate reziduală estimată de "
          f"{cap_r:.1f} MW, la {dist_km:.1f} km față de locația proiectului tău de {mw:.1f} MW.")
    p2 = (f"Scorul de risc de {risk:.1f}% (nivel {nivel}) reflectă presiunea cumulată la nivel "
          f"de stație și zonă; capacitatea rămasă în zona {zona} este de {mw_zr:.1f} MW conform "
          f"Ordinului ANRE 137/2021.")
    if env_flag:
        p3 = ("⚠️ ATENȚIE CRITICĂ: Locația ta se suprapune cu aria protejată Natura 2000 — "
              "Pădurea Bârnova (ROSCI0256). Înainte de orice demers tehnic, consultă un expert "
              "de mediu; procedura de evaluare adecvată poate dura 12–18 luni și poate bloca "
              "complet proiectul. Recomandăm urgent identificarea unei locații alternative.")
    elif risk >= 40:
        p3 = ("Racordarea necesită un studiu de soluție aprofundat și negocieri cu operatorul "
              "de rețea; estimăm 6–12 luni pentru obținerea ATR cu posibile lucrări de întărire.")
    else:
        p3 = ("Condițiile de rețea sunt favorabile; recomandăm inițierea imediată a procedurii "
              "ATR în regim standard ANRE, cu o estimare de 3–6 luni până la avizul pozitiv.")
    return f"{p1}\n\n{p2}\n\n{p3}"


# ─────────────────────────────────────────────────────────────────────────────
# Schema request
# ─────────────────────────────────────────────────────────────────────────────
class EvaluateRequest(BaseModel):
    lat: float
    lon: float
    requested_mw: float


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint principal
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/evaluate-risk")
async def evaluate_risk(req: EvaluateRequest):
    if req.requested_mw <= 0:
        raise HTTPException(400, detail="Puterea solicitată trebuie să fie pozitivă.")

    # ── Logică existentă (neschimbată) ───────────────────────────────────────
    station_name, dist_km, station_coords = find_closest_station(req.lat, req.lon)
    cap  = get_capacity_data(station_name, station_coords, req.requested_mw)
    risk = compute_risk_score(req.requested_mw, cap)  # ← NESCHIMBAT

    # ── Module noi de fezabilitate ────────────────────────────────────────────
    env_flag   = check_env_flag(req.lat, req.lon)
    capex_eur, capex_per_mw = compute_capex(dist_km, req.requested_mw)

    # Apeluri API externe (async, cu fallback solid)
    resource_efficiency = await fetch_solar_radiation(req.lat, req.lon)
    elevation_meters    = await fetch_elevation(req.lat, req.lon)

    # ── AI Insight (preia env_flag) ───────────────────────────────────────────
    insight = generate_ai_insight(
        station=station_name,
        dist_km=dist_km,
        cap=cap,
        risk=risk,
        mw=req.requested_mw,
        env_flag=env_flag,
    )

    return {
        # ── Câmpuri existente ──────────────────────────────────────────────
        "closest_station":   station_name,
        "distance_km":       dist_km,
        "capacity_left":     cap["cap_ramasa_statie"],
        "risk_score":        risk,
        "ai_insight":        insight,
        "station_lat":       station_coords["lat"],
        "station_lon":       station_coords["lon"],
        "zona_retea":        cap["zona"],
        "judet_statie":      cap["judet"],
        "mw_aprobat_statie": cap["mw_aprobat_statie"],
        "mw_zona_ramasa":    cap["mw_zona_ramasa"],
        "mw_zona_totala":    cap["mw_zona_totala"],
        # ── Câmpuri noi v3 ─────────────────────────────────────────────────
        "env_flag":             env_flag,
        "capex_eur":            capex_eur,
        "capex_per_mw":         capex_per_mw,
        "resource_efficiency":  resource_efficiency,
        "elevation_meters":     elevation_meters,
    }


@app.get("/")
async def root():
    return {
        "mesaj":           "GridScout API v3.0 ✅",
        "excel_incarcat":  not FORMULAR_DF.empty,
        "zone_incarcare":  len(ZONE_CAPACITY),
        "statii_unice":    len(STATION_STATS),
        "openai_activ":    openai_client is not None,
        "versiune":        "3.0.0",
    }
