import React, { useState, useMemo } from 'react'
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

function formatFriendlySource(source?: string): { title: string; subtitle: string; badge: string } {
    if (!source) {
        return {
            title: 'Autonomous Multi-Agent Synthesis',
            subtitle: 'Orchestrated via TravelMind Agent Swarm',
            badge: 'Multi-Agent AI'
        }
    }
    const clean = source.toLowerCase().trim()
    if (clean === 'grounded_research_fallback' || clean.includes('grounded_research')) {
        return {
            title: 'Research-Based Grounded Itinerary',
            subtitle: 'Synthesized with verified multi-source research intelligence',
            badge: 'Verified Research'
        }
    }
    if (clean.includes('amadeus')) {
        return {
            title: 'Amadeus Verified GDS Network',
            subtitle: 'Live global distribution flight system',
            badge: 'Global Distribution'
        }
    }
    if (clean.includes('multi_agent') || clean.includes('dag')) {
        return {
            title: 'Multi-Agent Autonomous DAG',
            subtitle: 'Compiled via multi-agent execution pipeline',
            badge: 'Autonomous DAG'
        }
    }
    if (clean.includes('deterministic')) {
        return {
            title: 'Deterministic Calculation Engine',
            subtitle: 'Validated against budgetary & geographical guardrails',
            badge: 'Deterministic'
        }
    }
    if (clean.includes('curated') || clean.includes('openstreetmap')) {
        return {
            title: 'Curated Landmarks & OpenStreetMap',
            subtitle: 'Geocoded destination points and verified places',
            badge: 'Curated Data'
        }
    }
    const formatted = source
        .replace(/_/g, ' ')
        .split(' ')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ')
    return {
        title: formatted,
        subtitle: `Engine Provider: ${source}`,
        badge: 'Intelligence Pipeline'
    }
}

