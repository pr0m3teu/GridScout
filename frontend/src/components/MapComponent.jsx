import { useEffect } from 'react';
import {
  MapContainer, TileLayer, Marker, Popup,
  Polyline, Circle, useMapEvents, useMap,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

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

const siteIcon    = colorIcon('blue');
const siteWarnIcon = colorIcon('orange');
const stationIcon = colorIcon('red');

const NATURA_2000_CENTER = [47.05, 27.63];
const NATURA_2000_RADIUS = 4000;
const DEFAULT_CENTER     = [47.1585, 27.6014];

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

export default function GridMap({
  userLat, userLon,
  stationLat, stationLon, stationName,
  envFlag, onMapClick,
}) {
  const connectionLine = userLat && userLon && stationLat && stationLon
    ? [[userLat, userLon], [stationLat, stationLon]]
    : null;

  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={9}
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
        userLat={userLat} userLon={userLon}
        stationLat={stationLat} stationLon={stationLon}
      />

      {envFlag && (
        <Circle
          center={NATURA_2000_CENTER}
          radius={NATURA_2000_RADIUS}
          pathOptions={{
            color: '#B91C1C',
            fillColor: '#FEE2E2',
            fillOpacity: 0.25,
            weight: 1.5,
            dashArray: '6 4',
          }}
        >
          <Popup>
            <div style={{ minWidth: 180, fontFamily: 'DM Sans, sans-serif' }}>
              <strong style={{ color: '#B91C1C', display: 'block', marginBottom: 4 }}>
                Protected Area — Natura 2000
              </strong>
              <span style={{ fontSize: 12, color: '#6B7280' }}>
                Bârnova Forest (ROSCI0256)<br />
                Buffer radius: 4 km
              </span>
            </div>
          </Popup>
        </Circle>
      )}

      {userLat && userLon && (
        <Marker position={[userLat, userLon]} icon={envFlag ? siteWarnIcon : siteIcon}>
          <Popup>
            <div style={{ fontFamily: 'DM Sans, sans-serif' }}>
              <strong style={{ display: 'block', marginBottom: 4 }}>Project Site</strong>
              <span style={{ fontSize: 12, color: '#6B7280' }}>
                {userLat}°N, {userLon}°E
              </span>
              {envFlag && (
                <span style={{ display: 'block', fontSize: 11, color: '#B91C1C', fontWeight: 600, marginTop: 4 }}>
                  Within Natura 2000 buffer
                </span>
              )}
            </div>
          </Popup>
        </Marker>
      )}

      {stationLat && stationLon && (
        <Marker position={[stationLat, stationLon]} icon={stationIcon}>
          <Popup>
            <div style={{ fontFamily: 'DM Sans, sans-serif' }}>
              <strong style={{ display: 'block', marginBottom: 4 }}>{stationName}</strong>
              <span style={{ fontSize: 12, color: '#6B7280' }}>Grid Interconnection Substation</span>
            </div>
          </Popup>
        </Marker>
      )}

      {connectionLine && (
        <Polyline
          positions={connectionLine}
          pathOptions={{ color: '#2563EB', weight: 2, dashArray: '8 5', opacity: 0.7 }}
        />
      )}
    </MapContainer>
  );
}