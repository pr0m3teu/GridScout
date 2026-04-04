import { useState, useCallback } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import {
  Zap, MapPin, AlertTriangle, Brain,
  BarChart3, Loader2, Activity, ChevronRight, Radio,
} from 'lucide-react';
import MapComponent from './components/MapComponent';

const API_URL = 'http://localhost:8000';

// ── Utilitar culori risc ──────────────────────────────────────────────────────
function getRiskConfig(score) {
  if (score >= 80) return {
    color: '#ef4444', bg: 'bg-red-500/10', border: 'border-red-500/30',
    label: 'RISC RIDICAT', dot: 'bg-red-400', glow: '0 0 20px #ef444440',
  };
  if (score >= 40) return {
    color: '#f59e0b', bg: 'bg-amber-500/10', border: 'border-amber-500/30',
    label: 'RISC MODERAT', dot: 'bg-amber-400', glow: '0 0 20px #f59e0b40',
  };
  return {
    color: '#22c55e', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30',
    label: 'RISC SCĂZUT', dot: 'bg-emerald-400', glow: '0 0 20px #22c55e40',
  };
}

// ── Donut gauge ───────────────────────────────────────────────────────────────
function RiskGauge({ score }) {
  const cfg  = getRiskConfig(score);
  const data = [{ value: score }, { value: 100 - score }];
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-52 h-52">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={68} outerRadius={90}
              startAngle={90} endAngle={-270} dataKey="value" strokeWidth={0}>
              <Cell fill={cfg.color} style={{ filter: `drop-shadow(${cfg.glow})` }} />
              <Cell fill="#1e293b" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-5xl font-black leading-none" style={{ color: cfg.color }}>{score}</span>
          <span className="text-base font-semibold text-slate-400 mt-1">%</span>
        </div>
      </div>
      <div className={`flex items-center gap-2 px-4 py-1.5 rounded-full border text-sm font-bold ${cfg.bg} ${cfg.border}`}
        style={{ color: cfg.color }}>
        <span className={`w-2 h-2 rounded-full animate-pulse ${cfg.dot}`} />
        {cfg.label}
      </div>
    </div>
  );
}

// ── Card container ────────────────────────────────────────────────────────────
function Card({ children, className = '' }) {
  return (
    <div className={`bg-slate-900/80 border border-slate-700/50 rounded-2xl backdrop-blur-sm ${className}`}>
      {children}
    </div>
  );
}

// ── Rând tabel tehnic ─────────────────────────────────────────────────────────
function TechRow({ label, value, accent = false }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-700/40 last:border-0">
      <span className="text-slate-400 text-xs">{label}</span>
      <span className={`text-xs font-semibold ${accent ? 'text-indigo-300' : 'text-slate-200'}`}>{value}</span>
    </div>
  );
}

// ── Input field ───────────────────────────────────────────────────────────────
function InputField({ label, id, value, onChange, placeholder, step = 'any' }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</label>
      <input
        id={id} type="number" step={step} value={value}
        onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full bg-slate-800/80 border border-slate-600/50 rounded-xl px-4 py-3
          text-slate-100 placeholder-slate-500 text-sm focus:outline-none
          focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all duration-200"
      />
    </div>
  );
}