// Modern SVG Icons (Self-contained, sharp, zero external dependency)
const Icons = {
    Calendar: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
    ),
    Plane: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z" />
        </svg>
    ),
    Hotel: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M18 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2Z" />
            <path d="m9 16 .348-.24c1.465-1.013 3.84-1.013 5.304 0L15 16" />
            <path d="M8 7h.01" />
            <path d="M16 7h.01" />
            <path d="M12 7h.01" />
            <path d="M12 11h.01" />
            <path d="M16 11h.01" />
            <path d="M8 11h.01" />
            <path d="M10 22v-4h4v4" />
        </svg>
    ),
    Compass: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
        </svg>
    ),
    Map: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
            <line x1="8" y1="2" x2="8" y2="18" />
            <line x1="16" y1="6" x2="16" y2="22" />
        </svg>
    ),
    Wallet: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
            <path d="M3 5v14a2 2 0 0 0 2 2h16v-5" />
            <path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
        </svg>
    ),
    CloudSun: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 2v2" />
            <path d="m4.93 4.93 1.41 1.41" />
            <path d="M20 12h2" />
            <path d="m19.07 4.93-1.41 1.41" />
            <path d="M15.947 12.65a4 4 0 0 0-5.925-4.128" />
            <path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6Z" />
        </svg>
    ),
    Cpu: () => (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="4" y="4" width="16" height="16" rx="2" />
            <rect x="9" y="9" width="6" height="6" />
            <path d="M15 2v2" />
            <path d="M15 20v2" />
            <path d="M2 15h2" />
            <path d="M2 9h2" />
            <path d="M20 15h2" />
            <path d="M20 9h2" />
            <path d="M9 2v2" />
            <path d="M9 20v2" />
        </svg>
    ),
    ArrowLeft: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
        </svg>
    ),
    Printer: () => (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="6 9 6 2 18 2 18 9" />
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
            <rect x="6" y="14" width="12" height="8" />
        </svg>
    ),
    Edit: () => (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
        </svg>
    ),
    Trash: () => (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            <line x1="10" y1="11" x2="10" y2="17" />
            <line x1="14" y1="11" x2="14" y2="17" />
        </svg>
    ),
    Sunrise: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 2v6" />
            <path d="m4.93 10.93 1.41 1.41" />
            <path d="M2 18h2" />
            <path d="M20 18h2" />
            <path d="m19.07 10.93-1.41 1.41" />
            <path d="M22 22H2" />
            <path d="m8 6 4-4 4 4" />
            <path d="M16 18a4 4 0 0 0-8 0" />
        </svg>
    ),
    Sun: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
    ),
    Moon: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
        </svg>
    ),
    Clock: () => (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
        </svg>
    ),
    Users: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
    ),
    CheckCircle: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
    ),
    Utensils: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M18 2v6a3 3 0 0 1-3 3 3 3 0 0 1-3-3V2" />
            <path d="M15 11v11" />
            <path d="M5 2v10a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2V2" />
            <path d="M7 14v8" />
        </svg>
    ),
    Transit: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="4" y="3" width="16" height="14" rx="3" />
            <path d="M4 11h16" />
            <path d="M12 3v8" />
            <circle cx="8" cy="14" r="1" />
            <circle cx="16" cy="14" r="1" />
            <path d="m6 17-2 4" />
            <path d="m18 17 2 4" />
        </svg>
    ),
    Search: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
    ),
    Shield: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
    ),
    ExternalLink: () => (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
        </svg>
    ),
    Sparkles: () => (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />
        </svg>
    )
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

    // Interactive checklist state (persists checkmarks during viewing)
    const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({})

    function toggleCheckItem(idx: number) {
        setCheckedItems(prev => ({ ...prev, [idx]: !prev[idx] }))
    }

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
    const todayStr = useMemo(() => {
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

    const friendlySource = formatFriendlySource(itinerary?.source)

    const googleFlightsDirectUrl = flightData.direct_search_url || `https://www.google.com/travel/flights?q=flights+from+${encodeURIComponent(trip.origin)}+to+${encodeURIComponent(trip.destination)}${trip.departure_date ? `+on+${trip.departure_date}` : ''}`

    // Filtered & Sorted Flights
    const filteredFlights = useMemo(() => {
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
    const filteredHotels = useMemo(() => {
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
    const filteredPlaces = useMemo(() => {
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

    // Navigation Tabs Configuration with counts and modern icons
    const navTabs = [
        { id: 'itinerary', label: 'Daily Schedule', icon: <Icons.Calendar />, count: `${days.length} Days` },
        { id: 'flights', label: 'Flights', icon: <Icons.Plane />, count: flightOffers.length },
        { id: 'hotels', label: 'Hotels & Stays', icon: <Icons.Hotel />, count: hotels.length },
        { id: 'destinations', label: 'Attractions', icon: <Icons.Compass />, count: places.length },
        { id: 'map', label: 'Interactive Map', icon: <Icons.Map /> },
        { id: 'budget', label: 'Cost Breakdown', icon: <Icons.Wallet /> },
        { id: 'support', label: 'Weather & Checklist', icon: <Icons.CloudSun /> },
        { id: 'agents', label: 'Agent Pipeline', icon: <Icons.Cpu />, count: Object.keys(agentExecutions).length || 8 },
    ]

    return (
        <div className="plan-detail-container">
            {/* Top Bar Navigation */}
            <div className="plan-top-bar">
                <button className="back-link-btn" onClick={onClose} aria-label="Return to saved trips">
                    <Icons.ArrowLeft />
                    <span>Back to Trips</span>
                </button>
                <div className="plan-actions-group">
                    <button className="button button-outline-sm" onClick={() => onExportHtml(trip.id)}>
                        <Icons.Printer />
                        <span>Export HTML / Print</span>
                    </button>
                    <button className="button button-primary-sm" onClick={() => setShowEditModal(true)}>
                        <Icons.Edit />
                        <span>Modify & Re-Plan</span>
                    </button>
                    <button className="button button-danger-sm" onClick={() => onDeleteTrip(trip.id)}>
                        <Icons.Trash />
                        <span>Delete</span>
                    </button>
                </div>
            </div>

            {/* Redesigned Trip Header Banner */}
            <div className="plan-header-banner">
                <div className="banner-details">
                    <div className="banner-top-meta">
                        <span className="status-pill status-saved">
                            <span className="status-dot-pulse" />
                            {trip.status === 'draft' ? 'Saved Itinerary' : trip.status.toUpperCase()}
                        </span>
                        <span className="banner-id-tag">REF #{trip.id.slice(0, 8).toUpperCase()}</span>
                    </div>

                    <h1 className="trip-destination-heading">
                        <span className="route-city">{trip.origin}</span>
                        <span className="route-flow-arrow" aria-hidden="true">&rarr;</span>
                        <span className="route-city">{trip.destination}</span>
                    </h1>

                    <div className="banner-meta-grid">
                        <div className="meta-card">
                            <span className="meta-card-icon"><Icons.Calendar /></span>
                            <div className="meta-card-body">
                                <small>Travel Dates</small>
                                <strong>{trip.departure_date || 'Flexible'} {trip.return_date ? `to ${trip.return_date}` : ''}</strong>
                            </div>
                        </div>

                        <div className="meta-card">
                            <span className="meta-card-icon"><Icons.Clock /></span>
                            <div className="meta-card-body">
                                <small>Duration</small>
                                <strong>{days.length > 0 ? `${days.length} Days / ${Math.max(1, days.length - 1)} Nights` : (trip.duration_days ? `${trip.duration_days} Days` : 'Multi-Day')}</strong>
                            </div>
                        </div>

                        <div className="meta-card">
                            <span className="meta-card-icon"><Icons.Users /></span>
                            <div className="meta-card-body">
                                <small>Travelers</small>
                                <strong>{trip.travelers} Traveler{trip.travelers > 1 ? 's' : ''}</strong>
                            </div>
                        </div>

                        <div className="meta-card">
                            <span className="meta-card-icon"><Icons.Wallet /></span>
                            <div className="meta-card-body">
                                <small>Target Budget</small>
                                <strong>{trip.budget ? formatMoney(trip.budget, trip.currency) : 'Flexible'}</strong>
                            </div>
                        </div>
                    </div>

                    {trip.summary && (
                        <p className="banner-summary-text">{trip.summary}</p>
                    )}
                </div>

                <div className="banner-source-card" title={`Diagnostic Engine: ${itinerary?.source || 'deterministic'}`}>
                    <div className="source-card-badge">
                        <Icons.Shield />
                        <span>{friendlySource.badge}</span>
                    </div>
                    <strong className="source-card-title">{friendlySource.title}</strong>
                    <span className="source-card-subtitle">{friendlySource.subtitle}</span>
                </div>
            </div>

            {/* Redesigned Premium SaaS Dashboard Navigation Tabs */}
            <div className="plan-tabs-bar-container">
                <div className="plan-tabs-bar" role="tablist" aria-label="Itinerary navigation sections">
                    {navTabs.map(tab => {
                        const isActive = activeSection === tab.id
                        return (
                            <button
                                key={tab.id}
                                role="tab"
                                id={`tab-${tab.id}`}
                                aria-selected={isActive}
                                aria-controls={`panel-${tab.id}`}
                                className={`plan-tab-btn ${isActive ? 'active' : ''}`}
                                onClick={() => setActiveSection(tab.id)}
                            >
                                <span className="tab-icon-wrapper">{tab.icon}</span>
                                <span className="tab-label">{tab.label}</span>
                                {tab.count !== undefined && (
                                    <span className={`tab-count-badge ${isActive ? 'badge-active' : ''}`}>
                                        {tab.count}
                                    </span>
                                )}
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* TAB 1: Daily Schedule */}
            {activeSection === 'itinerary' && (
                <div className="tab-content-section" id="panel-itinerary" role="tabpanel" aria-labelledby="tab-itinerary">
                    <div className="section-heading-bar">
                        <div>
                            <h2>Personalized Daily Itinerary</h2>
                            <p className="section-subtext">Day-by-day curated schedule adapted to your destination and pace</p>
                        </div>
                        <span className="estimate-tag">{friendlySource.title}</span>
                    </div>

                    {days.length === 0 ? (
                        <div className="empty-filter-box">
                            <p>No daily schedule generated yet. Click 'Modify & Re-Plan' to calculate schedule.</p>
                        </div>
                    ) : (
                        <div className="itinerary-days-container">
                            {days.map((dayItem: any) => (
                                <div key={dayItem.day} className="day-schedule-card">
                                    <div className="day-header-strip">
                                        <div className="day-badge-wrapper">
                                            <span className="day-badge">DAY {String(dayItem.day).padStart(2, '0')}</span>
                                            {dayItem.date && <span className="day-date-label">{new Date(dayItem.date).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span>}
                                        </div>
                                        <h3 className="day-title-text">{dayItem.title || `Day ${dayItem.day} in ${trip.destination}`}</h3>
                                    </div>

                                    {/* Detailed time slots */}
                                    <div className="slots-grid">
                                        <div className="slot-box morning-slot">
                                            <div className="slot-header-line">
                                                <span className="slot-icon-badge morning-badge">
                                                    <Icons.Sunrise />
                                                    <span>MORNING</span>
                                                </span>
                                                {dayItem.morning?.time && (
                                                    <span className="slot-time-pill">
                                                        <Icons.Clock /> {dayItem.morning.time}
                                                    </span>
                                                )}
                                            </div>
                                            <h4>{dayItem.morning?.activity || dayItem.activities?.[0] || 'Morning Activity & Exploration'}</h4>
                                            {dayItem.morning?.cost && <div className="slot-cost">Est: {dayItem.morning.cost}</div>}
                                        </div>

                                        <div className="slot-box afternoon-slot">
                                            <div className="slot-header-line">
                                                <span className="slot-icon-badge afternoon-badge">
                                                    <Icons.Sun />
                                                    <span>AFTERNOON</span>
                                                </span>
                                                {dayItem.afternoon?.time && (
                                                    <span className="slot-time-pill">
                                                        <Icons.Clock /> {dayItem.afternoon.time}
                                                    </span>
                                                )}
                                            </div>
                                            <h4>{dayItem.afternoon?.activity || dayItem.activities?.[1] || 'Afternoon Sightseeing & Local Experience'}</h4>
                                            {dayItem.afternoon?.cost && <div className="slot-cost">Est: {dayItem.afternoon.cost}</div>}
                                        </div>

                                        <div className="slot-box evening-slot">
                                            <div className="slot-header-line">
                                                <span className="slot-icon-badge evening-badge">
                                                    <Icons.Moon />
                                                    <span>EVENING</span>
                                                </span>
                                                {dayItem.evening?.time && (
                                                    <span className="slot-time-pill">
                                                        <Icons.Clock /> {dayItem.evening.time}
                                                    </span>
                                                )}
                                            </div>
                                            <h4>{dayItem.evening?.activity || dayItem.activities?.[2] || 'Evening Dinner & Cultural Stroll'}</h4>
                                            {dayItem.evening?.cost && <div className="slot-cost">Est: {dayItem.evening.cost}</div>}
                                        </div>
                                    </div>

                                    {/* Regional Dining & Transit Highlights */}
                                    {(dayItem.dining_recommendation || dayItem.transit_tip) && (
                                        <div className="itinerary-tips-box">
                                            {dayItem.dining_recommendation && (
                                                <div className="itinerary-tip-card dining-tip">
                                                    <div className="tip-header">
                                                        <Icons.Utensils />
                                                        <strong>Culinary Recommendation</strong>
                                                    </div>
                                                    <p>{dayItem.dining_recommendation}</p>
                                                </div>
                                            )}
                                            {dayItem.transit_tip && (
                                                <div className="itinerary-tip-card transit-tip">
                                                    <div className="tip-header">
                                                        <Icons.Transit />
                                                        <strong>Transit & Navigation</strong>
                                                    </div>
                                                    <p>{dayItem.transit_tip}</p>
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
                <div className="tab-content-section" id="panel-flights" role="tabpanel" aria-labelledby="tab-flights">
                    <div className="section-heading-bar">
                        <div>
                            <h2>Verified Flight Options</h2>
                            <p className="section-subtext">Commercial air routes between {trip.origin} and {trip.destination}</p>
                        </div>
                        <span className="estimate-tag">{flightData.provider === 'unconfigured' ? 'Amadeus Global Distribution (Unconfigured)' : (flightData.provider || 'Flight Intelligence Engine')}</span>
                    </div>

                    {flightOffers.length === 0 ? (
                        <div className="flight-unconfigured-hero-card unconfigured-card">
                            <div className="flight-unconfigured-header">
                                <div className="flight-provider-icon-box">
                                    <Icons.Plane />
                                </div>
                                <div className="flight-provider-text">
                                    <h3>Live Flight Search: Provider Unconfigured</h3>
                                    <p>
                                        Live carrier quotes require an active Amadeus GDS connection.
                                        Configure <code className="inline-code">AMADEUS_CLIENT_ID</code> and <code className="inline-code">AMADEUS_CLIENT_SECRET</code> in your environment to unlock direct real-time flight booking quotes.
                                    </p>
                                </div>
                            </div>

                            <div className="integrity-guarantee-pill">
                                <Icons.Shield />
                                <div>
                                    <strong>Strict Zero-Synthetic Data Policy:</strong> TravelMind enforces strict factual integrity. We never synthesize fictional airlines, fake flight numbers, or simulated fare prices.
                                </div>
                            </div>

                            <div className="unconfigured-actions-strip">
                                <a
                                    href={googleFlightsDirectUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="button button-primary"
                                >
                                    <Icons.Search />
                                    <span>Search Real Flights on Google Flights ({trip.origin} &rarr; {trip.destination}) &rarr;</span>
                                </a>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* Flight Discovery Controls */}
                            <div className="discovery-controls-card">
                                <div className="discovery-search-row">
                                    <div className="search-input-wrapper">
                                        <Icons.Search />
                                        <input
                                            type="text"
                                            className="discovery-search-input"
                                            placeholder="Search carrier, flight number, or airport..."
                                            value={flightSearchQuery}
                                            onChange={(e) => setFlightSearchQuery(e.target.value)}
                                        />
                                    </div>
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
                                        aria-label="Sort flights"
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
                                        className="direct-provider-link"
                                    >
                                        <span>Compare Real Rates on Google Flights</span>
                                        <Icons.ExternalLink />
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
                                                        <div className="carrier-identity">
                                                            <span className="carrier-icon"><Icons.Plane /></span>
                                                            <strong>{o.carrier_names?.join(', ') || o.carriers?.join(', ') || 'Airline Carrier Offer'}</strong>
                                                        </div>
                                                        <span className="flight-price-tag">{formatMoney(o.price, o.currency || trip.currency)}</span>
                                                    </div>

                                                    <div className="flight-route-display-card">
                                                        <div className="flight-endpoint origin-endpoint">
                                                            <div className="airport-name-line">
                                                                <span className="airport-full-name">{depName}</span>
                                                                {depIata && <span className="airport-iata-code">{depIata}</span>}
                                                            </div>
                                                            <div className="airport-meta-line">
                                                                <span className="airport-city-tag">{depCity}{depCountry ? `, ${depCountry}` : ''}</span>
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
                                                                {arrIata && <span className="airport-iata-code">{arrIata}</span>}
                                                            </div>
                                                            <div className="airport-meta-line">
                                                                <span className="airport-city-tag">{arrCity}{arrCountry ? `, ${arrCountry}` : ''}</span>
                                                                {arrTerminal && <span className="terminal-badge">Terminal {arrTerminal}</span>}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <div className="flight-tags-row">
                                                        {o.cabin_class && <span className="flight-tag-badge">Class: {o.cabin_class}</span>}
                                                        {o.flight_number && <span className="flight-tag-badge">Flight #{o.flight_number}</span>}
                                                        {o.baggage && <span className="flight-tag-badge">Baggage: {o.baggage}</span>}
                                                        {o.gate && <span className="flight-tag-badge">Gate: {o.gate}</span>}
                                                        {o.price_per_traveler && trip.travelers > 1 && (
                                                            <span className="flight-tag-badge">{formatMoney(o.price_per_traveler, o.currency || trip.currency)} / traveler</span>
                                                        )}
                                                    </div>

                                                    <div className="flight-timing-line">
                                                        <div className="flight-time-col">
                                                            <small>Scheduled Departure</small>
                                                            <p className="flight-timestamp">{depTime ? new Date(depTime).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Scheduled departure'}</p>
                                                        </div>
                                                        <div className="flight-duration-center">
                                                            <span>{o.duration || 'Direct'}</span>
                                                            <span className="stops-label">{o.stops === 0 ? 'Nonstop' : `${o.stops} Stop(s)`}</span>
                                                        </div>
                                                        <div className="flight-time-col">
                                                            <small>Scheduled Arrival</small>
                                                            <p className="flight-timestamp">{arrTime ? new Date(arrTime).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Scheduled arrival'}</p>
                                                        </div>
                                                    </div>

                                                    <div className="flight-card-footer">
                                                        <small className="source-tag">GDS Provider: {o.source || 'Amadeus Network'}</small>
                                                        {o.booking_url ? (
                                                            <a href={o.booking_url} target="_blank" rel="noopener noreferrer" className="button button-primary-sm">
                                                                <span>Provider Booking</span>
                                                                <Icons.ExternalLink />
                                                            </a>
                                                        ) : (
                                                            <a
                                                                href={googleFlightsDirectUrl}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="button button-outline-sm"
                                                            >
                                                                <span>View on Google Flights</span>
                                                                <Icons.ExternalLink />
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
                                                <span>Load More Flights ({filteredFlights.length - displayedFlights.length} remaining)</span>
                                            </button>
                                            <small className="load-more-stats">
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
                <div className="tab-content-section" id="panel-hotels" role="tabpanel" aria-labelledby="tab-hotels">
                    <div className="section-heading-bar">
                        <div>
                            <h2>Curated & Discovered Accommodations</h2>
                            <p className="section-subtext">Verified hotels, boutique stays, and heritage properties in {trip.destination}</p>
                        </div>
                        <span className="estimate-tag">{hotelData.source || 'Verified Directory & OpenStreetMap'}</span>
                    </div>

                    <div className="transparency-callout-card">
                        <Icons.Shield />
                        <div>
                            <strong>Pricing Transparency:</strong> Displayed rates reflect verified benchmark reference rates across 6 distinct tiers (from hostels to luxury heritage). Room availability, taxes, and seasonal rates vary in real-time. Use the provider search link to view exact live quotes for your travel dates.
                        </div>
                    </div>

                    {hotels.length === 0 ? (
                        <div className="empty-filter-box">
                            <p>No accommodations retrieved for this destination.</p>
                        </div>
                    ) : (
                        <>
                            {/* Hotel Discovery Controls */}
                            <div className="discovery-controls-card">
                                <div className="discovery-search-row">
                                    <div className="search-input-wrapper">
                                        <Icons.Search />
                                        <input
                                            type="text"
                                            className="discovery-search-input"
                                            placeholder="Search hotel, guesthouse, or neighborhood..."
                                            value={hotelSearchQuery}
                                            onChange={(e) => setHotelSearchQuery(e.target.value)}
                                        />
                                    </div>
                                    <select
                                        className="discovery-select-dropdown"
                                        value={hotelSortBy}
                                        onChange={(e) => setHotelSortBy(e.target.value)}
                                        aria-label="Sort hotels"
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
                                            <div key={idx} className="hotel-card">
                                                {h.photo_url && (
                                                    <div className="hotel-image-header">
                                                        <img
                                                            src={h.photo_url}
                                                            alt={h.name}
                                                            className="hotel-thumb-img"
                                                            loading="lazy"
                                                            onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                                        />
                                                    </div>
                                                )}
                                                <div className="hotel-top-strip">
                                                    <span className="stars-pill">
                                                        ⭐ {h.rating ? `${h.rating} / 5` : 'Verified Stay'}
                                                        {h.review_count ? ` (${h.review_count.toLocaleString()} reviews)` : ''}
                                                    </span>
                                                    <strong className="hotel-rate-text">
                                                        {formatMoney(h.price_per_night, h.currency || trip.currency)} <small>/ night</small>
                                                    </strong>
                                                </div>
                                                {h.tier && <div className="hotel-tier-tag">{h.tier}</div>}
                                                <h3 className="hotel-title-text">{h.name}</h3>
                                                <p className="hotel-neighborhood">📍 {h.neighborhood || h.address || 'Central District'}</p>

                                                {h.total_stay_price && (
                                                    <div className="hotel-stay-total-strip">
                                                        Total for {days.length || trip.duration_days || 1} nights: <strong>{formatMoney(h.total_stay_price, h.currency || trip.currency)}</strong>
                                                        {h.taxes_and_fees ? ` (incl. ${formatMoney(h.taxes_and_fees, h.currency || trip.currency)} est. taxes)` : ''}
                                                    </div>
                                                )}

                                                <div className="amenities-chips">
                                                    {(h.amenities || []).map((amenity: string) => (
                                                        <span key={amenity} className="amenity-chip">{amenity}</span>
                                                    ))}
                                                </div>

                                                <div className="hotel-card-footer-strip">
                                                    <small className="source-meta-tag">Source: {h.source || 'Verified Directory'}</small>
                                                    <a
                                                        href={h.booking_url || `https://www.google.com/travel/hotels?q=${encodeURIComponent(h.name + ' ' + trip.destination)}`}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="button button-outline-sm"
                                                    >
                                                        <span>Check Live Availability</span>
                                                        <Icons.ExternalLink />
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
                                                <span>Load More Stays ({filteredHotels.length - displayedHotels.length} remaining)</span>
                                            </button>
                                            <small className="load-more-stats">
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
                <div className="tab-content-section" id="panel-destinations" role="tabpanel" aria-labelledby="tab-destinations">
                    <div className="section-heading-bar">
                        <div>
                            <h2>Discovered Attractions & Iconic Landmarks</h2>
                            <p className="section-subtext">Must-visit historical sites, cultural ghats, viewpoints, and temples in {trip.destination}</p>
                        </div>
                        <span className="estimate-tag">{destData.source || 'Curated, Wikipedia & OpenStreetMap'}</span>
                    </div>

                    {places.length === 0 ? (
                        <div className="empty-filter-box">
                            <p>No landmarks discovered for this destination.</p>
                        </div>
                    ) : (
                        <>
                            {/* Attraction Discovery Controls */}
                            <div className="discovery-controls-card">
                                <div className="discovery-search-row">
                                    <div className="search-input-wrapper">
                                        <Icons.Search />
                                        <input
                                            type="text"
                                            className="discovery-search-input"
                                            placeholder="Search landmark name, description, or category..."
                                            value={placeSearchQuery}
                                            onChange={(e) => setPlaceSearchQuery(e.target.value)}
                                        />
                                    </div>
                                    <select
                                        className="discovery-select-dropdown"
                                        value={placeSortBy}
                                        onChange={(e) => setPlaceSortBy(e.target.value)}
                                        aria-label="Sort attractions"
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
                                            <div key={idx} className="place-item-card">
                                                {place.photo_url && (
                                                    <div className="place-image-header">
                                                        <img
                                                            src={place.photo_url}
                                                            alt={place.name}
                                                            className="place-thumb-img"
                                                            loading="lazy"
                                                            onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                                        />
                                                    </div>
                                                )}
                                                <div className="place-top-meta-row">
                                                    <div className="place-cat-tag">{(place.category || 'Landmark').replace(/_/g, ' ').toUpperCase()}</div>
                                                    {place.distance_km !== undefined && place.distance_km !== null && (
                                                        <span className="distance-badge-pill">📍 {place.distance_km} km to center</span>
                                                    )}
                                                </div>
                                                <h3 className="place-name-title">{place.name}</h3>
                                                {place.description && <p className="place-desc">{place.description}</p>}
                                                <div className="place-meta">
                                                    <span className="place-rating-badge">{place.rating ? `⭐ ${place.rating} / 5.0` : '🏛️ Verified Landmark'}</span>
                                                    <span className="place-admission-badge">
                                                        {place.admission_fee_inr !== undefined
                                                            ? (place.admission_fee_inr === 0 ? 'Free public access' : `₹${place.admission_fee_inr} entry`)
                                                            : (place.admission_price || (place.price_level ? (place.price_level === 'Free' ? 'Free access' : `Tier ${place.price_level}`) : (place.price || 'Free admission')))}
                                                    </span>
                                                </div>
                                                <p className="place-address">📍 {place.address || trip.destination}</p>
                                                {place.opening_hours && <small className="place-hours-text"><Icons.Clock /> {place.opening_hours}</small>}
                                                <div className="place-card-footer">
                                                    <small className="source-meta-tag">Source: {place.source || 'OpenStreetMap'}</small>
                                                    <a
                                                        href={place.website || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.name + ' ' + trip.destination)}`}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="place-directions-link"
                                                    >
                                                        <span>{place.website ? 'Official Portal' : 'Directions on Map'}</span>
                                                        <Icons.ExternalLink />
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
                                                <span>Load More Places ({filteredPlaces.length - displayedPlaces.length} remaining)</span>
                                            </button>
                                            <small className="load-more-stats">
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
                <div className="tab-content-section" id="panel-map" role="tabpanel" aria-labelledby="tab-map">
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
                <div className="tab-content-section" id="panel-budget" role="tabpanel" aria-labelledby="tab-budget">
                    <div className="section-heading-bar">
                        <div>
                            <h2>Deterministic Budget Guardrails</h2>
                            <p className="section-subtext">Comprehensive itemized financial breakdown calculated by Budget Intelligence Engine</p>
                        </div>
                        <span className="estimate-tag">Decimal Calculation Engine</span>
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
                            <strong className={parseFloat(String(budgetData.remaining || 0)) < 0 ? 'text-negative' : 'text-positive'}>
                                {formatMoney(budgetData.remaining, budgetData.currency || trip.currency)}
                            </strong>
                        </div>
                        <div className="budget-kpi-box">
                            <span>Budget Health</span>
                            <strong className={`status-badge-inline ${budgetData.over_budget ? 'danger' : 'success'}`}>
                                {budgetData.over_budget ? 'OVER BUDGET' : 'WITHIN BUDGET'}
                            </strong>
                        </div>
                    </div>

                    <div className="surface-card mt-3">
                        <h3 className="budget-allocations-title">Itemized Allocations & Estimation Model</h3>
                        <div className="budget-lines-table">
                            {Object.entries(budgetItems).map(([cat, amt]) => {
                                const totalNum = parseFloat(budgetData.total || '1000') || 1
                                const amtNum = parseFloat(amt) || 0
                                const pct = Math.min(100, Math.round((amtNum / totalNum) * 100))
                                return (
                                    <div key={cat} className="budget-line-row">
                                        <div className="line-category-group">
                                            <span className="line-category">{cat.replace(/_/g, ' ').toUpperCase()}</span>
                                            <span className="line-percentage">{pct}%</span>
                                        </div>
                                        <span className="line-bar-container">
                                            <div className="line-bar-fill" style={{ width: `${pct}%` }} />
                                        </span>
                                        <strong className="line-amount">{formatMoney(amt, trip.currency)}</strong>
                                    </div>
                                )
                            })}
                        </div>
                        <div className="budget-footnotes-box">
                            <p>• <strong>Flights:</strong> {flightOffers.length > 0 ? 'Selected provider offer total' : 'Unconfigured provider (flights excluded from confirmed total)'}.</p>
                            <p>• <strong>Accommodation:</strong> Benchmark reference rates calculated for {days.length || trip.duration_days || 1} nights with 12% estimated local hospitality taxes.</p>
                            <p>• <strong>Meals & Dining:</strong> Transparent per-person daily dining model adapted to destination cost indices.</p>
                            <p>• <strong>Local Transit:</strong> Metro, licensed cab, and arrival transfer allocations.</p>
                            <p>• <strong>Safety Contingency:</strong> 12% deterministic buffer held for unexpected currency fluctuations or travel expenses.</p>
                        </div>
                    </div>
                </div>
            )}

            {/* TAB 7: Weather & Support */}
            {activeSection === 'support' && (
                <div className="tab-content-section" id="panel-support" role="tabpanel" aria-labelledby="tab-support">
                    <div className="section-heading-bar">
                        <div>
                            <h2>Weather Forecast & Support Briefing</h2>
                            <p className="section-subtext">Meteorological analysis and adaptive pre-departure packing recommendations</p>
                        </div>
                        <span className="estimate-tag">Open-Meteo High-Resolution Model</span>
                    </div>

                    {/* Current Conditions Card */}
                    {currentWeather && (
                        <div className="weather-current-hero-card">
                            <div className="weather-current-left">
                                <span className="weather-kicker">Current Destination Conditions · {trip.destination}</span>
                                <div className="weather-temp-row">
                                    <h3 className="weather-big-temp">
                                        {currentWeather.temp_c !== undefined ? `${currentWeather.temp_c}°C` : 'N/A'}
                                    </h3>
                                    {currentWeather.apparent_temp_c !== undefined && (
                                        <span className="weather-feels-like">(Feels like {currentWeather.apparent_temp_c}°C)</span>
                                    )}
                                </div>
                                <p className="weather-condition-desc">{currentWeather.condition || 'Current weather condition'}</p>
                            </div>
                            <div className="weather-current-metrics">
                                {currentWeather.wind_speed_kmh !== undefined && (
                                    <div className="metric-box">
                                        <small>Wind Speed</small>
                                        <p>{currentWeather.wind_speed_kmh} km/h</p>
                                    </div>
                                )}
                                {currentWeather.precipitation_probability !== undefined && (
                                    <div className="metric-box">
                                        <small>Precipitation</small>
                                        <p>{currentWeather.precipitation_probability}%</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {supportInfo.horizon_notice && (
                        <div className="horizon-notice-banner">
                            <Icons.Calendar />
                            <span><strong>Forecast Horizon Notice:</strong> {supportInfo.horizon_notice}</span>
                        </div>
                    )}

                    {weatherForecast.length > 0 && (
                        <div className="forecast-section-wrapper">
                            <h4 className="forecast-section-title">5-Day Meteorological Outlook</h4>
                            <div className="weather-forecast-row">
                                {weatherForecast.map((w: any, idx: number) => {
                                    const dateObj = w.date ? new Date(w.date) : null
                                    const weekday = dateObj ? dateObj.toLocaleDateString(undefined, { weekday: 'short' }) : `Day ${idx + 1}`
                                    const dateFormatted = dateObj ? dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''
                                    return (
                                        <div key={idx} className="weather-day-chip">
                                            <span className="weather-day-name">{weekday}</span>
                                            {dateFormatted && <span className="weather-day-subdate">{dateFormatted}</span>}
                                            <div className="weather-icon-indicator"><Icons.CloudSun /></div>
                                            <strong className="weather-day-temp">{w.temp_max_c ? `${w.temp_max_c}°C` : 'N/A'}</strong>
                                            <small className="weather-day-condition">{w.condition || 'Clear'}</small>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}

                    <div className="surface-card mt-3">
                        <div className="checklist-card-header">
                            <div>
                                <h3>Forecast-Adaptive Pre-Departure Checklist</h3>
                                <p className="section-subtext">
                                    Checklist dynamically adjusted based on destination climate predictions and planned activities.
                                </p>
                            </div>
                            <span className="checklist-count-tag">
                                {Object.values(checkedItems).filter(Boolean).length} / {packingChecklist.length} Checked
                            </span>
                        </div>
                        <ul className="checklist-items">
                            {packingChecklist.map((item: string, idx: number) => {
                                const isChecked = Boolean(checkedItems[idx])
                                return (
                                    <li key={idx} className={`checklist-item ${isChecked ? 'item-checked' : ''}`} onClick={() => toggleCheckItem(idx)}>
                                        <input
                                            type="checkbox"
                                            id={`chk-${idx}`}
                                            checked={isChecked}
                                            onChange={() => {}}
                                            aria-label={item}
                                        />
                                        <label htmlFor={`chk-${idx}`} onClick={(e) => e.stopPropagation()}>
                                            {item}
                                        </label>
                                    </li>
                                )
                            })}
                        </ul>
                    </div>
                </div>
            )}

            {/* TAB 8: Agent Swarm Logs */}
            {activeSection === 'agents' && (
                <div className="tab-content-section" id="panel-agents" role="tabpanel" aria-labelledby="tab-agents">
                    <div className="section-heading-bar">
                        <div>
                            <h2>Multi-Agent Autonomous Execution Logs</h2>
                            <p className="section-subtext">Live telemetry from the TravelMind 8-Agent Swarm execution pipeline</p>
                        </div>
                        <span className="estimate-tag">Orchestration DAG Status</span>
                    </div>

                    <div className="agent-logs-container">
                        <div className="agent-logs-table-header">
                            <span className="col-agent">Agent / Specialization</span>
                            <span className="col-status">Status</span>
                            <span className="col-duration">Execution Latency</span>
                            <span className="col-diagnostics">Diagnostics & Telemetry</span>
                        </div>
                        <div className="agent-logs-list">
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
                                const duration = exec?.duration_ms || 0
                                const isError = status === 'error' || status === 'failed'

                                return (
                                    <div key={name} className={`agent-log-row ${isError ? 'row-error' : 'row-ok'}`}>
                                        <div className="agent-name-cell">
                                            <span className={`status-indicator-dot dot-${status}`} />
                                            <div>
                                                <strong className="agent-title">{name.replace(/_/g, ' ').toUpperCase()}</strong>
                                                <small className="agent-sublabel">Core Swarm Node</small>
                                            </div>
                                        </div>
                                        <div className="agent-status-cell">
                                            <span className={`agent-status-tag tag-${status}`}>{status.toUpperCase()}</span>
                                        </div>
                                        <div className="agent-timing-cell">
                                            <span className="agent-duration-badge">{duration} ms</span>
                                        </div>
                                        <div className="agent-error-cell">
                                            {exec?.error ? (
                                                <span className="error-text">⚠️ {exec.error}</span>
                                            ) : (
                                                <span className="ok-text">✓ Execution verified within DAG bounds</span>
                                            )}
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* Edit / Modify Trip Modal */}
            {showEditModal && (
                <div className="modal-backdrop">
                    <div className="modal-dialog">
                        <div className="modal-header">
                            <div>
                                <span className="section-kicker">Trip Parameters</span>
                                <h3>Modify Trip & Re-Plan</h3>
                            </div>
                            <button className="close-btn" onClick={() => setShowEditModal(false)} aria-label="Close dialog">&times;</button>
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
                                <div className="date-error-alert">
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
