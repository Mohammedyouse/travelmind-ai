import React, { useState } from 'react'

type MapPoint = {
    id: string
    name: string
    category: string
    rating?: number
    lat?: number
    lon?: number
    address?: string
    price_level?: string
    type: 'destination' | 'attraction' | 'hotel' | 'dining'
}

type InteractiveMapProps = {
    origin: string
    destination: string
    places: any[]
    hotels: any[]
    coordinates?: { latitude: number; longitude: number } | null
}

export function InteractiveMap({
    origin,
    destination,
    places,
    hotels,
    coordinates,
}: InteractiveMapProps) {
    const [selectedPoint, setSelectedPoint] = useState<MapPoint | null>(null)
    const [categoryFilter, setCategoryFilter] = useState<string>('all')

    // Collect map points
    const points: MapPoint[] = []

    // Calculate dynamic centroid from discovered places or coordinates
    const validCoords = places.filter(p => typeof p.lat === 'number' && typeof p.lon === 'number')
    const centerLat = coordinates?.latitude || (validCoords.length > 0 ? (validCoords.reduce((acc, p) => acc + p.lat, 0) / validCoords.length) : 28.6139)
    const centerLon = coordinates?.longitude || (validCoords.length > 0 ? (validCoords.reduce((acc, p) => acc + p.lon, 0) / validCoords.length) : 77.2090)

    // Center destination point
    points.push({
        id: 'dest-center',
        name: `${destination} City Center`,
        category: 'Urban Hub',
        type: 'destination',
        lat: centerLat,
        lon: centerLon,
        address: `${destination} Central District`,
    })

    // Add attractions
    places.forEach((p, idx) => {
        points.push({
            id: `place-${idx}`,
            name: p.name,
            category: p.category?.replace('_', ' ').toUpperCase() || 'ATTRACTION',
            rating: p.rating || 4.7,
            lat: typeof p.lat === 'number' ? p.lat : centerLat + ((idx % 5) * 0.015 - 0.03),
            lon: typeof p.lon === 'number' ? p.lon : centerLon + ((idx % 4) * 0.018 - 0.035),
            address: p.address || `${destination}`,
            price_level: p.price_level || '$$',
            type: p.category?.includes('market') || p.category?.includes('food') || p.category?.includes('culinary') ? 'dining' : 'attraction',
        })
    })

    // Add hotels
    hotels.forEach((h, idx) => {
        points.push({
            id: `hotel-${idx}`,
            name: h.name,
            category: h.tier || `${h.stars || 4}-Star Boutique Stay`,
            rating: h.rating || 4.8,
            lat: typeof h.latitude === 'number' ? h.latitude : centerLat - ((idx % 4) * 0.012 + 0.008),
            lon: typeof h.longitude === 'number' ? h.longitude : centerLon + ((idx % 3) * 0.014 + 0.005),
            address: `${h.neighborhood || 'City Center'}, ${destination}`,
            price_level: h.price_per_night ? `${h.currency === 'INR' ? '₹' : '$'}${h.price_per_night}/night` : 'Stay',
            type: 'hotel',
        })
    })

    const filteredPoints = categoryFilter === 'all'
        ? points
        : points.filter(p => p.type === categoryFilter || p.type === 'destination')

    return (
        <div className="interactive-map-card">
            <div className="map-toolbar">
                <div className="map-route-indicator">
                    <span className="route-pulse" />
                    <strong>Route: {origin} &rarr; {destination}</strong>
                </div>

                <div className="map-filters">
                    <button
                        className={`filter-btn ${categoryFilter === 'all' ? 'active' : ''}`}
                        onClick={() => setCategoryFilter('all')}
                    >
                        All ({points.length})
                    </button>
                    <button
                        className={`filter-btn ${categoryFilter === 'attraction' ? 'active' : ''}`}
                        onClick={() => setCategoryFilter('attraction')}
                    >
                        Landmarks ({points.filter(p => p.type === 'attraction').length})
                    </button>
                    <button
                        className={`filter-btn ${categoryFilter === 'hotel' ? 'active' : ''}`}
                        onClick={() => setCategoryFilter('hotel')}
                    >
                        Hotels ({points.filter(p => p.type === 'hotel').length})
                    </button>
                    <button
                        className={`filter-btn ${categoryFilter === 'dining' ? 'active' : ''}`}
                        onClick={() => setCategoryFilter('dining')}
                    >
                        Dining ({points.filter(p => p.type === 'dining').length})
                    </button>
                </div>
            </div>

            {/* SVG Visual Radar / Map Canvas */}
            <div className="svg-map-wrapper">
                <svg
                    viewBox="0 0 800 450"
                    className="vector-map-svg"
                    role="img"
                    aria-label={`Interactive map of ${destination}`}
                >
                    <defs>
                        <radialGradient id="mapGlow" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.15" />
                            <stop offset="100%" stopColor="#0f172a" stopOpacity="0" />
                        </radialGradient>
                        <linearGradient id="flightPath" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
                            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.8" />
                        </linearGradient>
                    </defs>

                    {/* Dark map canvas background */}
                    <rect width="800" height="450" fill="#090d16" rx="12" />
                    <circle cx="400" cy="225" r="300" fill="url(#mapGlow)" />

                    {/* Decorative grid lines */}
                    <line x1="100" y1="0" x2="100" y2="450" stroke="#1e293b" strokeDasharray="4,4" />
                    <line x1="300" y1="0" x2="300" y2="450" stroke="#1e293b" strokeDasharray="4,4" />
                    <line x1="500" y1="0" x2="500" y2="450" stroke="#1e293b" strokeDasharray="4,4" />
                    <line x1="700" y1="0" x2="700" y2="450" stroke="#1e293b" strokeDasharray="4,4" />
                    <line x1="0" y1="120" x2="800" y2="120" stroke="#1e293b" strokeDasharray="4,4" />
                    <line x1="0" y1="240" x2="800" y2="240" stroke="#1e293b" strokeDasharray="4,4" />
                    <line x1="0" y1="360" x2="800" y2="360" stroke="#1e293b" strokeDasharray="4,4" />

                    {/* Flight trajectory arc */}
                    <path
                        d="M 80 340 Q 240 100 420 220"
                        fill="none"
                        stroke="url(#flightPath)"
                        strokeWidth="2.5"
                        strokeDasharray="6,6"
                    />

                    {/* Origin node */}
                    <g transform="translate(80, 340)">
                        <circle r="9" fill="#38bdf8" opacity="0.3" />
                        <circle r="5" fill="#38bdf8" />
                        <text x="-12" y="24" fill="#94a3b8" fontSize="11" fontFamily="sans-serif">
                            {origin} (Origin)
                        </text>
                    </g>

                    {/* Destination cluster pins */}
                    {filteredPoints.map((pt, idx) => {
                        // Project lat/lon onto SVG coordinates relative to dynamic centroid
                        const ptLon = pt.lon ?? centerLon
                        const ptLat = pt.lat ?? centerLat
                        const offsetX = (ptLon - centerLon) * 2200
                        const offsetY = -(ptLat - centerLat) * 2200

                        const cx = Math.max(160, Math.min(740, 440 + offsetX + ((idx % 3) * 25 - 25)))
                        const cy = Math.max(60, Math.min(410, 225 + offsetY + ((idx % 4) * 20 - 30)))

                        const isSelected = selectedPoint?.id === pt.id
                        const pinColor = pt.type === 'hotel'
                            ? '#a855f7'
                            : pt.type === 'dining'
                            ? '#f59e0b'
                            : pt.type === 'destination'
                            ? '#10b981'
                            : '#38bdf8'

                        return (
                            <g
                                key={pt.id}
                                transform={`translate(${cx}, ${cy})`}
                                onClick={() => setSelectedPoint(pt)}
                                style={{ cursor: 'pointer' }}
                            >
                                <circle r={isSelected ? 16 : 10} fill={pinColor} opacity={0.25} />
                                <circle r={isSelected ? 8 : 6} fill={pinColor} />
                                <text
                                    x="10"
                                    y="4"
                                    fill={isSelected ? '#ffffff' : '#cbd5e1'}
                                    fontSize={isSelected ? '12' : '10'}
                                    fontWeight={isSelected ? 'bold' : 'normal'}
                                    fontFamily="sans-serif"
                                >
                                    {pt.name.length > 20 ? pt.name.substring(0, 18) + '...' : pt.name}
                                </text>
                            </g>
                        )
                    })}
                </svg>

                {/* Selected Point Detail Popup Overlay */}
                {selectedPoint && (
                    <div className="map-detail-popup">
                        <div className="popup-header">
                            <div>
                                <span className={`popup-type-tag type-${selectedPoint.type}`}>
                                    {selectedPoint.type.toUpperCase()}
                                </span>
                                <h4>{selectedPoint.name}</h4>
                            </div>
                            <button className="close-popup-btn" onClick={() => setSelectedPoint(null)}>
                                &times;
                            </button>
                        </div>
                        <p className="popup-category">{selectedPoint.category}</p>
                        <div className="popup-meta-row">
                            {selectedPoint.rating && <span>⭐ {selectedPoint.rating} / 5.0</span>}
                            {selectedPoint.price_level && <span>💰 {selectedPoint.price_level}</span>}
                        </div>
                        {selectedPoint.address && <p className="popup-address">📍 {selectedPoint.address}</p>}
                        {selectedPoint.lat && (
                            <small className="popup-coords">
                                Coordinates: {selectedPoint.lat.toFixed(4)}, {selectedPoint.lon?.toFixed(4)}
                            </small>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}
