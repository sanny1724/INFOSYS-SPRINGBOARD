import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icon
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

const MapComponent = ({ activeThreats, userLocation }) => {
    // Default center (Kruger) if user location not yet found
    const center = userLocation || [-24.0, 31.5];

    return (
        <div style={{ height: '300px', width: '100%', borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.2)' }}>
            {/* Key forces re-render when center changes */}
            <MapContainer key={center.toString()} center={center} zoom={12} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />

                {/* User Location Marker */}
                {userLocation && (
                    <Marker position={userLocation}>
                        <Popup>📍 You are here</Popup>
                    </Marker>
                )}

                {/* Dynamic Threat Markers */}
                {activeThreats.map((threat, index) => (
                    <Marker key={index} position={threat.position}>
                        <Popup>
                            <strong>⚠️ THREAT DETECTED</strong><br />
                            Type: {threat.type}<br />
                            Confidence: {threat.confidence}
                        </Popup>
                    </Marker>
                ))}
            </MapContainer>
        </div>
    );
};

export default MapComponent;
