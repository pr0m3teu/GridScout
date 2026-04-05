import { useState, useCallback } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import {
  Zap, MapPin, AlertTriangle, BarChart3,
  Loader2, Activity, ChevronRight, Radio,
  TrendingUp, Sun, Mountain, FileText,
  Shield, AlertCircle, CheckCircle, Info,
  Navigation,
} from 'lucide-react';
import GridMap from './components/MapComponent';

const API_URL = 'http://localhost:8000';

// ── Risk score: higher = worse (congestion) ───────────────────────────────
function riskProfile(score) {
  if (score >= 80) return { color: '#B91C1C', bg: '#FEF2F2', border: '#FECACA', label: 'Risc Ridicat' };
  if (score >= 40) return { color: '#92400E', bg: '#FFFBEB', border: '#FDE68A', label: 'Risc Moderat' };
  return             { color: '#14532D', bg: '#F0FDF4', border: '#BBF7D0', label: 'Risc Scăzut' };
}

// ── Route score: higher = better (viability) ──────────────────────────────
function routeProfile(score) {
  if (score === null || score === undefined) return null;
  if (score >= 80) return { color: '#14532D', bg: '#F0FDF4', border: '#BBF7D0', label: 'Traseu Excelent' };
  if (score >= 60) return { color: '#1D4ED8', bg: '#EBF5FF', border: '#DBEAFE', label: 'Traseu Viabil' };
  if (score >= 40) return { color: '#92400E', bg: '#FFFBEB', border: '#FDE68A', label: 'Traseu Constrâns' };
  return             { color: '#B91C1C', bg: '#FEF2F2', border: '#FECACA', label: 'Constrângeri Ridicate' };
}

