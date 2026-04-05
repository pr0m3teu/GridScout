import { useEffect, useMemo } from 'react';
import {
  MapContainer, TileLayer, Marker, Popup,
  Polyline, Circle, useMapEvents, useMap,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet's missing default icon paths when bundled with Vite/Webpack
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl:       'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl:     'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const colorIcon = (color) =>
  new L.Icon({
    iconUrl:   `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    iconSize:    [25, 41],
    iconAnchor:  [12, 41],
    popupAnchor: [1, -34],
    shadowSize:  [41, 41],
  });

const siteIcon      = colorIcon('blue');
const siteWarnIcon  = colorIcon('orange');
const stationIcon   = colorIcon('red');

// Geographic center of Romania — used as the default map view
// before the user selects a site. No region-specific hardcoding.
const ROMANIA_CENTER = [45.9432, 24.9668];
const ROMANIA_ZOOM   = 7;

// ── Protection type labels ─────────────────────────────────────────────────
const PROTECTION_LABELS = {
  national_park:   'Parc Național',
  nature_reserve:  'Rezervație Naturală',
  protected_area:  'Zonă Protejată',
};

function protectionLabel(type) {
  return PROTECTION_LABELS[type] || 'Zonă Protejată';
}

// ── Route line style — changes color when constraints are detected ──────────
function routeStyle(envFlag, infraCount) {
  if (envFlag)       return { color: '#B91C1C', weight: 2.5, dashArray: '8 5', opacity: 0.85 };
  if (infraCount > 0) return { color: '#D97706', weight: 2,   dashArray: '8 5', opacity: 0.8  };
  return               { color: '#2563EB', weight: 2,   dashArray: '8 5', opacity: 0.7  };
}

// ── Map click handler ──────────────────────────────────────────────────────
function ClickHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      onMapClick(
        parseFloat(e.latlng.lat.toFixed(6)),
        parseFloat(e.latlng.lng.toFixed(6)),
      );
    },
  });
  return null;
}

// ── Auto-fit bounds when site or station changes ───────────────────────────
function BoundsFitter({ userLat, userLon, stationLat, stationLon }) {
  const map = useMap();

  useEffect(() => {
    if (userLat && userLon && stationLat && stationLon) {
      map.fitBounds(
        L.latLngBounds([userLat, userLon], [stationLat, stationLon]),
        { padding: [60, 60] },
      );
    } else if (userLat && userLon) {
      map.setView([userLat, userLon], 11);
    }
  }, [userLat, userLon, stationLat, stationLon, map]);

  return null;
}

// ── Main component ─────────────────────────────────────────────────────────
/**
 * Props
 * ─────
 * userLat / userLon          — project site coordinates (WGS84)
 * stationLat / stationLon    — nearest substation coordinates
 * stationName                — substation display name
 * envFlag                    — true when ≥1 protected area is crossed
 * violations                 — full violation array from the API:
 *                              [{ category, name, penalty, detail }]
 *                              Protected area entries carry:
 *                                detail.centroid_lat / centroid_lon
 *                                detail.display_radius_m
 *                                detail.protection_type / iucn_level
 * onMapClick                 — callback(lat, lon) when the map is clicked
 */
export default function GridMap({
  userLat, userLon,
  stationLat, stationLon, stationName,
  envFlag,
  violations = [],
  onMapClick,
}) {
  const connectionLine = userLat && userLon && stationLat && stationLon
    ? [[userLat, userLon], [stationLat, stationLon]]
    : null;

  // Separate protected-area violations (have centroid data) from infra crossings
  const protectedViolations = useMemo(
    () => violations.filter(
      v => v.category === 'protected_area'
        && v.detail?.centroid_lat != null
        && v.detail?.centroid_lon != null,
    ),
    [violations],
  );

  const infraCount = useMemo(
    () => violations.filter(v => v.category !== 'protected_area').length,
    [violations],
  );

  const linePath = routeStyle(envFlag, infraCount);

  return (
    <MapContainer
      center={ROMANIA_CENTER}
      zoom={ROMANIA_ZOOM}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer
        attribution='&copy; <a href="https://carto.com/">CartoDB</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
        maxZoom={20}
      />

      <ClickHandler onMapClick={onMapClick} />
      <BoundsFitter
        userLat={userLat}   userLon={userLon}
        stationLat={stationLat} stationLon={stationLon}
      />

      {/* ── Dynamic protected area overlays ───────────────────────────────
          Rendered from real API data — centroid + estimated radius returned
          by the backend ScoringEngine for every intersecting protected area.
          No geographic coordinates are hardcoded here.
      ─────────────────────────────────────────────────────────────────── */}
      {protectedViolations.map((v, i) => {
        const {
          centroid_lat,
          centroid_lon,
          display_radius_m = 4000,
          protection_type  = 'protected_area',
          iucn_level,
        } = v.detail;

        const isNationalPark = protection_type === 'national_park';

        return (
          <Circle
            key={`protected-${v.name}-${i}`}
            center={[centroid_lat, centroid_lon]}
            radius={display_radius_m}
            pathOptions={{
              color:       isNationalPark ? '#7C2D12' : '#B91C1C',
              fillColor:   isNationalPark ? '#FED7AA' : '#FEE2E2',
              fillOpacity: 0.28,
              weight:      isNationalPark ? 2 : 1.5,
              dashArray:   '6 4',
            }}
          >
            <Popup>
              <div style={{ minWidth: 200, fontFamily: 'DM Sans, sans-serif' }}>
                <strong style={{ color: isNationalPark ? '#7C2D12' : '#B91C1C', display: 'block', marginBottom: 4 }}>
                  {v.name}
                </strong>
                <span style={{ fontSize: 12, color: '#6B7280', display: 'block' }}>
                  {protectionLabel(protection_type)}
                  {iucn_level && iucn_level !== 'unknown' ? ` · IUCN Categoria ${iucn_level}` : ''}
                </span>
                <span style={{ fontSize: 11, color: '#B91C1C', display: 'block', marginTop: 6, fontWeight: 600 }}>
                  Penalizare traseu: −{v.penalty} pct
                </span>
                <span style={{ fontSize: 11, color: '#6B7280', display: 'block', marginTop: 2 }}>
                  Sursă: OpenStreetMap / Natura 2000
                </span>
              </div>
            </Popup>
          </Circle>
        );
      })}

      {/* ── Project site marker ────────────────────────────────────────── */}
      {userLat && userLon && (
        <Marker
          position={[userLat, userLon]}
          icon={envFlag ? siteWarnIcon : siteIcon}
        >
          <Popup>
            <div style={{ fontFamily: 'DM Sans, sans-serif' }}>
              <strong style={{ display: 'block', marginBottom: 4 }}>
                Amplasament Proiect
              </strong>
              <span style={{ fontSize: 12, color: '#6B7280' }}>
                {userLat}°N, {userLon}°E
              </span>
              {envFlag && (
                <span style={{
                  display: 'block', fontSize: 11,
                  color: '#B91C1C', fontWeight: 600, marginTop: 4,
                }}>
                  ⚠ Traseul intersectează zone protejate
                </span>
              )}
              {!envFlag && infraCount > 0 && (
                <span style={{
                  display: 'block', fontSize: 11,
                  color: '#D97706', fontWeight: 600, marginTop: 4,
                }}>
                  ⚠ {infraCount} traversare infrastructură
                </span>
              )}
            </div>
          </Popup>
        </Marker>
      )}

      {/* ── Substation marker ──────────────────────────────────────────── */}
      {stationLat && stationLon && (
        <Marker position={[stationLat, stationLon]} icon={stationIcon}>
          <Popup>
            <div style={{ fontFamily: 'DM Sans, sans-serif' }}>
              <strong style={{ display: 'block', marginBottom: 4 }}>
                {stationName}
              </strong>
              <span style={{ fontSize: 12, color: '#6B7280' }}>
                Stație de interconectare la rețea
              </span>
            </div>
          </Popup>
        </Marker>
      )}

      {/* ── Proposed connection route ──────────────────────────────────── */}
      {connectionLine && (
        <Polyline
          positions={connectionLine}
          pathOptions={linePath}
        />
      )}

      {/* ── Map legend (shown only after analysis) ─────────────────────── */}
      {(protectedViolations.length > 0 || infraCount > 0 || connectionLine) && (
        <div
          style={{
            position: 'absolute', bottom: 24, left: 12, zIndex: 1000,
            background: 'rgba(255,255,255,0.94)',
            border: '1px solid #E4E7EC',
            borderRadius: 8,
            padding: '8px 12px',
            fontSize: 11,
            fontFamily: 'DM Sans, sans-serif',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            lineHeight: 1.8,
            backdropFilter: 'blur(4px)',
          }}
        >
          {connectionLine && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                width: 24, height: 2,
                background: linePath.color,
                borderRadius: 2,
                flexShrink: 0,
              }} />
              <span style={{ color: '#374151' }}>Traseu propus</span>
            </div>
          )}
          {protectedViolations.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                width: 12, height: 12,
                borderRadius: '50%',
                background: '#FEE2E2',
                border: '1.5px dashed #B91C1C',
                flexShrink: 0,
              }} />
              <span style={{ color: '#374151' }}>
                Zonă protejată ({protectedViolations.length})
              </span>
            </div>
          )}
          {infraCount > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                width: 12, height: 2,
                background: '#D97706',
                borderRadius: 2,
                flexShrink: 0,
              }} />
              <span style={{ color: '#374151' }}>
                Infrastructură ({infraCount} traversări)
              </span>
            </div>
          )}
        </div>
      )}
    </MapContainer>
  );
}
