import React from 'react'
import type { TripRecord, NotificationItem, SubscriptionInfo, User } from '../services/api'

type DashboardViewProps = {
    user: User
    trips: TripRecord[]
    notifications: NotificationItem[]
    subscription?: SubscriptionInfo
    onSelectTrip: (trip: TripRecord) => void
    onStartPlanning: () => void
    onOpenAssistant: () => void
    onUpgrade: () => void
}

export function DashboardView({
    user,
    trips,
    notifications,
    subscription,
    onSelectTrip,
    onStartPlanning,
    onOpenAssistant,
    onUpgrade,
}: DashboardViewProps) {
    const tier = subscription?.tier || 'free'
    const tripLimit = subscription?.limits?.trip_limit || 3
    const tripsUsed = trips.length
    const quotaPct = Math.min(100, Math.round((tripsUsed / tripLimit) * 100))

    const totalBudget = trips.reduce((acc, t) => acc + (t.budget || 0), 0)
    const activeTrip = trips.length > 0 ? trips[0] : null

    return (
        <div className="dashboard-container">
            {/* Header greeting */}
            <div className="dashboard-header">
                <div>
                    <span className="section-kicker">Traveler Command Desk</span>
                    <h1>Welcome back, {user.full_name}</h1>
                    <p>Here is the overview of your journeys, budget guardrails, and active planning agents.</p>
                </div>
                <div className="dashboard-cta-row">
                    <button className="button button-primary" onClick={onStartPlanning}>
                        + Plan New Journey
                    </button>
                    <button className="button button-glass" onClick={onOpenAssistant}>
                        💬 AI Concierge
                    </button>
                </div>
            </div>

            {/* Metrics cards */}
            <div className="kpi-grid">
                <div className="kpi-card">
                    <span className="kpi-icon">🌍</span>
                    <div className="kpi-info">
                        <span className="kpi-label">Saved Journeys</span>
                        <strong className="kpi-value">{trips.length}</strong>
                    </div>
                </div>

                <div className="kpi-card">
                    <span className="kpi-icon">💵</span>
                    <div className="kpi-info">
                        <span className="kpi-label">Total Planned Budget</span>
                        <strong className="kpi-value">${totalBudget.toLocaleString()}</strong>
                    </div>
                </div>

                <div className="kpi-card">
                    <span className="kpi-icon">⚡</span>
                    <div className="kpi-info">
                        <span className="kpi-label">Active Plan Tier</span>
                        <strong className="kpi-value">{tier.toUpperCase()}</strong>
                    </div>
                </div>

                <div className="kpi-card">
                    <span className="kpi-icon">📊</span>
                    <div className="kpi-info">
                        <div className="quota-header">
                            <span className="kpi-label">Quota Usage</span>
                            <span className="quota-text">{tripsUsed} / {tripLimit === 1000 ? '∞' : tripLimit} trips</span>
                        </div>
                        <div className="progress-bar-bg">
                            <div className="progress-bar-fill" style={{ width: `${quotaPct}%` }} />
                        </div>
                        {tripsUsed >= tripLimit && (
                            <button className="text-button-link" onClick={onUpgrade}>Upgrade to Pro &rarr;</button>
                        )}
                    </div>
                </div>
            </div>

            {/* Main content grid */}
            <div className="dashboard-grid">
                {/* Left Column: Recent Trips */}
                <div className="dashboard-main-col">
                    <div className="section-heading-bar">
                        <h2>Your Active Journeys</h2>
                        <span>{trips.length} total</span>
                    </div>

                    {trips.length === 0 ? (
                        <div className="empty-dashboard-card">
                            <span className="empty-icon">🗺️</span>
                            <h3>No trips planned yet</h3>
                            <p>Launch the trip wizard to research live flights, hotels, attractions, and generate your first Gemini itinerary.</p>
                            <button className="button button-primary" onClick={onStartPlanning}>
                                Create Your First Trip
                            </button>
                        </div>
                    ) : (
                        <div className="trip-cards-grid">
                            {trips.map(trip => (
                                <div key={trip.id} className="trip-overview-card" onClick={() => onSelectTrip(trip)}>
                                    <div className="card-top-row">
                                        <span className="route-tag">
                                            {trip.origin} &rarr; {trip.destination}
                                        </span>
                                        <span className={`status-pill status-${trip.status}`}>
                                            {trip.status}
                                        </span>
                                    </div>
                                    <h3 className="trip-destination-title">{trip.destination}</h3>
                                    <p className="trip-dates-text">
                                        📅 {trip.departure_date || 'Flexible'} {trip.return_date ? `to ${trip.return_date}` : ''}
                                    </p>
                                    <div className="trip-card-footer">
                                        <span>👥 {trip.travelers} traveler{trip.travelers > 1 ? 's' : ''}</span>
                                        <strong className="trip-budget-badge">
                                            {trip.budget ? `${trip.budget.toLocaleString()} ${trip.currency}` : 'Flexible'}
                                        </strong>
                                    </div>
                                    <button className="button button-outline-sm button-block mt-2">
                                        View Full Plan & Itinerary &rarr;
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Right Column: Alerts & AI Health */}
                <div className="dashboard-side-col">
                    <div className="surface-card">
                        <div className="section-heading-bar">
                            <h3>Trip Alerts & Updates</h3>
                            <span>🔔</span>
                        </div>
                        {notifications.length === 0 ? (
                            <p className="muted-text">No active alerts at this moment.</p>
                        ) : (
                            <ul className="notif-mini-list">
                                {notifications.slice(0, 4).map(n => (
                                    <li key={n.id} className={`notif-mini-item ${n.status}`}>
                                        <strong>{n.title}</strong>
                                        <p>{n.message}</p>
                                        <small>{new Date(n.created_at).toLocaleDateString()}</small>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    <div className="surface-card mt-4">
                        <div className="section-heading-bar">
                            <h3>Autonomous Agent Swarm</h3>
                            <span className="status-dot-green" />
                        </div>
                        <ul className="agent-status-mini-list">
                            <li><span>Travel Concierge</span><small>Online</small></li>
                            <li><span>Flight Intelligence</span><small>Amadeus Ready</small></li>
                            <li><span>Accommodation Intelligence</span><small>Live Directory</small></li>
                            <li><span>Destination Discovery</span><small>OSM Geocoded</small></li>
                            <li><span>Transportation & Route</span><small>Online</small></li>
                            <li><span>Budget Intelligence</span><small>Decimal Engine</small></li>
                            <li><span>Personalization Agent</span><small>ML Scorer</small></li>
                            <li><span>Travel Support Agent</span><small>Open-Meteo Sync</small></li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    )
}
