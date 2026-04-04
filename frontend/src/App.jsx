import { useState, useCallback } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import {
  Zap, MapPin, AlertTriangle, BarChart3,
  Loader2, Activity, ChevronRight, Radio,
  TrendingUp, Sun, Mountain, FileText, Shield,
} from 'lucide-react';
import GridMap from './components/MapComponent';

const API_URL = 'http://localhost:8000';

function riskProfile(score) {
  if (score >= 80) return {
    color:      '#B91C1C',
    background: '#FEF2F2',
    border:     '#FECACA',
    label:      'High Risk',
    track:      '#FCA5A5',
  };
  if (score >= 40) return {
    color:      '#92400E',
    background: '#FFFBEB',
    border:     '#FDE68A',
    label:      'Moderate Risk',
    track:      '#FCD34D',
  };
  return {
    color:      '#14532D',
    background: '#F0FDF4',
    border:     '#BBF7D0',
    label:      'Low Risk',
    track:      '#4ADE80',
  };
}

function formatEur(value) {
  if (value >= 1_000_000) return `€${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000)     return `€${(value / 1_000).toFixed(1)}K`;
  return `€${value.toFixed(0)}`;
}

function RiskGauge({ score }) {
  const profile = riskProfile(score);
  const data = [{ value: score }, { value: 100 - score }];

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-48 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%" cy="50%"
              innerRadius={64} outerRadius={84}
              startAngle={90} endAngle={-270}
              dataKey="value"
              strokeWidth={0}
            >
              <Cell fill={profile.color} />
              <Cell fill="#F3F4F6" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span
            className="text-4xl font-bold font-mono leading-none"
            style={{ color: profile.color }}
          >
            {score}
          </span>
          <span className="text-sm text-ink-500 mt-1 font-mono">/ 100</span>
        </div>
      </div>
      <div
        className="flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold border"
        style={{
          color:           profile.color,
          backgroundColor: profile.background,
          borderColor:     profile.border,
        }}
      >
        <span
          className="w-1.5 h-1.5 rounded-full animate-pulse"
          style={{ backgroundColor: profile.color }}
        />
        {profile.label}
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
        <h2 className="text-xs font-semibold text-ink-500 uppercase tracking-widest">
          {title}
        </h2>
      </div>
      {action}
    </div>
  );
}

function DataRow({ label, value, mono = false, highlight = false }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border last:border-0">
      <span className="text-xs text-ink-500">{label}</span>
      <span
        className={`text-xs font-semibold ${mono ? 'font-mono' : ''} ${
          highlight ? 'text-brand-700' : 'text-ink-900'
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function NumberInput({ label, id, value, onChange, placeholder, step = 'any' }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-semibold text-ink-500 uppercase tracking-wider">
        {label}
      </label>
      <input
        id={id}
        type="number"
        step={step}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
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

function EnvironmentalAlert() {
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 w-7 h-7 rounded-lg bg-red-50 border border-red-100 flex items-center justify-center flex-shrink-0">
          <Shield size={14} className="text-risk-high" />
        </div>
        <div>
          <p className="text-sm font-semibold text-risk-high mb-1">
            Natura 2000 Protected Area Detected
          </p>
          <p className="text-xs text-ink-500 leading-relaxed">
            The selected site falls within 4 km of{' '}
            <span className="font-semibold text-ink-700">Bârnova Forest (ROSCI0256)</span> —
            a Natura 2000 conservation area. The project may require an Appropriate Assessment
            under Habitats Directive 92/43/EEC. Consult an environmental specialist before
            proceeding with any technical submissions.
          </p>
        </div>
      </div>
    </Card>
  );
}

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
      setError('Please fill in all fields before running the analysis.');
      return;
    }

    const pLat = parseFloat(lat);
    const pLon = parseFloat(lon);
    const pMw  = parseFloat(mw);

    if (isNaN(pLat) || isNaN(pLon) || isNaN(pMw) || pMw <= 0) {
      setError('Invalid input. Please verify coordinates and the requested capacity.');
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
        throw new Error(err.detail || `Server error ${res.status}`);
      }
      setResult(await res.json());
    } catch (err) {
      setError(`Connection failed: ${err.message}. Ensure the backend is running on port 8000.`);
    } finally {
      setLoading(false);
    }
  };

  const profile      = result ? riskProfile(result.risk_score) : null;
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
              Romania · ANRE
            </span>
          </div>
        </div>
        <div className="flex items-center gap-5 text-xs text-ink-400">
          <span className="flex items-center gap-1.5">
            <Radio size={11} className="text-emerald-500" />
            Live ANRE Data · Order 137/2021
          </span>
          <span className="flex items-center gap-1.5">
            <Activity size={11} className="text-brand-500" />
            Congestion Intelligence Platform
          </span>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden" style={{ height: 'calc(100vh - 57px)' }}>

        {/* Left panel — 60% */}
        <section className="flex flex-col gap-4 p-5" style={{ width: '60%' }}>

          <Card className="p-5">
            <SectionHeader
              icon={MapPin}
              title="Site Parameters"
              action={
                <span className="text-xs text-ink-400">Click map to set coordinates</span>
              }
            />

            <div className="grid grid-cols-3 gap-3 mb-4">
              <NumberInput
                label="Latitude (°N)"
                id="lat"
                value={lat}
                onChange={setLat}
                placeholder="47.1585"
              />
              <NumberInput
                label="Longitude (°E)"
                id="lon"
                value={lon}
                onChange={setLon}
                placeholder="27.6014"
              />
              <NumberInput
                label="Requested Capacity (MW)"
                id="mw"
                value={mw}
                onChange={setMw}
                placeholder="15.0"
                step="0.1"
              />
            </div>

            {error && (
              <div className="mb-4 flex items-start gap-2 text-xs text-red-700
                bg-red-50 border border-red-200 rounded-lg px-3.5 py-3">
                <AlertTriangle size={14} className="mt-0.5 flex-shrink-0 text-red-500" />
                {error}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2
                bg-brand-700 hover:bg-brand-800
                disabled:opacity-50 disabled:cursor-not-allowed
                text-white font-semibold text-sm rounded-lg px-6 py-2.5
                transition-colors duration-150 active:scale-[0.99]"
            >
              {loading ? (
                <><Loader2 size={15} className="animate-spin" />Running Analysis…</>
              ) : (
                <><Activity size={15} />Run Interconnection Analysis<ChevronRight size={14} /></>
              )}
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
              onMapClick={handleMapClick}
            />
          </Card>
        </section>

        {/* Right panel — 40% */}
        <section
          className="flex flex-col gap-4 p-5 pl-0 overflow-y-auto"
          style={{ width: '40%' }}
        >

          {/* Congestion Risk Score */}
          <Card className="p-6">
            <SectionHeader icon={BarChart3} title="Congestion Risk Score" />

            {result ? (
              <>
                <RiskGauge score={result.risk_score} />

                <div className="mt-5 pt-4 border-t border-border">
                  <div className="flex justify-between text-xs text-ink-500 mb-2">
                    <span>Zone {result.zona_retea} — Network Utilization</span>
                    <span className="font-mono font-semibold" style={{ color: profile?.color }}>
                      {Math.round(zoneUsagePct)}% used
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width:           `${zoneUsagePct}%`,
                        backgroundColor: profile?.color,
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-ink-400 mt-1.5 font-mono">
                    <span>0 MW</span>
                    <span>{result.mw_zona_totala} MW total</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 gap-3">
                <div className="w-32 h-32 rounded-full border-2 border-dashed border-border
                  flex items-center justify-center">
                  <BarChart3 size={28} className="text-ink-300" />
                </div>
                <p className="text-ink-400 text-xs text-center leading-relaxed">
                  Enter project parameters and run the analysis<br />to generate a risk score.
                </p>
              </div>
            )}
          </Card>

          {/* Environmental Alert */}
          {result?.env_flag && <EnvironmentalAlert />}

          {/* Intelligence Report */}
          <Card className="p-5">
            <SectionHeader icon={FileText} title="Intelligence Report" />

            {loading && (
              <div className="flex items-center gap-2 text-xs text-ink-400">
                <Loader2 size={13} className="animate-spin text-brand-500" />
                Generating report…
              </div>
            )}

            {result && !loading && (
              <div className="space-y-3 animate-fadeIn">
                {insightParas.map((para, i) => (
                  <p key={i} className="text-xs text-ink-700 leading-relaxed">
                    {para}
                  </p>
                ))}
              </div>
            )}

            {!result && !loading && (
              <p className="text-xs text-ink-400 leading-relaxed">
                The AI-generated assessment will appear here after the analysis runs.
                It covers grid capacity, environmental exposure, and actionable recommendations.
              </p>
            )}
          </Card>

          {/* Grid Connection Details */}
          <Card className="p-5">
            <SectionHeader icon={Zap} title="Grid Connection Details" />

            {result ? (
              <>
                <DataRow label="Substation"          value={result.closest_station}         highlight />
                <DataRow label="County"              value={result.judet_statie || '—'} />
                <DataRow label="ANRE Network Zone"   value={`Zone ${result.zona_retea}`}     highlight />
                <DataRow label="Distance to Substation" value={`${result.distance_km} km`}  mono />
                <DataRow label="Approved Capacity (ANRE)" value={`${result.mw_aprobat_statie} MW`} mono />
                <DataRow label="Remaining Station Capacity" value={`${result.capacity_left} MW`} mono highlight />
                <DataRow label="Zone Total Capacity" value={`${result.mw_zona_totala} MW`}  mono />
                <DataRow label="Zone Remaining Capacity" value={`${result.mw_zona_ramasa} MW`} mono highlight />
                <DataRow label="Requested Capacity"  value={`${mw} MW`}                     mono />
                <DataRow label="Congestion Risk Score" value={`${result.risk_score} / 100`} mono />
                <DataRow
                  label="Substation Coordinates"
                  value={`${result.station_lat}°N, ${result.station_lon}°E`}
                  mono
                />
              </>
            ) : (
              ['Substation', 'ANRE Network Zone', 'Distance', 'Approved Capacity',
               'Remaining Capacity', 'Zone Capacity', 'Risk Score'].map(label => (
                <SkeletonRow key={label} label={label} />
              ))
            )}
          </Card>

          {/* Commercial Feasibility */}
          <Card className="p-5">
            <SectionHeader icon={TrendingUp} title="Commercial Feasibility" />

            {result ? (
              <>
                <DataRow label="Estimated Grid Connection CAPEX" value={formatEur(result.capex_eur)} mono highlight />
                <DataRow label="Specific Cost"                   value={`${formatEur(result.capex_per_mw)} / MW`} mono />
                <div className="flex items-center justify-between py-2.5 border-b border-border">
                  <span className="text-xs text-ink-500 flex items-center gap-1.5">
                    <Sun size={11} className="text-amber-500" />
                    Solar Irradiance (2023)
                  </span>
                  <span className="text-xs font-semibold font-mono text-ink-900">
                    {result.resource_efficiency.toLocaleString('en')} kWh/m²/yr
                  </span>
                </div>
                <div className="flex items-center justify-between py-2.5">
                  <span className="text-xs text-ink-500 flex items-center gap-1.5">
                    <Mountain size={11} className="text-ink-400" />
                    Terrain Elevation
                  </span>
                  <span className="text-xs font-semibold font-mono text-ink-900">
                    {result.elevation_meters} m
                  </span>
                </div>
                <p className="text-xs text-ink-400 mt-3 pt-3 border-t border-border leading-relaxed">
                  CAPEX estimate: distance to substation × €90,000/km.
                  Irradiance: Open-Meteo Archive API. Elevation: Open-Elevation API.
                </p>
              </>
            ) : (
              ['Grid Connection CAPEX', 'Specific Cost (€/MW)',
               'Solar Irradiance (kWh/m²/yr)', 'Elevation (m)'].map(label => (
                <SkeletonRow key={label} label={label} />
              ))
            )}
          </Card>

          <p className="text-center text-xs text-ink-400 pb-2">
            GridScout · ANRE Order 137/2021 · Open-Meteo · Open-Elevation
          </p>
        </section>
      </main>
    </div>
  );
}