function formatEur(value) {
  if (value >= 1_000_000) return `€${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000)     return `€${(value / 1_000).toFixed(1)}K`;
  return `€${value.toFixed(0)}`;
}

function RiskGauge({ score }) {
  const p    = riskProfile(score);
  const data = [{ value: score }, { value: 100 - score }];
  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-48 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={64} outerRadius={84}
              startAngle={90} endAngle={-270} dataKey="value" strokeWidth={0}>
              <Cell fill={p.color} />
              <Cell fill="#F3F4F6" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-4xl font-bold font-mono leading-none" style={{ color: p.color }}>{score}</span>
          <span className="text-sm text-ink-500 mt-1 font-mono">/ 100</span>
        </div>
      </div>
      <div className="flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold border"
        style={{ color: p.color, backgroundColor: p.bg, borderColor: p.border }}>
        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: p.color }} />
        {p.label}
      </div>
    </div>
  );
}

function Card({ children, className = '' }) {
  return (
    <div className={`bg-surface border border-border rounded-xl shadow-card ${className}`}>
      {children}
    </div>
  );
}

function SectionHeader({ icon: Icon, title, action }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <Icon size={15} className="text-ink-400" />
        <h2 className="text-xs font-semibold text-ink-500 uppercase tracking-widest">{title}</h2>
      </div>
      {action}
    </div>
  );
}

function DataRow({ label, value, mono = false, highlight = false }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border last:border-0">
      <span className="text-xs text-ink-500">{label}</span>
      <span className={`text-xs font-semibold ${mono ? 'font-mono' : ''} ${highlight ? 'text-brand-700' : 'text-ink-900'}`}>
        {value}
      </span>
    </div>
  );
}

function NumberInput({ label, id, value, onChange, placeholder, step = 'any' }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-semibold text-ink-500 uppercase tracking-wider">{label}</label>
      <input
        id={id} type="number" step={step} value={value}
        onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full bg-canvas border border-border rounded-lg px-3 py-2.5
          text-ink-900 placeholder-ink-400 text-sm font-mono
          focus:outline-none focus:ring-2 focus:ring-brand-500/30
          focus:border-brand-500 transition-all duration-150"
      />
    </div>
  );
}

function SkeletonRow({ label }) {
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-border last:border-0">
      <span className="text-xs text-ink-400">{label}</span>
      <div className="skeleton h-3 w-20" />
    </div>
  );
}

// ── Dynamic constraint alerts — driven entirely by API response data ────────
function ConstraintAlerts({ violations, constraintSource }) {
  if (!violations || violations.length === 0) return null;

  const protectedCrossings = violations.filter(v => v.category === 'protected_area');
  const infraCrossings     = violations.filter(v => v.category !== 'protected_area');

  return (
    <div className="flex flex-col gap-2">
      {protectedCrossings.map((v, i) => (
        <Card key={`pa-${i}`} className="p-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 w-7 h-7 rounded-lg bg-red-50 border border-red-100 flex items-center justify-center flex-shrink-0">
              <Shield size={14} className="text-risk-high" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-risk-high mb-1 truncate">
                Zonă Protejată: {v.name}
              </p>
              <p className="text-xs text-ink-500 leading-relaxed">
                {v.detail?.protection_type === 'national_park'
                  ? 'Parc național. '
                  : v.detail?.protection_type === 'nature_reserve'
                  ? 'Rezervație naturală. '
                  : 'Zonă protejată. '}
                {v.detail?.iucn_level && v.detail.iucn_level !== 'unknown'
                  ? `Categoria IUCN ${v.detail.iucn_level}. `
                  : ''}
                Poate fi necesară o Evaluare Adecvată conform Directivei Habitate 92/43/CEE.
                Consultați un specialist în mediu înainte de orice depunere tehnică.
              </p>
            </div>
          </div>
        </Card>
      ))}

      {infraCrossings.length > 0 && (
        <Card className="p-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 w-7 h-7 rounded-lg bg-amber-50 border border-amber-100 flex items-center justify-center flex-shrink-0">
              <AlertCircle size={14} className="text-amber-700" />
            </div>
            <div>
              <p className="text-sm font-semibold text-amber-800 mb-1">
                Traversări Infrastructură
              </p>
              <p className="text-xs text-ink-500 leading-relaxed">
                Traseul propus traversează{' '}
                {infraCrossings.map((v, i) => (
                  <span key={i}>
                    {i > 0 ? ', ' : ''}
                    <span className="font-medium text-ink-700">{v.name.toLowerCase()}</span>
                  </span>
                ))}.
                {' '}Aceste traversări necesită avize tehnice și pot extinde termenele de construcție.
              </p>
            </div>
          </div>
        </Card>
      )}

      {constraintSource === 'fallback' && (
        <div className="flex items-center gap-2 text-xs text-ink-400 px-1">
          <Info size={12} />
          Date de constrângeri indisponibile — analiza live nu a putut fi finalizată.
        </div>
      )}
    </div>
  );
}

// ── Route viability score card ─────────────────────────────────────────────
function RouteViabilityCard({ routeScore, violations, constraintSource }) {
  const p = routeProfile(routeScore);

  const protectedCount = violations?.filter(v => v.category === 'protected_area').length ?? 0;
  const infraCount     = violations?.filter(v => v.category !== 'protected_area').length ?? 0;

  return (
    <Card className="p-6">
      <SectionHeader
        icon={Navigation}
        title="Viabilitate Traseu"
        action={
          constraintSource && constraintSource !== 'unavailable' && (
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium
              ${constraintSource === 'overpass'
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                : constraintSource === 'cache'
                ? 'text-brand-700 bg-brand-50 border-brand-100'
                : 'text-ink-500 bg-gray-50 border-gray-200'}`}>
              {constraintSource === 'overpass' ? 'Live · Overpass' : constraintSource === 'cache' ? 'Din Cache' : constraintSource}
            </span>
          )
        }
      />

      {routeScore !== null && routeScore !== undefined ? (
        <>
          <div className="flex items-center gap-4 mb-5">
            <div className="flex-1">
              <div className="flex items-baseline gap-1.5 mb-2">
                <span className="text-3xl font-bold font-mono" style={{ color: p.color }}>{routeScore}</span>
                <span className="text-sm text-ink-400 font-mono">/ 100</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-semibold rounded-full px-3 py-1 w-fit border"
                style={{ color: p.color, backgroundColor: p.bg, borderColor: p.border }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: p.color }} />
                {p.label}
              </div>
            </div>
            <div className="flex flex-col gap-1.5 text-right">
              {protectedCount > 0 && (
                <div className="flex items-center gap-1.5 justify-end text-xs text-risk-high">
                  <Shield size={11} />
                  {protectedCount} zonă{protectedCount > 1 ? ' protejate' : ' protejată'}
                </div>
              )}
              {infraCount > 0 && (
                <div className="flex items-center gap-1.5 justify-end text-xs text-amber-700">
                  <AlertCircle size={11} />
                  {infraCount} traversare{infraCount > 1 ? ' infrastructură' : ' infrastructură'}
                </div>
              )}
              {protectedCount === 0 && infraCount === 0 && (
                <div className="flex items-center gap-1.5 justify-end text-xs text-emerald-700">
                  <CheckCircle size={11} />
                  Nicio constrângere detectată
                </div>
              )}
            </div>
          </div>

          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700"
              style={{ width: `${routeScore}%`, backgroundColor: p.color }} />
          </div>
          <div className="flex justify-between text-xs text-ink-400 mt-1.5 font-mono">
            <span>0</span>
            <span>50</span>
            <span>100</span>
          </div>
        </>
      ) : (
        <div className="flex items-center gap-2 text-xs text-ink-400 py-4">
          <Info size={13} />
          Analiza viabilității traseului indisponibilă — datele de constrângeri nu au putut fi obținute.
        </div>
      )}
    </Card>
  );
}

