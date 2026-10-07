import React, { useEffect, useState } from 'react'
import { api, type NotificationItem, type SubscriptionInfo, type TripInput, type TripRecord } from './services/api'
import { useAuth } from './stores/AuthContext'

import { Navbar } from './components/Navbar'
import { LandingPage } from './components/LandingPage'
import { DashboardView } from './components/DashboardView'
import { TripWizard } from './components/TripWizard'
import { PlanDetailView } from './components/PlanDetailView'
import { SavedTripsView } from './components/SavedTripsView'
import { AssistantChat } from './components/AssistantChat'
import { SubscriptionsView } from './components/SubscriptionsView'
import { PreferencesView } from './components/PreferencesView'
import { NotificationsModal } from './components/NotificationsModal'
import { AdminView } from './components/AdminView'

export default function App() {
    const { user, token, isRestoring, login, register, logout, restoreMessage } = useAuth()

    // Navigation & View State
    const [activeTab, setActiveTab] = useState<string>('landing')
    const [showAuthModal, setShowAuthModal] = useState<boolean>(false)
    const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
    const [showNotifModal, setShowNotifModal] = useState<boolean>(false)

    // Data State
    const [trips, setTrips] = useState<TripRecord[]>([])
    const [selectedTrip, setSelectedTrip] = useState<TripRecord | null>(null)
    const [notifications, setNotifications] = useState<NotificationItem[]>([])
    const [subscription, setSubscription] = useState<SubscriptionInfo | undefined>(undefined)

    // Form / Action loading states
    const [isSubmittingTrip, setIsSubmittingTrip] = useState<boolean>(false)
    const [isUpdatingTrip, setIsUpdatingTrip] = useState<boolean>(false)
    const [isUpgradingSub, setIsUpgradingSub] = useState<boolean>(false)
    const [errorMsg, setErrorMsg] = useState<string>('')
    const [noticeMsg, setNoticeMsg] = useState<string>('')

    // Auth Form State
    const [authEmail, setAuthEmail] = useState('')
    const [authPassword, setAuthPassword] = useState('')
    const [authFullName, setAuthFullName] = useState('')
    const [authPending, setAuthPending] = useState(false)
    const [authError, setAuthError] = useState('')

    // Fetch initial user data on login
    useEffect(() => {
        if (!token || !user) {
            setActiveTab('landing')
            return
        }

        // Set default logged in view to dashboard
        setActiveTab('dashboard')

        // Fetch user trips
        api.trips(token).then(savedTrips => {
            setTrips(savedTrips)
            if (savedTrips.length > 0 && !selectedTrip) {
                // optionally default selected trip
            }
        }).catch(() => {})

        // Fetch notifications
        api.notifications(token).then(notifs => {
            setNotifications(notifs)
        }).catch(() => {})

        // Fetch subscription
        api.currentSubscription(token).then(sub => {
            setSubscription(sub)
        }).catch(() => {})
    }, [token, user])

    // Auth Submit handler
    async function handleAuthSubmit(e: React.FormEvent) {
        e.preventDefault()
        setAuthPending(true)
        setAuthError('')
        try {
            if (authMode === 'register') {
                await register(authEmail, authPassword, authFullName)
            } else {
                await login(authEmail, authPassword)
            }
            setShowAuthModal(false)
            setAuthEmail('')
            setAuthPassword('')
            setAuthFullName('')
        } catch (caught: any) {
            setAuthError(caught.message || 'Authentication failed. Please verify credentials.')
        } finally {
            setAuthPending(false)
        }
    }

    // Create Trip Handler
    async function handleCreateTrip(input: TripInput) {
        if (!token) {
            setShowAuthModal(true)
            return
        }
        setIsSubmittingTrip(true)
        setErrorMsg('')
        setNoticeMsg('')
        try {
            const created = await api.createTrip(token, input)
            setTrips(prev => [created, ...prev])
            setSelectedTrip(created)
            setNoticeMsg('Trip plan generated and saved successfully!')
            setActiveTab('detail')
        } catch (err: any) {
            setErrorMsg(err.message || 'Could not build trip plan.')
        } finally {
            setIsSubmittingTrip(false)
        }
    }

    // Update Trip Handler
    async function handleUpdateTrip(id: string, updates: Partial<TripInput>) {
        if (!token) return
        setIsUpdatingTrip(true)
        setErrorMsg('')
        try {
            const updated = await api.updateTrip(token, id, updates)
            setSelectedTrip(updated)
            setTrips(prev => prev.map(t => (t.id === id ? updated : t)))
            setNoticeMsg('Trip changes saved and recalculated.')
        } catch (err: any) {
            setErrorMsg(err.message || 'Could not update trip.')
        } finally {
            setIsUpdatingTrip(false)
        }
    }

    // Delete Trip Handler
    async function handleDeleteTrip(id: string) {
        if (!token) return
        if (!window.confirm('Are you sure you want to delete this trip plan?')) return
        try {
            await api.deleteTrip(token, id)
            setTrips(prev => prev.filter(t => t.id !== id))
            if (selectedTrip?.id === id) {
                setSelectedTrip(null)
                setActiveTab('trips')
            }
            setNoticeMsg('Trip plan deleted.')
        } catch (err: any) {
            setErrorMsg(err.message || 'Could not delete trip.')
        }
    }

    // Export HTML Handler
    function handleExportHtml(id: string) {
        const url = api.exportTripUrl(id, 'html')
        window.open(url, '_blank')
    }

    // Upgrade Subscription Handler
    async function handleUpgradeSubscription(tier: string) {
        if (!token) {
            setShowAuthModal(true)
            return
        }
        setIsUpgradingSub(true)
        try {
            const updated = await api.upgradeSubscription(token, tier)
            setSubscription(updated)
            setNoticeMsg(`Your account is now upgraded to ${tier.toUpperCase()}!`)
        } finally {
            setIsUpgradingSub(false)
        }
    }

    // Mark notification read
    async function handleMarkNotificationRead(id: string) {
        if (!token) return
        await api.markNotificationRead(token, id)
        setNotifications(prev => prev.map(n => (n.id === id ? { ...n, status: 'read' } : n)))
    }

    if (isRestoring) {
        return (
            <main className="restore-screen">
                <span className="loading-mark">T</span>
                <p>Restoring TravelMind AI workspace...</p>
            </main>
        )
    }

    return (
        <div className="app-shell">
            {/* Navigation Header */}
            <Navbar
                user={user}
                activeTab={activeTab}
                setActiveTab={tab => {
                    setActiveTab(tab)
                    if (tab !== 'detail') setSelectedTrip(null)
                }}
                notifications={notifications}
                subscription={subscription}
                onOpenNotifications={() => setShowNotifModal(true)}
                onOpenAuth={() => {
                    setAuthMode('login')
                    setShowAuthModal(true)
                }}
                onLogout={() => {
                    logout()
                    setActiveTab('landing')
                }}
            />

            {/* Global Notice / Error Messages */}
            {noticeMsg && (
                <div className="global-banner success-banner" onClick={() => setNoticeMsg('')}>
                    <span>✓ {noticeMsg}</span>
                    <button className="dismiss-btn">&times;</button>
                </div>
            )}
            {errorMsg && (
                <div className="global-banner error-banner" onClick={() => setErrorMsg('')}>
                    <span>⚠️ {errorMsg}</span>
                    <button className="dismiss-btn">&times;</button>
                </div>
            )}

            {/* Main Application Body */}
            <main className="main-viewport">
                {/* 1. Landing Page */}
                {activeTab === 'landing' && (
                    <LandingPage
                        onStartPlanning={() => {
                            if (user) setActiveTab('plan')
                            else setShowAuthModal(true)
                        }}
                        onViewPricing={() => setActiveTab('pricing')}
                    />
                )}

                {/* 2. User Dashboard */}
                {activeTab === 'dashboard' && user && (
                    <DashboardView
                        user={user}
                        trips={trips}
                        notifications={notifications}
                        subscription={subscription}
                        onSelectTrip={t => {
                            setSelectedTrip(t)
                            setActiveTab('detail')
                        }}
                        onStartPlanning={() => setActiveTab('plan')}
                        onOpenAssistant={() => setActiveTab('assistant')}
                        onUpgrade={() => setActiveTab('pricing')}
                    />
                )}

                {/* 3. Trip Planner Wizard */}
                {activeTab === 'plan' && (
                    <TripWizard
                        onSubmit={handleCreateTrip}
                        onCancel={() => setActiveTab(user ? 'dashboard' : 'landing')}
                        isSubmitting={isSubmittingTrip}
                        error={errorMsg}
                    />
                )}

                {/* 4. Single Trip Detail View (8 sub-tabs) */}
                {activeTab === 'detail' && selectedTrip && (
                    <PlanDetailView
                        trip={selectedTrip}
                        onUpdateTrip={handleUpdateTrip}
                        onDeleteTrip={handleDeleteTrip}
                        onExportHtml={handleExportHtml}
                        onClose={() => setActiveTab('trips')}
                        isUpdating={isUpdatingTrip}
                    />
                )}

                {/* 5. Saved Trips Library */}
                {activeTab === 'trips' && user && (
                    <SavedTripsView
                        trips={trips}
                        onSelectTrip={t => {
                            setSelectedTrip(t)
                            setActiveTab('detail')
                        }}
                        onDeleteTrip={handleDeleteTrip}
                        onExportTrip={handleExportHtml}
                        onCreateNew={() => setActiveTab('plan')}
                    />
                )}

                {/* 6. AI Travel Concierge Assistant */}
                {activeTab === 'assistant' && user && token && (
                    <div className="view-container">
                        <AssistantChat token={token} tripId={selectedTrip?.id || trips[0]?.id} />
                    </div>
                )}

                {/* 7. Subscriptions & Pricing */}
                {activeTab === 'pricing' && (
                    <SubscriptionsView
                        subscription={subscription}
                        onUpgrade={handleUpgradeSubscription}
                        isUpgrading={isUpgradingSub}
                    />
                )}

                {/* 8. User Preferences */}
                {activeTab === 'preferences' && user && token && (
                    <div className="view-container">
                        <PreferencesView token={token} />
                    </div>
                )}

                {/* 9. Admin Dashboard */}
                {activeTab === 'admin' && user && token && user.role === 'admin' && (
                    <div className="view-container">
                        <AdminView token={token} />
                    </div>
                )}
            </main>

            {/* Authentication Modal */}
            {showAuthModal && (
                <div className="modal-backdrop" onClick={() => setShowAuthModal(false)}>
                    <div className="modal-dialog auth-modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <div>
                                <span className="section-kicker">TravelMind Studio</span>
                                <h3>{authMode === 'login' ? 'Welcome Back' : 'Create Your Account'}</h3>
                            </div>
                            <button className="close-btn" onClick={() => setShowAuthModal(false)}>&times;</button>
                        </div>

                        {restoreMessage && <div className="notice-banner">{restoreMessage}</div>}
                        {authError && <div className="error-banner">{authError}</div>}

                        <form onSubmit={handleAuthSubmit} className="modal-form">
                            {authMode === 'register' && (
                                <label>
                                    Full Name
                                    <input
                                        type="text"
                                        placeholder="e.g. Jane Doe"
                                        value={authFullName}
                                        onChange={e => setAuthFullName(e.target.value)}
                                        required
                                    />
                                </label>
                            )}

                            <label>
                                Email Address
                                <input
                                    type="email"
                                    placeholder="name@example.com"
                                    value={authEmail}
                                    onChange={e => setAuthEmail(e.target.value)}
                                    required
                                />
                            </label>

                            <label>
                                Password
                                <input
                                    type="password"
                                    placeholder="••••••••"
                                    minLength={8}
                                    value={authPassword}
                                    onChange={e => setAuthPassword(e.target.value)}
                                    required
                                />
                            </label>

                            <button className="button button-primary button-block mt-3" disabled={authPending}>
                                {authPending ? 'Authenticating...' : authMode === 'login' ? 'Sign In' : 'Create Free Account'}
                            </button>

                            <button
                                type="button"
                                className="text-button-link mt-3 center-block"
                                onClick={() => {
                                    setAuthMode(authMode === 'login' ? 'register' : 'login')
                                    setAuthError('')
                                }}
                            >
                                {authMode === 'login' ? 'New traveler? Create an account' : 'Already have an account? Sign in'}
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {/* Notifications Drawer Modal */}
            {showNotifModal && (
                <NotificationsModal
                    notifications={notifications}
                    onMarkRead={handleMarkNotificationRead}
                    onClose={() => setShowNotifModal(false)}
                />
            )}
        </div>
    )
}