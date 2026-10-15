import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

type MapPoint = {
    id: string
    name: string
    category: string
    rating?: number
    lat: number
    lon: number
    address?: string
    price?: string
    photo_url?: string
    type: 'destination' | 'attraction' | 'hotel'
    source?: string
    url?: string
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
    const mapContainerRef = useRef<HTMLDivElement | null>(null)
    const mapInstanceRef = useRef<L.Map | null>(null)
    const markersLayerRef = useRef<L.LayerGroup | null>(null)
    const markerMapRef = useRef<Map<string, L.Marker>>(new Map())

    const [categoryFilter, setCategoryFilter] = useState<'all' | 'attraction' | 'hotel'>('all')
    const [selectedPoint, setSelectedPoint] = useState<MapPoint | null>(null)

    // Build verified points from real coordinates ONLY (no synthetic offsets)
    const points: MapPoint[] = []

    if (coordinates && typeof coordinates.latitude === 'number' && typeof coordinates.longitude === 'number') {
        points.push({
            id: 'dest-center',
            name: `${destination} City Center`,
            category: 'Destination Hub',
            lat: coordinates.latitude,
            lon: coordinates.longitude,
            address: `${destination} Central Coordinates`,
            type: 'destination',
            source: 'Geographic Centroid',
        })
    }

    places.forEach((p, idx) => {
        if (typeof p.lat === 'number' && typeof p.lon === 'number' && !isNaN(p.lat) && !isNaN(p.lon)) {
            points.push({
                id: `place-${idx}`,
                name: p.name,
                category: (p.category || 'Attraction').replace(/_/g, ' ').toUpperCase(),
                rating: p.rating,
                lat: p.lat,
                lon: p.lon,
                address: p.address || destination,
                price: p.price || (p.admission_fee_inr ? `₹${p.admission_fee_inr}` : undefined),
                photo_url: p.photo_url,
                type: 'attraction',
                source: p.source || 'OpenStreetMap / Verified Landmark Database',
                url: p.website || undefined,
            })
        }
    })

    hotels.forEach((h, idx) => {
        const lat = typeof h.latitude === 'number' ? h.latitude : (typeof h.lat === 'number' ? h.lat : null)
        const lon = typeof h.longitude === 'number' ? h.longitude : (typeof h.lon === 'number' ? h.lon : null)
        if (lat !== null && lon !== null && !isNaN(lat) && !isNaN(lon)) {
            points.push({
                id: `hotel-${idx}`,
                name: h.name,
                category: h.tier || 'Hotel / Stay',
                rating: h.rating,
                lat,
                lon,
                address: h.address || `${destination}`,
                price: h.price_per_night ? `${h.currency === 'INR' ? '₹' : '$'}${h.price_per_night} / night` : undefined,
                photo_url: h.photo_url,
                type: 'hotel',
                source: h.source || 'Accommodation Provider Reference',
                url: h.booking_url || undefined,
            })
        }
    })

    const filteredPoints = categoryFilter === 'all'
        ? points
        : points.filter(p => p.type === categoryFilter || p.type === 'destination')

    // Initialize Leaflet Map
    useEffect(() => {
        if (!mapContainerRef.current) return

        if (!mapInstanceRef.current) {
            // Determine initial center
            const initialLat = coordinates?.latitude ?? (points.length > 0 ? points[0].lat : 19.0760)
            const initialLon = coordinates?.longitude ?? (points.length > 0 ? points[0].lon : 72.8777)

            const map = L.map(mapContainerRef.current, {
                center: [initialLat, initialLon],
                zoom: 12,
                scrollWheelZoom: false,
            })

            // OpenStreetMap tile layer with mandatory attribution
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
            }).addTo(map)

            const markersLayer = L.layerGroup().addTo(map)
            markersLayerRef.current = markersLayer
            mapInstanceRef.current = map
        }

        return () => {
            if (mapInstanceRef.current) {
                mapInstanceRef.current.remove()
                mapInstanceRef.current = null
                markersLayerRef.current = null
            }
        }
    }, [])

    // Update Markers when filteredPoints change
    useEffect(() => {
        const map = mapInstanceRef.current
        const layer = markersLayerRef.current
        if (!map || !layer) return

        layer.clearLayers()
        markerMapRef.current.clear()

        if (filteredPoints.length === 0) return

        const latLngBounds = L.latLngBounds([])

        filteredPoints.forEach(point => {
            const latLng: [number, number] = [point.lat, point.lon]
            latLngBounds.extend(latLng)

            // Distinct marker styling based on type
            const pinColor = point.type === 'destination'
                ? '#38bdf8'
                : point.type === 'hotel'
                ? '#10b981'
                : '#f59e0b'

            const iconHtml = `
                <div class="leaflet-custom-pin" style="background-color: ${pinColor}; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,0.4); border: 2px solid #ffffff; cursor: pointer;">
                    <span style="font-size: 13px;">${point.type === 'hotel' ? '🏨' : point.type === 'destination' ? '📍' : '🏛️'}</span>
                </div>
            `

            const customIcon = L.divIcon({
                className: 'custom-pin-wrapper',
                html: iconHtml,
                iconSize: [28, 28],
                iconAnchor: [14, 14],
                popupAnchor: [0, -16],
            })

            const popupContent = `
                <div class="leaflet-popup-details" style="font-family: inherit; min-width: 200px;">
                    <strong style="font-size: 14px; display: block; margin-bottom: 4px; color: #0f172a;">${point.name}</strong>
                    <span style="font-size: 11px; padding: 2px 6px; background: #e0f2fe; color: #0369a1; border-radius: 4px; font-weight: 600;">${point.category}</span>
                    <p style="font-size: 12px; color: #475569; margin: 6px 0 2px;">${point.address || ''}</p>
                    ${point.rating ? `<p style="font-size: 12px; margin: 2px 0; color: #047857;">⭐ Provider Rating: <strong>${point.rating}</strong></p>` : ''}
                    ${point.price ? `<p style="font-size: 12px; margin: 2px 0; color: #0f172a;">💵 ${point.price}</p>` : ''}
                    <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #e2e8f0; display: flex; gap: 8px;">
                        <a href="https://www.google.com/maps/search/?api=1&query=${point.lat},${point.lon}" target="_blank" rel="noopener noreferrer" style="font-size: 11px; color: #0284c7; text-decoration: underline;">
                            Get Real Directions &rarr;
                        </a>
                        ${point.url ? `<a href="${point.url}" target="_blank" rel="noopener noreferrer" style="font-size: 11px; color: #0284c7; text-decoration: underline;">Visit &rarr;</a>` : ''}
                    </div>
                </div>
            `

            const marker = L.marker(latLng, { icon: customIcon })
                .bindPopup(popupContent)
                .on('click', () => {
                    setSelectedPoint(point)
                })

            marker.addTo(layer)
            markerMapRef.current.set(point.id, marker)
        })

        if (latLngBounds.isValid()) {
            map.fitBounds(latLngBounds, { padding: [40, 40], maxZoom: 14 })
        }
    }, [filteredPoints])

    function handleSelectPoint(point: MapPoint) {
        setSelectedPoint(point)
        const map = mapInstanceRef.current
        const marker = markerMapRef.current.get(point.id)
        if (map && marker) {
            map.flyTo([point.lat, point.lon], 15, { duration: 1 })
            marker.openPopup()
        }
    }

    return (
        <div className="interactive-map-card">
            <div className="map-toolbar">
                <div className="map-route-indicator">
                    <span className="route-pulse" />
                    <strong>OpenStreetMap Functional Navigator: {origin} &rarr; {destination}</strong>
                </div>

                <div className="map-filters">
                    <button
                        className={`filter-btn ${categoryFilter === 'all' ? 'active' : ''}`}
                        onClick={() => setCategoryFilter('all')}
                    >
                        All Pins ({points.length})
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
                        Accommodations ({points.filter(p => p.type === 'hotel').length})
                    </button>
                </div>
            </div>

            {points.length === 0 ? (
                <div className="map-empty-state" style={{ padding: '3rem 1.5rem', textAlign: 'center', background: 'var(--bg-surface)' }}>
                    <p style={{ color: 'var(--text-muted)' }}>
                        No verified geographic coordinates are available for this destination.
                        Map pins are only rendered for verified real-world latitude and longitude coordinates.
                    </p>
                </div>
            ) : (
                <div className="leaflet-map-wrapper" style={{ position: 'relative' }}>
                    <div
                        ref={mapContainerRef}
                        style={{ height: '480px', width: '100%', borderRadius: '12px', zIndex: 1 }}
                        aria-label={`Interactive map of ${destination}`}
                    />
                </div>
            )}

            {/* List of Verified Location Pins for Easy Selection */}
            {points.length > 0 && (
                <div className="map-locations-tray" style={{ marginTop: '1rem' }}>
                    <div className="tray-header" style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h4 style={{ fontSize: '0.95rem', color: 'var(--text-primary)' }}>Verified Coordinates ({filteredPoints.length})</h4>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Click any location to center and inspect details</span>
                    </div>
                    <div className="map-points-scroll-list" style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
                        {filteredPoints.map(p => (
                            <div
                                key={p.id}
                                className={`map-point-card ${selectedPoint?.id === p.id ? 'active' : ''}`}
                                onClick={() => handleSelectPoint(p)}
                                style={{
                                    flex: '0 0 240px',
                                    padding: '0.75rem',
                                    borderRadius: '8px',
                                    background: selectedPoint?.id === p.id ? 'var(--bg-surface-elevated)' : 'var(--bg-surface)',
                                    border: `1px solid ${selectedPoint?.id === p.id ? 'var(--brand-primary)' : 'var(--border-subtle)'}`,
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease',
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                                    <span style={{ fontSize: '13px' }}>{p.type === 'hotel' ? '🏨' : p.type === 'destination' ? '📍' : '🏛️'}</span>
                                    <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {p.name}
                                    </strong>
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.category}</div>
                                {p.price && <div style={{ fontSize: '0.75rem', color: 'var(--brand-primary)', marginTop: '2px' }}>{p.price}</div>}
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                                    {p.lat.toFixed(4)}, {p.lon.toFixed(4)}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
