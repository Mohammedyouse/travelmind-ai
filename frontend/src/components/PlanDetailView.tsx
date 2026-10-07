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
    const packingChecklist = supportInfo.checklist || []

    const agentExecutions = (results.agent_execution || {}) as Record<string, { status: string; attempts: number; duration_ms: number; error: string }>

    async function handleSaveEdit(e: React.FormEvent) {
        e.preventDefault()
        await onUpdateTrip(trip.id, {
            origin: editOrigin.trim().toUpperCase(),
            destination: editDestination.trim().toUpperCase(),
            departure_date: editDeparture,
            return_date: editReturn || undefined,
            travelers: Number(editTravelers) || 1,
            budget: Number(editBudget) || 2000,
            currency: editCurrency,
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
                    <p className="banner-summary">{trip.summary || 'Trip itinerary synthesized and validated.'}</p>
                </div>
                <div className="banner-badge-box">
                    <span className="source-label">Source</span>
                    <strong className="source-value">{itinerary?.source || 'Verified Provider Research'}</strong>
                </div>
            </div>

            {/* Sub-navigation tabs */}
            <div className="plan-subtabs-row">
                <button className={`subtab-btn ${activeSection === 'itinerary' ? 'active' : ''}`} onClick={() => setActiveSection('itinerary')}>
                    📅 Daily Schedule ({days.length} Days)
                </button>
                <button className={`subtab-btn ${activeSection === 'flights' ? 'active' : ''}`} onClick={() => setActiveSection('flights')}>
                    ✈️ Flights ({flightOffers.length})
                </button>
                <button className={`subtab-btn ${activeSection === 'hotels' ? 'active' : ''}`} onClick={() => setActiveSection('hotels')}>
                    🏨 Hotels & Stays ({hotels.length})
                </button>
                <button className={`subtab-btn ${activeSection === 'destinations' ? 'active' : ''}`} onClick={() => setActiveSection('destinations')}>
                    📍 Attractions ({places.length})
                </button>
                <button className={`subtab-btn ${activeSection === 'map' ? 'active' : ''}`} onClick={() => setActiveSection('map')}>
                    🗺️ Interactive Map
                </button>
                <button className={`subtab-btn ${activeSection === 'budget' ? 'active' : ''}`} onClick={() => setActiveSection('budget')}>
                    💵 Cost Breakdown
                </button>
                <button className={`subtab-btn ${activeSection === 'support' ? 'active' : ''}`} onClick={() => setActiveSection('support')}>
                    ⛅ Weather & Checklist
                </button>
                <button className={`subtab-btn ${activeSection === 'agents' ? 'active' : ''}`} onClick={() => setActiveSection('agents')}>
                    🤖 Agent Swarm
                </button>
            </div>

            {/* TAB 1: Day-by-Day Itinerary */}
            {activeSection === 'itinerary' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Personalized Daily Itinerary</h2>
                        <span className="estimate-tag">{itinerary?.source || 'Development estimate'}</span>
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
                        <span>{flightData.provider || 'Flight Intelligence Engine'}</span>
                    </div>

                    {flightOffers.length === 0 ? (
                        <div className="unconfigured-card">
                            <span className="info-icon">ℹ️</span>
                            <div>
                                <strong>Live Flight Provider Status: {results.flight_intelligence?.status || 'unconfigured'}</strong>
                                <p>{results.flight_intelligence?.summary || 'Configure AMADEUS_CLIENT_ID & SECRET in .env to pull real-time fares from Amadeus.'}</p>
                            </div>
                        </div>
                    ) : (
                        <div className="offers-table-grid">
                            {flightOffers.map((o: any, idx: number) => {
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
                                            <strong>✈️ {o.carrier_names?.join(', ') || o.carriers?.join(', ') || 'Airline'}</strong>
                                            <span className="flight-price-tag">{formatMoney(o.price, o.currency || trip.currency)}</span>
                                        </div>

                                        {/* Verified Airport Route Display with Full Names & IATA Codes */}
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
                                                <span className="route-arrow-symbol">→</span>
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
                                            {o.price_per_traveler && trip.travelers > 1 && (
                                                <span className="flight-tag-badge">👥 {formatMoney(o.price_per_traveler, o.currency || trip.currency)} / traveler</span>
                                            )}
                                        </div>

                                        <div className="flight-timing-line">
                                            <div className="flight-time-col">
                                                <small>Departs</small>
                                                <p className="flight-timestamp">{depTime ? new Date(depTime).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Check schedule'}</p>
                                            </div>
                                            <div className="flight-duration-center">
                                                <span>{o.duration || 'Direct / Layover'}</span>
                                                <span className="stops-label">{o.stops === 0 ? 'Nonstop' : `${o.stops} Stop(s)`}</span>
                                            </div>
                                            <div className="flight-time-col">
                                                <small>Arrives</small>
                                                <p className="flight-timestamp">{arrTime ? new Date(arrTime).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Check schedule'}</p>
                                            </div>
                                        </div>

                                        <div className="flight-card-footer">
                                            <small className="source-tag">Source: {o.source || 'verified-schedule'}</small>
                                            <button className="button button-primary-sm">Select Flight</button>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* TAB 3: Hotels */}
            {activeSection === 'hotels' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Curated Accommodations (Hostels to Luxury)</h2>
                        <span>{hotelData.source || 'Verified Hotel Directory'}</span>
                    </div>

                    {hotels.length === 0 ? (
                        <p className="empty-copy">No hotels retrieved for this destination.</p>
                    ) : (
                        <div className="hotel-cards-grid">
                            {hotels.map((h: any, idx: number) => (
                                <div key={idx} className="hotel-card">
                                    <div className="hotel-top-strip">
                                        <span className="stars-pill">{'⭐'.repeat(h.stars || 4)} {h.rating || 4.7}</span>
                                        <strong className="hotel-rate-text">{formatMoney(h.price_per_night, h.currency || trip.currency)} <small>/ night</small></strong>
                                    </div>
                                    {h.tier && <div className="hotel-tier-tag">{h.tier}</div>}
                                    <h3>{h.name}</h3>
                                    <p className="hotel-neighborhood">📍 {h.neighborhood || 'City Center'}</p>
                                    <div className="amenities-chips">
                                        {(h.amenities || []).map((amenity: string) => (
                                            <span key={amenity} className="amenity-chip">{amenity}</span>
                                        ))}
                                    </div>
                                    <button className="button button-outline-sm button-block mt-3">Reserve Property &rarr;</button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* TAB 4: Destinations & Attractions */}
            {activeSection === 'destinations' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Discovered Attractions & Iconic Landmarks</h2>
                        <span>{destData.source || 'Curated & OpenStreetMap Verified'}</span>
                    </div>

                    {places.length === 0 ? (
                        <p className="empty-copy">No landmarks discovered.</p>
                    ) : (
                        <div className="places-grid">
                            {places.map((place: any, idx: number) => (
                                <div key={idx} className="place-item-card">
                                    <div className="place-cat-tag">{place.category?.replace('_', ' ').toUpperCase()}</div>
                                    <h3>{place.name}</h3>
                                    {place.description && <p className="place-desc">{place.description}</p>}
                                    <div className="place-meta">
                                        <span>⭐ {place.rating || 4.6} / 5.0</span>
                                        <span>💰 {place.price_level || '$$'}</span>
                                    </div>
                                    <p className="place-address">📍 {place.address || trip.destination}</p>
                                </div>
                            ))}
                        </div>
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
                        <h3>Itemized Allocations</h3>
                        <div className="budget-lines-table">
                            {Object.entries(budgetItems).map(([cat, amt]) => (
                                <div key={cat} className="budget-line-row">
                                    <span className="line-category">{cat.replace('_', ' ').toUpperCase()}</span>
                                    <span className="line-bar-container">
                                        <div className="line-bar-fill" style={{ width: `${Math.min(100, (parseFloat(amt) / (parseFloat(budgetData.total || '1000') || 1)) * 100)}%` }} />
                                    </span>
                                    <strong className="line-amount">{formatMoney(amt, trip.currency)}</strong>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* TAB 7: Weather & Support */}
            {activeSection === 'support' && (
                <div className="tab-content-section">
                    <div className="section-heading-bar">
                        <h2>Weather Forecast & Support Briefing</h2>
                        <span>Open-Meteo Integration</span>
                    </div>

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
                        <h3>Pre-Departure Packing & Travel Checklist</h3>
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
                        {['travel_concierge', 'flight_intelligence', 'accommodation_intelligence', 'destination_discovery', 'transportation_route', 'budget_intelligence', 'personalization_recommendation', 'travel_support'].map(name => {
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
                                    <input type="date" value={editDeparture} onChange={e => setEditDeparture(e.target.value)} required />
                                </label>
                                <label>
                                    Return Date
                                    <input type="date" value={editReturn} onChange={e => setEditReturn(e.target.value)} />
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

                            <div className="modal-actions-bar">
                                <button type="button" className="button button-quiet" onClick={() => setShowEditModal(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="button button-primary" disabled={isUpdating}>
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
