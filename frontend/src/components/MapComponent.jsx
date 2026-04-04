import { useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Circle,
  useMapEvents,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// ─── Fix Leaflet default icon paths broken by Vite bundling ────────────────
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl:
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl:
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// ─── Icoane colorate ────────────────────────────────────────────────────────
const makeColorIcon = (color) =>
  new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl:
      'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  });

const greenIcon  = makeColorIcon('green');
const redIcon    = makeColorIcon('red');
const orangeIcon = makeColorIcon('orange');

// ─── Coordonate Pădurea Bârnova (Natura 2000 ROSCI0256) ────────────────────
const BARNOVA_CENTER = [47.05, 27.63];
const BARNOVA_RADIUS = 4000; // metri

// ─── Handler click pe hartă ─────────────────────────────────────────────────
function MapClickHandler({ onMapClick }) {
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

// ─── Auto-pan când apare un rezultat ────────────────────────────────────────
function AutoPan({ userLat, userLon, stationLat, stationLon }) {
  const map = useMap();

  useEffect(() => {
    if (userLat && userLon && stationLat && stationLon) {
      const bounds = L.latLngBounds(
        [userLat, userLon],
        [stationLat, stationLon],
      );
      map.fitBounds(bounds, { padding: [60, 60] });
    } else if (userLat && userLon) {
      map.setView([userLat, userLon], 11);
    }
  }, [userLat, userLon, stationLat, stationLon, map]);

  return null;
}

// ─── Componentă principală ───────────────────────────────────────────────────
export default function MapComponent({
  userLat,
  userLon,
  stationLat,
  stationLon,
  stationName,
  env_flag,
  onMapClick,
}) {
  const IASI_CENTER = [47.1585, 27.6014];

  const polylinePositions =
    userLat && userLon && stationLat && stationLon
      ? [[userLat, userLon], [stationLat, stationLon]]
      : null;

  return (
    <MapContainer
      center={IASI_CENTER}
      zoom={9}
      style={{ height: '100%', width: '100%' }}
      className="rounded-xl"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <MapClickHandler onMapClick={onMapClick} />
      <AutoPan
        userLat={userLat}
        userLon={userLon}
        stationLat={stationLat}
        stationLon={stationLon}
      />

      {/* ── Zona protejată Natura 2000 — Pădurea Bârnova ─────────────────── */}
      {env_flag && (
        <Circle
          center={BARNOVA_CENTER}
          radius={BARNOVA_RADIUS}
          pathOptions={{
            color: '#ef4444',
            fillColor: '#ef4444',
            fillOpacity: 0.2,
            weight: 2,
            dashArray: '6, 4',
          }}
        >
          <Popup>
            <div style={{ minWidth: '180px' }}>
              <strong style={{ color: '#dc2626' }}>⚠️ Natura 2000</strong>
              <br />
              <span style={{ fontSize: '12px' }}>
                Pădurea Bârnova (ROSCI0256)
                <br />
                Rază de protecție: 4 km
              </span>
            </div>
          </Popup>
        </Circle>
      )}

      {/* ── Marker verde — locația utilizatorului ───────────────────────── */}
      {userLat && userLon && (
        <Marker
          position={[userLat, userLon]}
          icon={env_flag ? orangeIcon : greenIcon}
        >
          <Popup>
            <strong>{env_flag ? '⚠️ Locația ta' : '📍 Locația ta'}</strong>
            <br />
            {userLat}°N, {userLon}°E
            {env_flag && (
              <>
                <br />
                <span style={{ color: '#dc2626', fontSize: '11px', fontWeight: 600 }}>
                  În zona Natura 2000!
                </span>
              </>
            )}
          </Popup>
        </Marker>
      )}

      {/* ── Marker roșu — stația cea mai apropiată ──────────────────────── */}
      {stationLat && stationLon && (
        <Marker position={[stationLat, stationLon]} icon={redIcon}>
          <Popup>
            <strong>⚡ {stationName}</strong>
            <br />
            Stație de racordare
          </Popup>
        </Marker>
      )}

      {/* ── Linie de conectare ───────────────────────────────────────────── */}
      {polylinePositions && (
        <Polyline
          positions={polylinePositions}
          pathOptions={{
            color: '#6366f1',
            weight: 2.5,
            dashArray: '8, 6',
            opacity: 0.85,
          }}
        />
      )}
    </MapContainer>
  );
}