// ── Skeleton loader ───────────────────────────────────────────────────────────
function SkeletonRow({ label }) {
  return (
    <div className="flex justify-between py-2.5 border-b border-slate-700/40 last:border-0">
      <span className="text-slate-500 text-xs">{label}</span>
      <div className="h-3 w-20 bg-slate-800 rounded animate-pulse" />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// App principal
// ─────────────────────────────────────────────────────────────────────────────
export default function App() {
  const [lat, setLat]         = useState('');
  const [lon, setLon]         = useState('');
  const [mw, setMw]           = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [result, setResult]   = useState(null);

  const handleMapClick = useCallback((clickLat, clickLon) => {
    setLat(String(clickLat));
    setLon(String(clickLon));
  }, []);

  const handleSubmit = async () => {
    setError('');
    setResult(null);
    if (!lat || !lon || !mw) {
      setError('Completează toate câmpurile înainte de a rula analiza.');
      return;
    }
    const pLat = parseFloat(lat), pLon = parseFloat(lon), pMw = parseFloat(mw);
    if (isNaN(pLat) || isNaN(pLon) || isNaN(pMw) || pMw <= 0) {
      setError('Valorile introduse nu sunt valide. Verifică coordonatele și puterea solicitată.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/evaluate-risk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat: pLat, lon: pLon, requested_mw: pMw }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Eroare server: ${res.status}`);
      }
      setResult(await res.json());
    } catch (err) {
      setError(`Conexiune eșuată: ${err.message}. Asigurați-vă că serverul backend rulează pe portul 8000.`);
    } finally {
      setLoading(false);
    }
  };

  const riskCfg = result ? getRiskConfig(result.risk_score) : null;

  // Split AI insight into paragraphs
  const aiParagraphs = result?.ai_insight
    ? result.ai_insight.split(/\n\n+/).filter(p => p.trim())
    : [];

  return (
    <div className="min-h-screen bg-[#0a0f1e] text-slate-100 flex flex-col">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="border-b border-slate-800/60 px-8 py-4 flex items-center justify-between
        bg-slate-950/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600
            flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Zap size={18} className="text-white" />
          </div>
          <div>
            <span className="text-lg font-bold text-slate-100 tracking-tight">GridScout</span>
            <span className="ml-2 text-xs text-indigo-400 font-medium bg-indigo-500/10
              border border-indigo-500/20 px-2 py-0.5 rounded-full">România · ANRE</span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <Radio size={11} className="text-emerald-400 animate-pulse" />
            Date reale ANRE Ordin 137/2021
          </span>
          <span className="flex items-center gap-1.5">
            <Brain size={11} className="text-violet-400" />
            GPT-4o-mini AI
          </span>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────────────────────── */}
      <main className="flex-1 flex gap-0 overflow-hidden" style={{ height: 'calc(100vh - 65px)' }}>

        {/* ════ STÂNGA 60% — Hartă + Formular ════════════════════════════════ */}
        <section className="flex flex-col gap-4 p-5" style={{ width: '60%' }}>

          {/* Formular */}
          <Card className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <MapPin size={16} className="text-indigo-400" />
              <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                Parametri Proiect
              </h2>
              <span className="text-xs text-slate-500 ml-auto">
                💡 Click pe hartă → auto-completare coordonate
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-4">
              <InputField label="Latitudine (°N)" id="lat" value={lat} onChange={setLat} placeholder="47.1585" />
              <InputField label="Longitudine (°E)" id="lon" value={lon} onChange={setLon} placeholder="27.6014" />
              <InputField label="Putere Dorită (MW)" id="mw" value={mw} onChange={setMw} placeholder="15.0" step="0.1" />
            </div>

            {error && (
              <div className="mb-4 flex items-start gap-2 text-sm text-red-300
                bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                <AlertTriangle size={15} className="mt-0.5 flex-shrink-0 text-red-400" />
                {error}
              </div>
            )}

            <button onClick={handleSubmit} disabled={loading}
              className="w-full flex items-center justify-center gap-2
                bg-gradient-to-r from-indigo-600 to-violet-600
                hover:from-indigo-500 hover:to-violet-500
                disabled:opacity-50 disabled:cursor-not-allowed
                text-white font-bold text-sm rounded-xl px-6 py-3
                transition-all duration-200 shadow-lg shadow-indigo-500/20 active:scale-[0.98]">
              {loading ? (
                <><Loader2 size={16} className="animate-spin" />Se generează analiza AI...</>
              ) : (
                <><Activity size={16} />Rulează Analiza<ChevronRight size={15} /></>
              )}
            </button>
          </Card>

          {/* Hartă */}
          <Card className="flex-1 overflow-hidden p-2">
            <MapComponent
              userLat={lat ? parseFloat(lat) : null}
              userLon={lon ? parseFloat(lon) : null}
              stationLat={result?.station_lat ?? null}
              stationLon={result?.station_lon ?? null}
              stationName={result?.closest_station ?? ''}
              onMapClick={handleMapClick}
            />
          </Card>
        </section>

        {/* ════ DREAPTA 40% — Intelligence Panel ════════════════════════════ */}
        <section className="flex flex-col gap-4 p-5 pl-0 overflow-y-auto" style={{ width: '40%' }}>

          {/* Scor Risc */}
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-5">
              <BarChart3 size={16} className="text-indigo-400" />
              <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                Scor de Risc Congestionare
              </h2>
            </div>
            {result ? (
              <>
                <RiskGauge score={result.risk_score} />

                {/* Progress bar zonă */}
                <div className="mt-5 pt-4 border-t border-slate-700/40">
                  <div className="flex justify-between text-xs text-slate-500 mb-2">
                    <span>Presiune rețea — Zona {result.zona_retea}</span>
                    <span style={{ color: riskCfg?.color }}>
                      {result.mw_zona_totala > 0
                        ? Math.round(((result.mw_zona_totala - result.mw_zona_ramasa) / result.mw_zona_totala) * 100)
                        : 0}% ocupat
                    </span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-1000"
                      style={{
                        width: result.mw_zona_totala > 0
                          ? `${Math.min(100, ((result.mw_zona_totala - result.mw_zona_ramasa) / result.mw_zona_totala) * 100)}%`
                          : '0%',
                        backgroundColor: riskCfg?.color,
                        boxShadow: `0 0 8px ${riskCfg?.color}80`,
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-slate-600 mt-1.5">
                    <span>0 MW</span>
                    <span>{result.mw_zona_totala} MW (cap. totală zonă)</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 gap-3">
                <div className="w-36 h-36 rounded-full border-4 border-dashed border-slate-700/50
                  flex items-center justify-center">
                  <BarChart3 size={36} className="text-slate-600" />
                </div>
                <p className="text-slate-500 text-sm text-center">
                  Completează formularul și rulează analiza<br />pentru a vedea scorul de risc.
                </p>
              </div>
            )}
          </Card>

          {/* AI Copilot */}
          <div className="ai-card-border">
            <div className="bg-slate-900 rounded-[calc(1rem-2px)] p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600
                  flex items-center justify-center">
                  <Brain size={14} className="text-white" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-200">AI Copilot Insight</h2>
                  <p className="text-xs text-violet-400">GPT-4o-mini · Analiză personalizată</p>
                </div>
              </div>

              {loading && (
                <div className="flex items-center gap-2 text-slate-400 text-sm">
                  <Loader2 size={14} className="animate-spin text-violet-400" />
                  Se generează raportul AI...
                </div>
              )}

              {result && !loading && (
                <div className="space-y-3">
                  {aiParagraphs.map((para, i) => (
                    <p key={i} className="text-slate-300 text-sm leading-relaxed">
                      {para}
                    </p>
                  ))}
                </div>
              )}

              {!result && !loading && (
                <p className="text-slate-500 text-sm leading-relaxed">
                  Raportul de analiză generat de GPT-4o-mini va apărea aici după rularea analizei —
                  evaluează capacitatea rețelei, zona ANRE și riscul tehnic pentru a oferi
                  o recomandare profesională adaptată proiectului tău.
                </p>
              )}
            </div>
          </div>

          {/* Detalii Tehnice */}
          <Card className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <Zap size={16} className="text-indigo-400" />
              <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                Detalii Tehnice
              </h2>
            </div>

            {result ? (
              <>
                <TechRow label="Stație de Racordare" value={result.closest_station} accent />
                <TechRow label="Județ Stație" value={result.judet_statie || '—'} />
                <TechRow label="Zonă Rețea ANRE" value={`Zona ${result.zona_retea}`} accent />
                <TechRow label="Distanță până la Stație" value={`${result.distance_km} km`} />
                <TechRow label="MW Aprobat la Stație (ANRE)" value={`${result.mw_aprobat_statie} MW`} />
                <TechRow label="Capacitate Reziduală Stație" value={`${result.capacity_left} MW`} />
                <TechRow label="Capacitate Totală Zonă" value={`${result.mw_zona_totala} MW`} />
                <TechRow label="Capacitate Rămasă Zonă" value={`${result.mw_zona_ramasa} MW`} accent />
                <TechRow label="Putere Solicitată" value={`${mw} MW`} />
                <TechRow label="Scor Final Risc" value={`${result.risk_score}%`} />
                <TechRow label="Coordonate Stație" value={`${result.station_lat}°N, ${result.station_lon}°E`} />
              </>
            ) : (
              ['Stație de Racordare', 'Zonă Rețea ANRE', 'Distanță', 'MW Aprobat (ANRE)',
               'Capacitate Reziduală', 'Capacitate Zonă', 'Scor Risc'].map(r => (
                <SkeletonRow key={r} label={r} />
              ))
            )}
          </Card>

          <p className="text-center text-xs text-slate-600 pb-2">
            GridScout v2.0 · Date ANRE Ordin 137/2021 + Formular ATR · AI: GPT-4o-mini
          </p>
        </section>
      </main>
    </div>
  );
}
