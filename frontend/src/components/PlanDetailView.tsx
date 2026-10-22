import React, { useState } from 'react'
import type { TripRecord, TripInput } from '../services/api'
import { InteractiveMap } from './InteractiveMap'

function formatMoney(amount: number | string | undefined | null, currency: string = 'USD'): string {
    if (amount === undefined || amount === null || amount === '') return ''
    const num = typeof amount === 'number' ? amount : parseFloat(String(amount))
    if (isNaN(num)) return `${amount} ${currency}`
    const curr = (currency || 'USD').toUpperCase()
    const sym = curr === 'INR' ? '₹' : curr === 'EUR' ? '€' : curr === 'GBP' ? '£' : curr === 'JPY' ? '¥' : '$'
    return `${sym}${num.toLocaleString(undefined, { minimumFractionDigits: num % 1 === 0 ? 0 : 2, maximumFractionDigits: 2 })}`
}

type PlanDetailViewProps = {
    trip: TripRecord
    onUpdateTrip: (id: string, updates: Partial<TripInput>) => Promise<void>
    onDeleteTrip: (id: string) => Promise<void>
    onExportHtml: (id: string) => void
    onClose: () => void
    isUpdating: boolean
}

export function PlanDetailView({
    trip,
    onUpdateTrip,
    onDeleteTrip,
    onExportHtml,
    onClose,
    isUpdating,
}: PlanDetailViewProps) {
    const [activeSection, setActiveSection] = useState<string>('itinerary')
    const [showEditModal, setShowEditModal] = useState<boolean>(false)

    // Edit form state
    const [editOrigin, setEditOrigin] = useState(trip.origin)
    const [editDestination, setEditDestination] = useState(trip.destination)
    const [editDeparture, setEditDeparture] = useState(trip.departure_date || '')
    const [editReturn, setEditReturn] = useState(trip.return_date || '')
    const [editTravelers, setEditTravelers] = useState(String(trip.travelers))
    const [editBudget, setEditBudget] = useState(String(trip.budget || 2000))
    const [editCurrency, setEditCurrency] = useState(trip.currency)
    const [editDateError, setEditDateError] = useState<string | null>(null)

    // Flight Discovery Controls
    const [flightSearchQuery, setFlightSearchQuery] = useState('')
    const [flightStopsFilter, setFlightStopsFilter] = useState('all') // 'all', '0', '1', '2+'
    const [flightSortBy, setFlightSortBy] = useState('price_asc') // 'price_asc', 'price_desc', 'stops'
    const [flightVisibleCount, setFlightVisibleCount] = useState(6)

    // Hotel Discovery Controls
    const [hotelSearchQuery, setHotelSearchQuery] = useState('')
    const [hotelTierFilter, setHotelTierFilter] = useState('all') // 'all', 'hostel', 'guesthouse', 'mid_range', 'boutique', 'luxury'
    const [hotelSortBy, setHotelSortBy] = useState('recommended') // 'recommended', 'price_asc', 'price_desc', 'rating_desc'
    const [hotelVisibleCount, setHotelVisibleCount] = useState(6)

    // Attraction Discovery Controls
    const [placeSearchQuery, setPlaceSearchQuery] = useState('')
    const [placeCategoryFilter, setPlaceCategoryFilter] = useState('all') // 'all', 'temple', 'ghat', 'heritage', 'bazaar', 'park', 'museum'
    const [placeSortBy, setPlaceSortBy] = useState('recommended') // 'recommended', 'distance_asc', 'name_asc', 'rating_desc'
    const [placeVisibleCount, setPlaceVisibleCount] = useState(8)

    // Dynamically compute today's date in user's local timezone (YYYY-MM-DD)
    const todayStr = React.useMemo(() => {
        const d = new Date()
        const year = d.getFullYear()
        const month = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
    }, [])

    const results = trip.plan_results || {}
    const itinerary = results.itinerary
    const days = itinerary?.days || []

    const flightData = results.flight_intelligence?.data || {}
    const flightOffers = flightData.offers || []

    const hotelData = results.accommodation_intelligence?.data || {}
    const hotels = hotelData.hotels || []

    const destData = results.destination_discovery?.data || {}
    const places = destData.places || []
    const coordinates = destData.coordinates

    const budgetData = results.budget_intelligence?.data || {}
    const budgetItems = (budgetData.items || {}) as Record<string, string>

    const supportData = results.travel_support?.data || {}
    const supportInfo = supportData.support || {}
    const weatherForecast = supportInfo.weather_forecast || []
    const currentWeather = supportInfo.current_weather
    const packingChecklist = supportInfo.checklist || []

    const googleFlightsDirectUrl = flightData.direct_search_url || `https://www.google.com/travel/flights?q=flights+from+${encodeURIComponent(trip.origin)}+to+${encodeURIComponent(trip.destination)}${trip.departure_date ? `+on+${trip.departure_date}` : ''}`

    // Filtered & Sorted Flights
    const filteredFlights = React.useMemo(() => {
        let list = [...flightOffers]
        if (flightSearchQuery.trim()) {
            const q = flightSearchQuery.toLowerCase().trim()
            list = list.filter((o: any) => {
                const carriers = (o.carrier_names || o.carriers || []).join(' ').toLowerCase()
                const fNum = String(o.flight_number || '').toLowerCase()
                const depCity = String(o.departure?.city || o.departure_city || '').toLowerCase()
                const arrCity = String(o.arrival?.city || o.arrival_city || '').toLowerCase()
                return carriers.includes(q) || fNum.includes(q) || depCity.includes(q) || arrCity.includes(q)
            })
        }
        if (flightStopsFilter !== 'all') {
            if (flightStopsFilter === '0') list = list.filter((o: any) => o.stops === 0)
            else if (flightStopsFilter === '1') list = list.filter((o: any) => o.stops === 1)
            else if (flightStopsFilter === '2+') list = list.filter((o: any) => (o.stops || 0) >= 2)
        }
        if (flightSortBy === 'price_asc') {
            list.sort((a: any, b: any) => (parseFloat(a.price) || 0) - (parseFloat(b.price) || 0))
        } else if (flightSortBy === 'price_desc') {
            list.sort((a: any, b: any) => (parseFloat(b.price) || 0) - (parseFloat(a.price) || 0))
        } else if (flightSortBy === 'stops') {
            list.sort((a: any, b: any) => (a.stops || 0) - (b.stops || 0))
        }
        return list
    }, [flightOffers, flightSearchQuery, flightStopsFilter, flightSortBy])

    const displayedFlights = filteredFlights.slice(0, flightVisibleCount)

    // Filtered & Sorted Hotels
    const filteredHotels = React.useMemo(() => {
        let list = [...hotels]
        if (hotelSearchQuery.trim()) {
            const q = hotelSearchQuery.toLowerCase().trim()
            list = list.filter((h: any) => {
                const name = String(h.name || '').toLowerCase()
                const nh = String(h.neighborhood || h.address || '').toLowerCase()
                const tier = String(h.tier || '').toLowerCase()
                const amenities = (h.amenities || []).join(' ').toLowerCase()
                return name.includes(q) || nh.includes(q) || tier.includes(q) || amenities.includes(q)
            })
        }
        if (hotelTierFilter !== 'all') {
            list = list.filter((h: any) => {
                const t = (h.tier || '').toLowerCase()
                const n = (h.name || '').toLowerCase()
                if (hotelTierFilter === 'hostel') return t.includes('hostel') || t.includes('budget') || n.includes('hostel')
                if (hotelTierFilter === 'guesthouse') return t.includes('guesthouse') || t.includes('homestay') || n.includes('guesthouse') || n.includes('homestay') || n.includes('guest house')
                if (hotelTierFilter === 'mid_range') return t.includes('mid-range') || t.includes('3-star') || t.includes('standard')
                if (hotelTierFilter === 'boutique') return t.includes('boutique') || t.includes('4-star')
                if (hotelTierFilter === 'luxury') return t.includes('luxury') || t.includes('5-star') || t.includes('heritage') || t.includes('palace') || t.includes('resort')
                return true
            })
        }
        if (hotelSortBy === 'price_asc') {
            list.sort((a: any, b: any) => (parseFloat(a.price_per_night) || 0) - (parseFloat(b.price_per_night) || 0))
        } else if (hotelSortBy === 'price_desc') {
            list.sort((a: any, b: any) => (parseFloat(b.price_per_night) || 0) - (parseFloat(a.price_per_night) || 0))
        } else if (hotelSortBy === 'rating_desc') {
            list.sort((a: any, b: any) => (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0))
        }
        return list
    }, [hotels, hotelSearchQuery, hotelTierFilter, hotelSortBy])

    const displayedHotels = filteredHotels.slice(0, hotelVisibleCount)

    // Filtered & Sorted Places
    const filteredPlaces = React.useMemo(() => {
        let list = [...places]
        if (placeSearchQuery.trim()) {
            const q = placeSearchQuery.toLowerCase().trim()
            list = list.filter((p: any) => {
                const name = String(p.name || '').toLowerCase()
                const desc = String(p.description || '').toLowerCase()
                const cat = String(p.category || '').toLowerCase()
                const addr = String(p.address || '').toLowerCase()
                return name.includes(q) || desc.includes(q) || cat.includes(q) || addr.includes(q)
            })
        }
        if (placeCategoryFilter !== 'all') {
            list = list.filter((p: any) => {
                const cat = (p.category || '').toLowerCase()
                const name = (p.name || '').toLowerCase()
                if (placeCategoryFilter === 'temple') return cat.includes('temple') || cat.includes('spiritual') || cat.includes('worship') || name.includes('temple') || name.includes('mandir')
                if (placeCategoryFilter === 'ghat') return cat.includes('ghat') || cat.includes('waterfront') || name.includes('ghat')
                if (placeCategoryFilter === 'heritage') return cat.includes('historic') || cat.includes('heritage') || cat.includes('monument') || cat.includes('ruins') || cat.includes('archaeological') || cat.includes('fort')
                if (placeCategoryFilter === 'bazaar') return cat.includes('bazaar') || cat.includes('market') || cat.includes('shopping') || name.includes('bazaar') || name.includes('market')
                if (placeCategoryFilter === 'park') return cat.includes('park') || cat.includes('nature') || cat.includes('garden')
                if (placeCategoryFilter === 'museum') return cat.includes('museum') || cat.includes('gallery') || name.includes('museum')
                return true
            })
        }
        if (placeSortBy === 'distance_asc') {
            list.sort((a: any, b: any) => (parseFloat(a.distance_km) || 999) - (parseFloat(b.distance_km) || 999))
        } else if (placeSortBy === 'name_asc') {
            list.sort((a: any, b: any) => String(a.name || '').localeCompare(String(b.name || '')))
        } else if (placeSortBy === 'rating_desc') {
            list.sort((a: any, b: any) => (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0))
        }
        return list
    }, [places, placeSearchQuery, placeCategoryFilter, placeSortBy])

    const displayedPlaces = filteredPlaces.slice(0, placeVisibleCount)

    const agentExecutions = (results.agent_execution || {}) as Record<string, { status: string; attempts: number; duration_ms: number; error: string }>

    function handleEditDepartureChange(val: string) {
        setEditDeparture(val)
        if (val < todayStr) {
            setEditDateError(`Departure date cannot be in the past (${todayStr}).`)
            return
        }
        if (editReturn && val > editReturn) {
            setEditDateError(`Departure date (${val}) is after return date (${editReturn}).`)
            return
        }
        setEditDateError(null)
    }

    function handleEditReturnChange(val: string) {
        setEditReturn(val)
        if (editDeparture && val < editDeparture) {
            setEditDateError(`Return date (${val}) cannot be before departure date (${editDeparture}).`)
            return
        }
        setEditDateError(null)
    }

    async function handleSaveEdit(e: React.FormEvent) {
        e.preventDefault()
        if (editOrigin.trim().toLowerCase() === editDestination.trim().toLowerCase()) {
            setEditDateError(`Destination cannot be the same as origin.`)
            return
        }
        if (editDeparture < todayStr) {
            setEditDateError(`Departure date cannot be in the past (${todayStr}).`)
            return
        }
        if (editReturn && editReturn < editDeparture) {
            setEditDateError(`Return date cannot be before departure date.`)
            return
        }
        setEditDateError(null)
        await onUpdateTrip(trip.id, {
            origin: editOrigin.trim().toUpperCase(),
            destination: editDestination.trim().toUpperCase(),
            departure_date: editDeparture,
            return_date: editReturn || undefined,
            travelers: Number(editTravelers) || 1,
            budget: Number(editBudget) || 2000,
            currency: editCurrency,
            client_date: todayStr,
        })
        setShowEditModal(false)
    }

    return (
        <div className="plan-detail-container">
            {/* Top Bar Navigation */}
            <div className="plan-top-bar">
                <button className="back-link-btn" onClick={onClose}>
                    &larr; Back to Trips
                </button>
                <div className="plan-actions-group">
                    <button className="button button-outline-sm" onClick={() => onExportHtml(trip.id)}>
                        📥 Export HTML / Print
                    </button>
                    <button className="button button-primary-sm" onClick={() => setShowEditModal(true)}>
                        ✏️ Modify & Re-Plan
                    </button>
                    <button className="button button-danger-sm" onClick={() => onDeleteTrip(trip.id)}>
                        🗑️ Delete
                    </button>
                </div>
            </div>

            {/* Trip Header Banner */}
            <div className="plan-header-banner">
                <div className="banner-details">
                    <span className="section-kicker">Saved Itinerary · {trip.status.toUpperCase()}</span>
                    <h1>{trip.origin} <span className="route-arrow">&rarr;</span> {trip.destination}</h1>
                    <p className="banner-dates">
                        📅 {trip.departure_date || 'Flexible Dates'} {trip.return_date ? `to ${trip.return_date}` : ''}
                        &nbsp;·&nbsp; 👥 {trip.travelers} Traveler{trip.travelers > 1 ? 's' : ''}
                        &nbsp;·&nbsp; 💰 Ceiling: {trip.budget ? formatMoney(trip.budget, trip.currency) : 'Flexible'}
                    </p>
                    {trip.summary && <p className="banner-summary-text">{trip.summary}</p>}
                </div>
                <div className="banner-meta-badge">
                    <small>SOURCE</small>
                    <strong>{itinerary?.source || 'multi_agent_dag'}</strong>
                </div>
            </div>

            {/* Navigation Tabs */}
            <div className="plan-tabs-bar" role="tablist">
                <button
                    className={`plan-tab-btn ${activeSection === 'itinerary' ? 'active' : ''}`}
                    onClick={() => setActiveSection('itinerary')}
                >
                    🗓️ Daily Schedule ({days.length} Days)
                </button>
                <button
                    className={`plan-tab-btn ${activeSection === 'flights' ? 'active' : ''}`}
                    onClick={() => setActiveSection('flights')}
                >
                    ✈️ Flights ({flightOffers.length})
                </button>
                <button
                    className={`plan-tab-btn ${activeSection === 'hotels' ? 'active' : ''}`}
                    onClick={() => setActiveSection('hotels')}
                >
                    🏨 Hotels & Stays ({hotels.length})
                </button>
                <button
                    className={`plan-tab-btn ${activeSection === 'destinations' ? 'active' : ''}`}
                    onClick={() => setActiveSection('destinations')}
                >
                    📍 Attractions ({places.length})
                </button>
                <button
                    className={`plan-tab-btn ${activeSection === 'map' ? 'active' : ''}`}
                    onClick={() => setActiveSection('map')}
                >
                    🗺️ Interactive Map
                </button>
                <button
                    className={`plan-tab-btn ${activeSection === 'budget' ? 'active' : ''}`}
                    onClick={() => setActiveSection('budget')}
                >
                    💵 Cost Breakdown
                </button>
                <button
                    className={`plan-tab-btn ${activeSection === 'support' ? 'active' : ''}`}
                    onClick={() => setActiveSection('support')}
                >
                    🌤️ Weather & Checklist
                </button>
                <button
                    className={`plan-tab-btn ${activeSection === 'agents' ? 'active' : ''}`}
                    onClick={() => setActiveSection('agents')}
                >
                    🤖 Agent Pipeline
                </button>
            </div>

            {/* TAB 1: Daily Schedule */}
            {activeSection === 'itinerary' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Personalized Daily Itinerary</h2>
                        <span className="estimate-tag">{itinerary?.source || 'Deterministic Agent Model'}</span>
                    </div>

                    {days.length === 0 ? (
                        <p className="empty-copy">No daily schedule generated yet. Click 'Modify & Re-Plan' to calculate schedule.</p>
                    ) : (
                        <div className="itinerary-days-container">
                            {days.map((dayItem: any) => (
                                <div key={dayItem.day} className="day-schedule-card">
                                    <div className="day-header-strip">
                                        <span className="day-badge">DAY {String(dayItem.day).padStart(2, '0')}</span>
                                        <h3 className="day-title-text">{dayItem.title || `Day ${dayItem.day}`}</h3>
                                    </div>

                                    {/* Detailed time slots if available */}
                                    <div className="slots-grid">
                                        <div className="slot-box morning-slot">
                                            <span className="slot-icon">🌅 MORNING</span>
                                            <h4>{dayItem.morning?.activity || dayItem.activities?.[0] || 'Morning Activity'}</h4>
                                            {dayItem.morning?.time && <small>🕒 {dayItem.morning.time}</small>}
                                            {dayItem.morning?.cost && <div className="slot-cost">💵 Est: {dayItem.morning.cost}</div>}
                                        </div>
                                        <div className="slot-box afternoon-slot">
                                            <span className="slot-icon">☀️ AFTERNOON</span>
                                            <h4>{dayItem.afternoon?.activity || dayItem.activities?.[1] || 'Afternoon Activity'}</h4>
                                            {dayItem.afternoon?.time && <small>🕒 {dayItem.afternoon.time}</small>}
                                            {dayItem.afternoon?.cost && <div className="slot-cost">💵 Est: {dayItem.afternoon.cost}</div>}
                                        </div>
                                        <div className="slot-box evening-slot">
                                            <span className="slot-icon">🌙 EVENING</span>
                                            <h4>{dayItem.evening?.activity || dayItem.activities?.[2] || 'Evening Dinner & Stroll'}</h4>
                                            {dayItem.evening?.time && <small>🕒 {dayItem.evening.time}</small>}
                                            {dayItem.evening?.cost && <div className="slot-cost">💵 Est: {dayItem.evening.cost}</div>}
                                        </div>
                                    </div>

                                    {/* Regional Dining & Transit Highlights */}
                                    {(dayItem.dining_recommendation || dayItem.transit_tip) && (
                                        <div className="itinerary-tips-box">
                                            {dayItem.dining_recommendation && (
                                                <div className="itinerary-tip-card dining-tip">
                                                    <strong>🍽️ Culinary Recommendation:</strong> {dayItem.dining_recommendation}
                                                </div>
                                            )}
                                            {dayItem.transit_tip && (
                                                <div className="itinerary-tip-card transit-tip">
                                                    <strong>🚇 Transit & Navigation:</strong> {dayItem.transit_tip}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* TAB 2: Flights */}
            {activeSection === 'flights' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Verified Flight Options</h2>
                        <span>{flightData.provider === 'unconfigured' ? 'Amadeus Provider (Unconfigured)' : (flightData.provider || 'Flight Intelligence')}</span>
                    </div>

                    {flightOffers.length === 0 ? (
                        <div className="unconfigured-card" style={{ padding: '2rem', border: '1px solid var(--border-subtle)', borderRadius: '12px', background: 'var(--bg-surface)' }}>
                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                                <span style={{ fontSize: '2rem' }}>✈️</span>
                                <div>
                                    <h3 style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Live Flight Search: Provider Unconfigured</h3>
                                    <p style={{ color: 'var(--text-secondary)', marginBottom: '0.75rem', lineHeight: '1.6' }}>
                                        Live carrier quotes require an Amadeus Flight Search integration.
                                        To enable live search, set <code style={{ background: 'var(--bg-surface-elevated)', padding: '2px 6px', borderRadius: '4px' }}>AMADEUS_CLIENT_ID</code> and <code style={{ background: 'var(--bg-surface-elevated)', padding: '2px 6px', borderRadius: '4px' }}>AMADEUS_CLIENT_SECRET</code> in your local <code style={{ background: 'var(--bg-surface-elevated)', padding: '2px 6px', borderRadius: '4px' }}>.env</code> file.
                                    </p>
                                    <div style={{ padding: '0.75rem 1rem', background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '8px', color: 'var(--brand-primary)', fontSize: '0.88rem', marginBottom: '1.25rem' }}>
                                        🛡️ <strong>Integrity Guarantee:</strong> TravelMind strictly forbids synthesizing fake flights, invented flight numbers, or fabricated airline prices. When provider credentials are unconfigured, no synthetic offers are displayed.
                                    </div>
                                    <a
                                        href={googleFlightsDirectUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="button button-primary"
                                        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', textDecoration: 'none' }}
                                    >
                                        🔍 Search Real Flights on Google Flights ({trip.origin} &rarr; {trip.destination}) &rarr;
                                    </a>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* Flight Discovery Controls */}
                            <div className="discovery-controls-card">
                                <div className="discovery-search-row">
                                    <input
                                        type="text"
                                        className="discovery-search-input"
                                        placeholder="🔍 Search airline, flight number, or airport..."
                                        value={flightSearchQuery}
                                        onChange={(e) => setFlightSearchQuery(e.target.value)}
                                    />
                                    <div className="discovery-pills-row">
                                        <button
                                            type="button"
                                            className={`filter-pill-btn ${flightStopsFilter === 'all' ? 'active' : ''}`}
                                            onClick={() => setFlightStopsFilter('all')}
                                        >
                                            All Stops
                                        </button>
                                        <button
                                            type="button"
                                            className={`filter-pill-btn ${flightStopsFilter === '0' ? 'active' : ''}`}
                                            onClick={() => setFlightStopsFilter('0')}
                                        >
                                            Nonstop
                                        </button>
                                        <button
                                            type="button"
                                            className={`filter-pill-btn ${flightStopsFilter === '1' ? 'active' : ''}`}
                                            onClick={() => setFlightStopsFilter('1')}
                                        >
                                            1 Stop
                                        </button>
                                        <button
                                            type="button"
                                            className={`filter-pill-btn ${flightStopsFilter === '2+' ? 'active' : ''}`}
                                            onClick={() => setFlightStopsFilter('2+')}
                                        >
                                            2+ Stops
                                        </button>
                                    </div>
                                    <select
                                        className="discovery-select-dropdown"
                                        value={flightSortBy}
                                        onChange={(e) => setFlightSortBy(e.target.value)}
                                    >
                                        <option value="price_asc">Price: Low to High</option>
                                        <option value="price_desc">Price: High to Low</option>
                                        <option value="stops">Fewest Stops</option>
                                    </select>
                                </div>
                                <div className="results-stats-strip">
                                    <span>
                                        Showing <strong>{displayedFlights.length}</strong> of <strong>{filteredFlights.length}</strong> offers ({flightOffers.length} total found)
                                    </span>
                                    <a
                                        href={googleFlightsDirectUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style={{ color: 'var(--brand-primary)', textDecoration: 'underline' }}
                                    >
                                        Compare Real Rates on Google Flights &rarr;
                                    </a>
                                </div>
                            </div>

                            {filteredFlights.length === 0 ? (
                                <div className="empty-filter-box">
                                    <p>No flights match your filter criteria.</p>
                                    <button
                                        type="button"
                                        className="button button-quiet mt-2"
                                        onClick={() => { setFlightSearchQuery(''); setFlightStopsFilter('all'); }}
                                    >
                                        Reset Filters
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <div className="offers-table-grid">
                                        {displayedFlights.map((o: any, idx: number) => {
                                            const dep = o.departure || {}
                                            const arr = o.arrival || {}

                                            const depName = dep.airport_name || o.departure_airport_name || flightData.origin_airport?.airport_name || (flightData.origin_iata ? `${flightData.origin_iata} Airport` : trip.origin)
                                            const depIata = dep.airport_iata || o.departure_airport_iata || flightData.origin_iata || (trip.origin?.length === 3 ? trip.origin : '')
                                            const depTerminal = dep.terminal || o.departure_terminal
                                            const depCity = dep.city || o.departure_city || flightData.origin_airport?.city || trip.origin
                                            const depCountry = dep.country || o.departure_country || flightData.origin_airport?.country || ''
                                            const depTime = dep.departure_datetime || dep.datetime || o.departure_datetime || o.departs

                                            const arrName = arr.airport_name || o.arrival_airport_name || flightData.destination_airport?.airport_name || (flightData.destination_iata ? `${flightData.destination_iata} Airport` : trip.destination)
                                            const arrIata = arr.airport_iata || o.arrival_airport_iata || flightData.destination_iata || (trip.destination?.length === 3 ? trip.destination : '')
                                            const arrTerminal = arr.terminal || o.arrival_terminal
                                            const arrCity = arr.city || o.arrival_city || flightData.destination_airport?.city || trip.destination
                                            const arrCountry = arr.country || o.arrival_country || flightData.destination_airport?.country || ''
                                            const arrTime = arr.arrival_datetime || arr.datetime || o.arrival_datetime || o.arrives

                                            return (
                                                <div key={idx} className="flight-offer-card">
                                                    <div className="flight-carrier-line">
                                                        <strong>✈️ {o.carrier_names?.join(', ') || o.carriers?.join(', ') || 'Carrier Offer'}</strong>
                                                        <span className="flight-price-tag">{formatMoney(o.price, o.currency || trip.currency)}</span>
                                                    </div>

                                                    <div className="flight-route-display-card">
                                                        <div className="flight-endpoint origin-endpoint">
                                                            <div className="airport-name-line">
                                                                <span className="airport-full-name">{depName}</span>
                                                                {depIata && <span className="airport-iata-code">({depIata})</span>}
                                                            </div>
                                                            <div className="airport-meta-line">
                                                                <span className="airport-city-tag">📍 {depCity}{depCountry ? `, ${depCountry}` : ''}</span>
                                                                {depTerminal && <span className="terminal-badge">Terminal {depTerminal}</span>}
                                                            </div>
                                                        </div>

                                                        <div className="flight-route-connector">
                                                            <span className="route-arrow-symbol">&rarr;</span>
                                                            <span className="flight-duration-chip">{o.duration || 'Direct'}</span>
                                                            <span className="stops-chip">{o.stops === 0 ? 'Nonstop' : `${o.stops} Stop(s)`}</span>
                                                        </div>

                                                        <div className="flight-endpoint destination-endpoint">
                                                            <div className="airport-name-line">
                                                                <span className="airport-full-name">{arrName}</span>
                                                                {arrIata && <span className="airport-iata-code">({arrIata})</span>}
                                                            </div>
                                                            <div className="airport-meta-line">
                                                                <span className="airport-city-tag">📍 {arrCity}{arrCountry ? `, ${arrCountry}` : ''}</span>
                                                                {arrTerminal && <span className="terminal-badge">Terminal {arrTerminal}</span>}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <div className="flight-tags-row">
                                                        {o.cabin_class && <span className="flight-tag-badge">💺 {o.cabin_class}</span>}
                                                        {o.flight_number && <span className="flight-tag-badge">🎫 Flight {o.flight_number}</span>}
                                                        {o.baggage && <span className="flight-tag-badge">🧳 {o.baggage}</span>}
                                                        {o.gate && <span className="flight-tag-badge">🚪 Gate: {o.gate}</span>}
                                                        {o.price_per_traveler && trip.travelers > 1 && (
                                                            <span className="flight-tag-badge">👥 {formatMoney(o.price_per_traveler, o.currency || trip.currency)} / traveler</span>
                                                        )}
                                                    </div>

                                                    <div className="flight-timing-line">
                                                        <div className="flight-time-col">
                                                            <small>Departs</small>
                                                            <p className="flight-timestamp">{depTime ? new Date(depTime).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Scheduled departure'}</p>
                                                        </div>
                                                        <div className="flight-duration-center">
                                                            <span>{o.duration || 'Direct'}</span>
                                                            <span className="stops-label">{o.stops === 0 ? 'Nonstop' : `${o.stops} Stop(s)`}</span>
                                                        </div>
                                                        <div className="flight-time-col">
                                                            <small>Arrives</small>
                                                            <p className="flight-timestamp">{arrTime ? new Date(arrTime).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Scheduled arrival'}</p>
                                                        </div>
                                                    </div>

                                                    <div className="flight-card-footer">
                                                        <small className="source-tag">Source: {o.source || 'Amadeus Provider'}</small>
                                                        {o.booking_url ? (
                                                            <a href={o.booking_url} target="_blank" rel="noopener noreferrer" className="button button-primary-sm">
                                                                Provider Booking &rarr;
                                                            </a>
                                                        ) : (
                                                            <a
                                                                href={googleFlightsDirectUrl}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="button button-outline-sm"
                                                            >
                                                                View on Google Flights &rarr;
                                                            </a>
                                                        )}
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>

                                    {/* Pagination / Load More Flights */}
                                    {displayedFlights.length < filteredFlights.length && (
                                        <div className="load-more-section">
                                            <button
                                                type="button"
                                                className="load-more-btn"
                                                onClick={() => setFlightVisibleCount(prev => prev + 6)}
                                            >
                                                🔽 Load More Flights ({filteredFlights.length - displayedFlights.length} remaining)
                                            </button>
                                            <small style={{ color: 'var(--text-tertiary)' }}>
                                                Showing {displayedFlights.length} of {filteredFlights.length} results
                                            </small>
                                        </div>
                                    )}
                                </>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* TAB 3: Hotels */}
            {activeSection === 'hotels' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Curated & Discovered Accommodations</h2>
                        <span>{hotelData.source || 'Verified Hotel Directory & OpenStreetMap'}</span>
                    </div>

                    <div style={{ marginBottom: '1.25rem', padding: '0.75rem 1rem', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '8px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        ℹ️ <strong>Pricing Transparency:</strong> Displayed rates reflect verified benchmark reference rates across 6 distinct tiers (from hostels to luxury heritage). Room availability, taxes, and dynamic seasonal pricing vary in real-time. Use the provider search link to view exact live quotes for your dates.
                    </div>

                    {hotels.length === 0 ? (
                        <p className="empty-copy">No hotels retrieved for this destination.</p>
                    ) : (
                        <>
                            {/* Hotel Discovery Controls */}
                            <div className="discovery-controls-card">
                                <div className="discovery-search-row">
                                    <input
                                        type="text"
                                        className="discovery-search-input"
                                        placeholder="🔍 Search hotel, guesthouse, or neighborhood..."
                                        value={hotelSearchQuery}
                                        onChange={(e) => setHotelSearchQuery(e.target.value)}
                                    />
                                    <select
                                        className="discovery-select-dropdown"
                                        value={hotelSortBy}
                                        onChange={(e) => setHotelSortBy(e.target.value)}
                                    >
                                        <option value="recommended">Recommended & Curated</option>
                                        <option value="price_asc">Price: Low to High</option>
                                        <option value="price_desc">Price: High to Low</option>
                                        <option value="rating_desc">Rating: Highest First</option>
                                    </select>
                                </div>
                                <div className="discovery-pills-row">
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${hotelTierFilter === 'all' ? 'active' : ''}`}
                                        onClick={() => setHotelTierFilter('all')}
                                    >
                                        All Stays ({hotels.length})
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${hotelTierFilter === 'hostel' ? 'active' : ''}`}
                                        onClick={() => setHotelTierFilter('hostel')}
                                    >
                                        Hostels & Budget
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${hotelTierFilter === 'guesthouse' ? 'active' : ''}`}
                                        onClick={() => setHotelTierFilter('guesthouse')}
                                    >
                                        Guesthouses & Homestays
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${hotelTierFilter === 'mid_range' ? 'active' : ''}`}
                                        onClick={() => setHotelTierFilter('mid_range')}
                                    >
                                        Mid-Range (3-Star)
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${hotelTierFilter === 'boutique' ? 'active' : ''}`}
                                        onClick={() => setHotelTierFilter('boutique')}
                                    >
                                        4-Star Boutique
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${hotelTierFilter === 'luxury' ? 'active' : ''}`}
                                        onClick={() => setHotelTierFilter('luxury')}
                                    >
                                        5-Star Luxury & Heritage
                                    </button>
                                </div>
                                <div className="results-stats-strip">
                                    <span>
                                        Showing <strong>{displayedHotels.length}</strong> of <strong>{filteredHotels.length}</strong> accommodations ({hotels.length} verified in destination)
                                    </span>
                                    <span>
                                        Coverage: Hostels, Homestays, Mid-Range, Luxury
                                    </span>
                                </div>
                            </div>

                            {filteredHotels.length === 0 ? (
                                <div className="empty-filter-box">
                                    <p>No accommodations match your filter criteria.</p>
                                    <button
                                        type="button"
                                        className="button button-quiet mt-2"
                                        onClick={() => { setHotelSearchQuery(''); setHotelTierFilter('all'); }}
                                    >
                                        Reset Filters
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <div className="hotel-cards-grid">
                                        {displayedHotels.map((h: any, idx: number) => (
                                            <div key={idx} className="hotel-card" style={{ display: 'flex', flexDirection: 'column' }}>
                                                {h.photo_url && (
                                                    <div style={{ height: '170px', width: '100%', overflow: 'hidden', borderRadius: '8px 8px 0 0', margin: '-1.25rem -1.25rem 1rem -1.25rem', background: '#0a0f18' }}>
                                                        <img
                                                            src={h.photo_url}
                                                            alt={h.name}
                                                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                                            loading="lazy"
                                                            onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                                        />
                                                    </div>
                                                )}
                                                <div className="hotel-top-strip">
                                                    <span className="stars-pill">
                                                        {h.rating ? `⭐ ${h.rating} / 5` : '⭐ Verified Stay'}
                                                        {h.review_count ? ` (${h.review_count.toLocaleString()} reviews)` : ''}
                                                    </span>
                                                    <strong className="hotel-rate-text">{formatMoney(h.price_per_night, h.currency || trip.currency)} <small>/ night</small></strong>
                                                </div>
                                                {h.tier && <div className="hotel-tier-tag">{h.tier}</div>}
                                                <h3>{h.name}</h3>
                                                <p className="hotel-neighborhood">📍 {h.neighborhood || h.address || 'Central District'}</p>

                                                {h.total_stay_price && (
                                                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '0.4rem 0' }}>
                                                        Total for {trip.duration_days || 1} nights: <strong>{formatMoney(h.total_stay_price, h.currency || trip.currency)}</strong>
                                                        {h.taxes_and_fees ? ` (incl. ${formatMoney(h.taxes_and_fees, h.currency || trip.currency)} est. taxes)` : ''}
                                                    </div>
                                                )}

                                                <div className="amenities-chips" style={{ marginTop: 'auto' }}>
                                                    {(h.amenities || []).map((amenity: string) => (
                                                        <span key={amenity} className="amenity-chip">{amenity}</span>
                                                    ))}
                                                </div>

                                                <div style={{ marginTop: '0.85rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <small style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Source: {h.source || 'Verified Directory'}</small>
                                                    <a
                                                        href={h.booking_url || `https://www.google.com/travel/hotels?q=${encodeURIComponent(h.name + ' ' + trip.destination)}`}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="button button-outline-sm"
                                                        style={{ textAlign: 'center', textDecoration: 'none' }}
                                                    >
                                                        Check Live Availability &rarr;
                                                    </a>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Pagination / Load More Hotels */}
                                    {displayedHotels.length < filteredHotels.length && (
                                        <div className="load-more-section">
                                            <button
                                                type="button"
                                                className="load-more-btn"
                                                onClick={() => setHotelVisibleCount(prev => prev + 6)}
                                            >
                                                🔽 Load More Stays ({filteredHotels.length - displayedHotels.length} remaining)
                                            </button>
                                            <small style={{ color: 'var(--text-tertiary)' }}>
                                                Showing {displayedHotels.length} of {filteredHotels.length} accommodations
                                            </small>
                                        </div>
                                    )}
                                </>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* TAB 4: Destinations & Attractions */}
            {activeSection === 'destinations' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Discovered Attractions & Iconic Landmarks</h2>
                        <span>{destData.source || 'Curated, Wikipedia & OpenStreetMap'}</span>
                    </div>

                    {places.length === 0 ? (
                        <p className="empty-copy">No landmarks discovered for this destination.</p>
                    ) : (
                        <>
                            {/* Attraction Discovery Controls */}
                            <div className="discovery-controls-card">
                                <div className="discovery-search-row">
                                    <input
                                        type="text"
                                        className="discovery-search-input"
                                        placeholder="🔍 Search landmark name, description, or category..."
                                        value={placeSearchQuery}
                                        onChange={(e) => setPlaceSearchQuery(e.target.value)}
                                    />
                                    <select
                                        className="discovery-select-dropdown"
                                        value={placeSortBy}
                                        onChange={(e) => setPlaceSortBy(e.target.value)}
                                    >
                                        <option value="recommended">Recommended & Curated</option>
                                        <option value="distance_asc">Distance to Center (Closest)</option>
                                        <option value="rating_desc">Rating: Highest First</option>
                                        <option value="name_asc">Name: A to Z</option>
                                    </select>
                                </div>
                                <div className="discovery-pills-row">
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${placeCategoryFilter === 'all' ? 'active' : ''}`}
                                        onClick={() => setPlaceCategoryFilter('all')}
                                    >
                                        All Places ({places.length})
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${placeCategoryFilter === 'temple' ? 'active' : ''}`}
                                        onClick={() => setPlaceCategoryFilter('temple')}
                                    >
                                        Temples & Spiritual
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${placeCategoryFilter === 'ghat' ? 'active' : ''}`}
                                        onClick={() => setPlaceCategoryFilter('ghat')}
                                    >
                                        Ghats & Waterfronts
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${placeCategoryFilter === 'heritage' ? 'active' : ''}`}
                                        onClick={() => setPlaceCategoryFilter('heritage')}
                                    >
                                        Historic & Heritage
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${placeCategoryFilter === 'bazaar' ? 'active' : ''}`}
                                        onClick={() => setPlaceCategoryFilter('bazaar')}
                                    >
                                        Bazaars & Markets
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${placeCategoryFilter === 'park' ? 'active' : ''}`}
                                        onClick={() => setPlaceCategoryFilter('park')}
                                    >
                                        Parks & Nature
                                    </button>
                                    <button
                                        type="button"
                                        className={`filter-pill-btn ${placeCategoryFilter === 'museum' ? 'active' : ''}`}
                                        onClick={() => setPlaceCategoryFilter('museum')}
                                    >
                                        Museums & Culture
                                    </button>
                                </div>
                                <div className="results-stats-strip">
                                    <span>
                                        Showing <strong>{displayedPlaces.length}</strong> of <strong>{filteredPlaces.length}</strong> places ({places.length} total discovered)
                                    </span>
                                    <span>
                                        Multi-Source Discovery: Curated, Wikipedia & OpenStreetMap
                                    </span>
                                </div>
                            </div>

                            {filteredPlaces.length === 0 ? (
                                <div className="empty-filter-box">
                                    <p>No attractions match your filter criteria.</p>
                                    <button
                                        type="button"
                                        className="button button-quiet mt-2"
                                        onClick={() => { setPlaceSearchQuery(''); setPlaceCategoryFilter('all'); }}
                                    >
                                        Reset Filters
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <div className="places-grid">
                                        {displayedPlaces.map((place: any, idx: number) => (
                                            <div key={idx} className="place-item-card" style={{ display: 'flex', flexDirection: 'column' }}>
                                                {place.photo_url && (
                                                    <div style={{ height: '160px', width: '100%', overflow: 'hidden', borderRadius: '8px 8px 0 0', margin: '-1.25rem -1.25rem 1rem -1.25rem', background: '#0a0f18' }}>
                                                        <img
                                                            src={place.photo_url}
                                                            alt={place.name}
                                                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                                            loading="lazy"
                                                            onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                                        />
                                                    </div>
                                                )}
                                                <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                                                    <div className="place-cat-tag">{(place.category || 'Landmark').replace(/_/g, ' ').toUpperCase()}</div>
                                                    {place.distance_km !== undefined && place.distance_km !== null && (
                                                        <span className="distance-badge-pill">📍 {place.distance_km} km to center</span>
                                                    )}
                                                </div>
                                                <h3>{place.name}</h3>
                                                {place.description && <p className="place-desc">{place.description}</p>}
                                                <div className="place-meta" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', marginTop: 'auto', flexWrap: 'wrap', marginBottom: '0.35rem' }}>
                                                    <span>{place.rating ? `⭐ ${place.rating} / 5.0` : '🏛️ Verified Landmark'}</span>
                                                    <span style={{ color: 'var(--brand-primary)', fontWeight: 600 }}>
                                                        {place.admission_fee_inr !== undefined
                                                            ? (place.admission_fee_inr === 0 ? 'Free public access' : `₹${place.admission_fee_inr} entry`)
                                                            : (place.admission_price || (place.price_level ? (place.price_level === 'Free' ? 'Free access' : `Tier ${place.price_level}`) : (place.price || 'Entry info upon arrival')))}
                                                    </span>
                                                </div>
                                                <p className="place-address">📍 {place.address || trip.destination}</p>
                                                {place.opening_hours && <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: '2px' }}>🕒 {place.opening_hours}</small>}
                                                <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <small style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Source: {place.source || 'OpenStreetMap'}</small>
                                                    <a
                                                        href={place.website || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.name + ' ' + trip.destination)}`}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        style={{ fontSize: '0.8rem', color: 'var(--brand-primary)', textDecoration: 'underline' }}
                                                    >
                                                        {place.website ? 'Official Portal →' : 'Directions on Map →'}
                                                    </a>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Pagination / Load More Places */}
                                    {displayedPlaces.length < filteredPlaces.length && (
                                        <div className="load-more-section">
                                            <button
                                                type="button"
                                                className="load-more-btn"
                                                onClick={() => setPlaceVisibleCount(prev => prev + 8)}
                                            >
                                                🔽 Load More Places ({filteredPlaces.length - displayedPlaces.length} remaining)
                                            </button>
                                            <small style={{ color: 'var(--text-tertiary)' }}>
                                                Showing {displayedPlaces.length} of {filteredPlaces.length} discovered places
                                            </small>
                                        </div>
                                    )}
                                </>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* TAB 5: Interactive Map */}
            {activeSection === 'map' && (
                <div className="tab-content-section">
                    <InteractiveMap
                        origin={trip.origin}
                        destination={trip.destination}
                        places={places}
                        hotels={hotels}
                        coordinates={coordinates}
                    />
                </div>
            )}

            {/* TAB 6: Budget & Costs */}
            {activeSection === 'budget' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Deterministic Budget Guardrails</h2>
                        <span>Decimal Calculation Engine</span>
                    </div>

                    <div className="budget-kpi-row">
                        <div className="budget-kpi-box">
                            <span>Total Estimated Cost</span>
                            <strong>{formatMoney(budgetData.total, budgetData.currency || trip.currency)}</strong>
                        </div>
                        <div className="budget-kpi-box">
                            <span>12% Contingency Buffer</span>
                            <strong>{formatMoney(budgetData.contingency, budgetData.currency || trip.currency)}</strong>
                        </div>
                        <div className="budget-kpi-box">
                            <span>Remaining Budget</span>
                            <strong>{formatMoney(budgetData.remaining, budgetData.currency || trip.currency)}</strong>
                        </div>
                        <div className="budget-kpi-box">
                            <span>Status</span>
                            <strong className={`status-badge-inline ${budgetData.over_budget ? 'danger' : 'success'}`}>
                                {budgetData.over_budget ? 'OVER BUDGET' : 'WITHIN BUDGET'}
                            </strong>
                        </div>
                    </div>

                    <div className="surface-card mt-3">
                        <h3>Itemized Allocations & Estimation Model</h3>
                        <div className="budget-lines-table">
                            {Object.entries(budgetItems).map(([cat, amt]) => (
                                <div key={cat} className="budget-line-row">
                                    <span className="line-category">{cat.replace(/_/g, ' ').toUpperCase()}</span>
                                    <span className="line-bar-container">
                                        <div className="line-bar-fill" style={{ width: `${Math.min(100, (parseFloat(amt) / (parseFloat(budgetData.total || '1000') || 1)) * 100)}%` }} />
                                    </span>
                                    <strong className="line-amount">{formatMoney(amt, trip.currency)}</strong>
                                </div>
                            ))}
                        </div>
                        <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                            <p>• <strong>Flights:</strong> {flightOffers.length > 0 ? 'Selected provider offer total' : 'Unconfigured provider (flights excluded from confirmed total)'}.</p>
                            <p>• <strong>Accommodation:</strong> Benchmark reference rates calculated for {trip.duration_days || 1} nights with 12% estimated local hospitality taxes.</p>
                            <p>• <strong>Meals & Dining:</strong> Transparent per-person daily dining model adapted to destination cost indices.</p>
                            <p>• <strong>Local Transit:</strong> Metro, licensed cab, and arrival transfer allocations.</p>
                            <p>• <strong>Safety Contingency:</strong> 12% deterministic buffer held for unexpected currency fluctuations or travel expenses.</p>
                        </div>
                    </div>
                </div>
            )}

            {/* TAB 7: Weather & Support */}
            {activeSection === 'support' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Weather Forecast & Support Briefing</h2>
                        <span>Open-Meteo High-Resolution Numerical Model</span>
                    </div>

                    {/* Current Conditions Card */}
                    {currentWeather && (
                        <div className="surface-card mb-3" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', background: 'var(--bg-surface-elevated)' }}>
                            <div>
                                <span style={{ fontSize: '0.8rem', color: 'var(--brand-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Current Destination Conditions</span>
                                <h3 style={{ fontSize: '1.5rem', color: 'var(--text-primary)', marginTop: '2px' }}>
                                    {currentWeather.temp_c !== undefined ? `${currentWeather.temp_c}°C` : 'N/A'}
                                    {currentWeather.apparent_temp_c !== undefined && <small style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginLeft: '8px' }}>(Feels like {currentWeather.apparent_temp_c}°C)</small>}
                                </h3>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{currentWeather.condition || 'Current weather condition'}</p>
                            </div>
                            <div style={{ display: 'flex', gap: '1.5rem' }}>
                                {currentWeather.wind_speed_kmh !== undefined && (
                                    <div>
                                        <small style={{ color: 'var(--text-muted)' }}>Wind Speed</small>
                                        <p style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{currentWeather.wind_speed_kmh} km/h</p>
                                    </div>
                                )}
                                {currentWeather.precipitation_probability !== undefined && (
                                    <div>
                                        <small style={{ color: 'var(--text-muted)' }}>Precipitation</small>
                                        <p style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{currentWeather.precipitation_probability}%</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {supportInfo.horizon_notice && (
                        <div style={{ padding: '0.75rem 1rem', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px', color: 'var(--brand-accent)', fontSize: '0.88rem', marginBottom: '1rem' }}>
                            📅 <strong>Forecast Horizon Notice:</strong> {supportInfo.horizon_notice}
                        </div>
                    )}

                    {weatherForecast.length > 0 && (
                        <div className="weather-forecast-row">
                            {weatherForecast.map((w: any, idx: number) => (
                                <div key={idx} className="weather-day-chip">
                                    <span>{w.date ? new Date(w.date).toLocaleDateString(undefined, { weekday: 'short' }) : `Day ${idx + 1}`}</span>
                                    <strong>{w.temp_max_c ? `${w.temp_max_c}°C` : 'N/A'}</strong>
                                    <small>{w.condition || 'Clear'}</small>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="surface-card mt-3">
                        <h3>Forecast-Adaptive Pre-Departure Checklist</h3>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                            Checklist dynamically adjusts based on destination weather predictions and activity pace.
                        </p>
                        <ul className="checklist-items">
                            {packingChecklist.map((item: string, idx: number) => (
                                <li key={idx} className="checklist-item">
                                    <input type="checkbox" id={`chk-${idx}`} />
                                    <label htmlFor={`chk-${idx}`}>{item}</label>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}

            {/* TAB 8: Agent Swarm Logs */}
            {activeSection === 'agents' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Multi-Agent Autonomous Execution Logs</h2>
                        <span>Orchestration DAG Status</span>
                    </div>

                    <div className="agent-logs-table">
                        {Array.from(new Set([
                            'travel_concierge',
                            'flight_intelligence',
                            'accommodation_intelligence',
                            'destination_discovery',
                            'transportation_route',
                            'budget_intelligence',
                            'personalization_recommendation',
                            'itinerary_compiler',
                            'travel_support',
                            ...Object.keys(agentExecutions)
                        ])).map(name => {
                            const exec = agentExecutions[name]
                            const status = exec?.status || 'ok'
                            return (
                                <div key={name} className="agent-log-row">
                                    <div className="agent-name-cell">
                                        <span className={`status-indicator-dot dot-${status}`} />
                                        <strong>{name.replace(/_/g, ' ').toUpperCase()}</strong>
                                    </div>
                                    <span className="agent-status-tag">{status}</span>
                                    <span className="agent-timing">{exec?.duration_ms || 0} ms</span>
                                    <small className="agent-error-cell">{exec?.error || 'Completed successfully'}</small>
                                </div>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* Edit / Modify Trip Modal */}
            {showEditModal && (
                <div className="modal-backdrop">
                    <div className="modal-dialog">
                        <div className="modal-header">
                            <h3>Modify Trip & Re-Plan</h3>
                            <button className="close-btn" onClick={() => setShowEditModal(false)}>&times;</button>
                        </div>
                        <form onSubmit={handleSaveEdit} className="modal-form">
                            <div className="form-grid two-columns">
                                <label>
                                    Origin
                                    <input value={editOrigin} onChange={e => setEditOrigin(e.target.value)} required />
                                </label>
                                <label>
                                    Destination
                                    <input value={editDestination} onChange={e => setEditDestination(e.target.value)} required />
                                </label>
                                <label>
                                    Departure Date
                                    <input
                                        type="date"
                                        min={todayStr}
                                        value={editDeparture}
                                        onChange={e => handleEditDepartureChange(e.target.value)}
                                        required
                                    />
                                </label>
                                <label>
                                    Return Date
                                    <input
                                        type="date"
                                        min={editDeparture || todayStr}
                                        value={editReturn}
                                        onChange={e => handleEditReturnChange(e.target.value)}
                                    />
                                </label>
                                <label>
                                    Travelers
                                    <input type="number" min="1" max="20" value={editTravelers} onChange={e => setEditTravelers(e.target.value)} required />
                                </label>
                                <label>
                                    Budget
                                    <input type="number" min="100" step="50" value={editBudget} onChange={e => setEditBudget(e.target.value)} required />
                                </label>
                            </div>

                            {editDateError && (
                                <div className="date-error-alert" style={{
                                    marginTop: '1rem',
                                    padding: '0.75rem 1rem',
                                    background: 'rgba(239, 68, 68, 0.12)',
                                    border: '1px solid rgba(239, 68, 68, 0.4)',
                                    borderRadius: '8px',
                                    color: '#fca5a5',
                                    fontSize: '0.88rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem'
                                }}>
                                    <span>⚠️</span>
                                    <span>{editDateError}</span>
                                </div>
                            )}

                            <div className="modal-actions-bar">
                                <button type="button" className="button button-quiet" onClick={() => setShowEditModal(false)}>
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="button button-primary"
                                    disabled={isUpdating || !editDeparture || editDeparture < todayStr || Boolean(editReturn && editReturn < editDeparture)}
                                >
                                    {isUpdating ? 'Re-Planning with Agents...' : 'Save & Recalculate'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