// ── Root component ─────────────────────────────────────────────────────────
export default function App() {
  const [lat,     setLat]     = useState('');
  const [lon,     setLon]     = useState('');
  const [mw,      setMw]      = useState('');
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');
  const [result,  setResult]  = useState(null);

  const handleMapClick = useCallback((clickLat, clickLon) => {
    setLat(String(clickLat));
    setLon(String(clickLon));
  }, []);

  const handleSubmit = async () => {
    setError('');
    setResult(null);

    if (!lat || !lon || !mw) {
      setError('Completați toate câmpurile înainte de a rula analiza.');
      return;
    }

    const pLat = parseFloat(lat);
    const pLon = parseFloat(lon);
    const pMw  = parseFloat(mw);

    if (isNaN(pLat) || isNaN(pLon) || isNaN(pMw) || pMw <= 0) {
      setError('Date invalide. Verificați coordonatele și capacitatea solicitată.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/evaluate-risk`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ lat: pLat, lon: pLon, requested_mw: pMw }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Eroare server ${res.status}`);
      }
      setResult(await res.json());
    } catch (err) {
      setError(`Conexiune eșuată: ${err.message}. Asigurați-vă că backend-ul rulează pe portul 8000.`);
    } finally {
      setLoading(false);
    }
  };

  const riskCfg      = result ? riskProfile(result.risk_score) : null;
  const insightParas = result?.ai_insight
    ? result.ai_insight.split(/\n\n+/).filter(p => p.trim())
    : [];
  const zoneUsagePct = result?.mw_zona_totala > 0
    ? Math.min(100, ((result.mw_zona_totala - result.mw_zona_ramasa) / result.mw_zona_totala) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-canvas text-ink-900 flex flex-col">

      <header className="bg-surface border-b border-border px-8 py-3.5 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-700 flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-base font-bold text-ink-900 tracking-tight">GridScout</span>
            <span className="text-xs text-brand-600 font-medium bg-brand-50 border border-brand-100 px-2 py-0.5 rounded-full">
              România · ANRE
            </span>
          </div>
        </div>
        <div className="flex items-center gap-5 text-xs text-ink-400">
          <span className="flex items-center gap-1.5">
            <Radio size={11} className="text-emerald-500" />
            Date ANRE Live · Ordin 137/2021
          </span>
          <span className="flex items-center gap-1.5">
            <Activity size={11} className="text-brand-500" />
            Platformă de Inteligență Congestionare
          </span>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden" style={{ height: 'calc(100vh - 57px)' }}>

        {/* Left panel — 60% */}
        <section className="flex flex-col gap-4 p-5" style={{ width: '60%' }}>
          <Card className="p-5">
            <SectionHeader
              icon={MapPin}
              title="Parametri Amplasament"
              action={<span className="text-xs text-ink-400">Click pe hartă pentru coordonate</span>}
            />
            <div className="grid grid-cols-3 gap-3 mb-4">
              <NumberInput label="Latitudine (°N)"          id="lat" value={lat} onChange={setLat} placeholder="47.1585" />
              <NumberInput label="Longitudine (°E)"         id="lon" value={lon} onChange={setLon} placeholder="27.6014" />
              <NumberInput label="Capacitate Solicitată (MW)" id="mw" value={mw}  onChange={setMw}  placeholder="15.0" step="0.1" />
            </div>
            {error && (
              <div className="mb-4 flex items-start gap-2 text-xs text-red-700
                bg-red-50 border border-red-200 rounded-lg px-3.5 py-3">
                <AlertTriangle size={14} className="mt-0.5 flex-shrink-0 text-red-500" />
                {error}
              </div>
            )}
            <button onClick={handleSubmit} disabled={loading}
              className="w-full flex items-center justify-center gap-2
                bg-brand-700 hover:bg-brand-800 disabled:opacity-50 disabled:cursor-not-allowed
                text-white font-semibold text-sm rounded-lg px-6 py-2.5
                transition-colors duration-150 active:scale-[0.99]">
              {loading
                ? <><Loader2 size={15} className="animate-spin" />Se rulează analiza…</>
                : <><Activity size={15} />Rulează Analiza de Racordare<ChevronRight size={14} /></>}
            </button>
          </Card>

          <Card className="flex-1 overflow-hidden p-2">
            <GridMap
              userLat={lat ? parseFloat(lat) : null}
              userLon={lon ? parseFloat(lon) : null}
              stationLat={result?.station_lat ?? null}
              stationLon={result?.station_lon ?? null}
              stationName={result?.closest_station ?? ''}
              envFlag={result?.env_flag ?? false}
              violations={result?.route_violations ?? []}
              onMapClick={handleMapClick}
            />
          </Card>
        </section>

        {/* Right panel — 40% */}
        <section className="flex flex-col gap-4 p-5 pl-0 overflow-y-auto" style={{ width: '40%' }}>

          {/* Congestion Risk Score */}
          <Card className="p-6">
            <SectionHeader icon={BarChart3} title="Scor Risc Congestionare" />
            {result ? (
              <>
                <RiskGauge score={result.risk_score} />
                <div className="mt-5 pt-4 border-t border-border">
                  <div className="flex justify-between text-xs text-ink-500 mb-2">
                    <span>Zona {result.zona_retea} — Utilizare Rețea</span>
                    <span className="font-mono font-semibold" style={{ color: riskCfg?.color }}>
                      {Math.round(zoneUsagePct)}% utilizat
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${zoneUsagePct}%`, backgroundColor: riskCfg?.color }} />
                  </div>
                  <div className="flex justify-between text-xs text-ink-400 mt-1.5 font-mono">
                    <span>0 MW</span>
                    <span>{result.mw_zona_totala} MW total</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 gap-3">
                <div className="w-32 h-32 rounded-full border-2 border-dashed border-border flex items-center justify-center">
                  <BarChart3 size={28} className="text-ink-300" />
                </div>
                <p className="text-ink-400 text-xs text-center leading-relaxed">
                  Introduceți parametrii proiectului și rulați analiza<br />pentru a genera un scor de risc.
                </p>
              </div>
            )}
          </Card>

          {/* Route Viability Score */}
          {result && (
            <RouteViabilityCard
              routeScore={result.route_score}
              violations={result.route_violations}
              constraintSource={result.constraint_source}
            />
          )}

          {/* Dynamic constraint alerts */}
          {result && result.route_violations?.length > 0 && (
            <ConstraintAlerts
              violations={result.route_violations}
              constraintSource={result.constraint_source}
            />
          )}

          {/* Intelligence Report */}
          <Card className="p-5">
            <SectionHeader icon={FileText} title="Raport de Expertiză" />
            {loading && (
              <div className="flex items-center gap-2 text-xs text-ink-400">
                <Loader2 size={13} className="animate-spin text-brand-500" />
                Se generează raportul…
              </div>
            )}
            {result && !loading && (
              <div className="space-y-3 animate-fadeIn">
                {insightParas.map((para, i) => (
                  <p key={i} className="text-xs text-ink-700 leading-relaxed">{para}</p>
                ))}
              </div>
            )}
            {!result && !loading && (
              <p className="text-xs text-ink-400 leading-relaxed">
                Evaluarea generată de AI va apărea aici după rularea analizei.
                Acoperă capacitatea rețelei, constrângerile de traseu și recomandări acționabile.
              </p>
            )}
          </Card>

          {/* Grid Connection Details */}
          <Card className="p-5">
            <SectionHeader icon={Zap} title="Detalii Racordare la Rețea" />
            {result ? (
              <>
                <DataRow label="Stație"                        value={result.closest_station}              highlight />
                <DataRow label="Județ"                         value={result.judet_statie || '—'} />
                <DataRow label="Zonă Rețea ANRE"               value={`Zona ${result.zona_retea}`}          highlight />
                <DataRow label="Distanță până la Stație"       value={`${result.distance_km} km`}           mono />
                <DataRow label="Capacitate Aprobată (ANRE)"    value={`${result.mw_aprobat_statie} MW`}     mono />
                <DataRow label="Capacitate Rămasă Stație"      value={`${result.capacity_left} MW`}         mono highlight />
                <DataRow label="Capacitate Totală Zonă"        value={`${result.mw_zona_totala} MW`}        mono />
                <DataRow label="Capacitate Rămasă Zonă"        value={`${result.mw_zona_ramasa} MW`}        mono highlight />
                <DataRow label="Capacitate Solicitată"         value={`${mw} MW`}                           mono />
                <DataRow label="Scor Risc Congestionare"       value={`${result.risk_score} / 100`}         mono />
                <DataRow label="Coordonate Stație"             value={`${result.station_lat}°N, ${result.station_lon}°E`} mono />
              </>
            ) : (
              ['Stație', 'Zonă Rețea ANRE', 'Distanță', 'Capacitate Aprobată',
               'Capacitate Rămasă', 'Capacitate Zonă', 'Scor Risc'].map(label => (
                <SkeletonRow key={label} label={label} />
              ))
            )}
          </Card>

          {/* Commercial Feasibility */}
          <Card className="p-5">
            <SectionHeader icon={TrendingUp} title="Fezabilitate Comercială" />
            {result ? (
              <>
                <DataRow label="CAPEX Racordare la Rețea"    value={formatEur(result.capex_eur)}          mono highlight />
                <DataRow label="Cost Specific"               value={`${formatEur(result.capex_per_mw)} / MW`} mono />
                <div className="flex items-center justify-between py-2.5 border-b border-border">
                  <span className="text-xs text-ink-500 flex items-center gap-1.5">
                    <Sun size={11} className="text-amber-500" />
                    Iradiere Solară (2023)
                  </span>
                  <span className="text-xs font-semibold font-mono text-ink-900">
                    {result.resource_efficiency.toLocaleString('ro')} kWh/m²/an
                  </span>
                </div>
                <div className="flex items-center justify-between py-2.5">
                  <span className="text-xs text-ink-500 flex items-center gap-1.5">
                    <Mountain size={11} className="text-ink-400" />
                    Altitudine Teren
                  </span>
                  <span className="text-xs font-semibold font-mono text-ink-900">
                    {result.elevation_meters} m
                  </span>
                </div>
                <p className="text-xs text-ink-400 mt-3 pt-3 border-t border-border leading-relaxed">
                  Estimare CAPEX: distanță × €90.000/km.
                  Iradiere: API Open-Meteo Archive.
                  Altitudine: API Open-Elevation.
                </p>
              </>
            ) : (
              ['CAPEX Racordare la Rețea', 'Cost Specific (€/MW)',
               'Iradiere Solară (kWh/m²/an)', 'Altitudine (m)'].map(label => (
                <SkeletonRow key={label} label={label} />
              ))
            )}
          </Card>

          <p className="text-center text-xs text-ink-400 pb-2">
            GridScout · ANRE Ordin 137/2021 · OpenStreetMap / Overpass · Open-Meteo · Open-Elevation
          </p>
        </section>
      </main>
    </div>
  );
}
