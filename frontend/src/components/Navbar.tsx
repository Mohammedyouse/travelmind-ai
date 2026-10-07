import React from 'react'
import type { User, NotificationItem, SubscriptionInfo } from '../services/api'

type NavbarProps = {
    user: User | null
    activeTab: string
    setActiveTab: (tab: string) => void
    notifications: NotificationItem[]
    subscription?: SubscriptionInfo
    onOpenNotifications: () => void
    onOpenAuth: () => void
    onLogout: () => void
}

export function Navbar({
    user,
    activeTab,
    setActiveTab,
    notifications,
    subscription,
    onOpenNotifications,
    onOpenAuth,
    onLogout,
}: NavbarProps) {
    const unreadCount = notifications.filter(n => n.status === 'unread').length
    const tier = subscription?.tier || 'free'

    return (
        <header className="navbar-container">
            <div className="navbar-brand" onClick={() => setActiveTab(user ? 'dashboard' : 'landing')} role="button" tabIndex={0}>
                <div className="logo-symbol">T</div>
                <div className="logo-text">
                    <span className="logo-name">TravelMind</span>
                    <span className="logo-tag">AI / SaaS</span>
                </div>
            </div>

            <nav className="navbar-links" aria-label="Main navigation">
                {!user ? (
                    <>
                        <button className={`nav-link ${activeTab === 'landing' ? 'active' : ''}`} onClick={() => setActiveTab('landing')}>
                            Overview
                        </button>
                        <button className={`nav-link ${activeTab === 'pricing' ? 'active' : ''}`} onClick={() => setActiveTab('pricing')}>
                            Plans & Pricing
                        </button>
                    </>
                ) : (
                    <>
                        <button className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
                            Dashboard
                        </button>
                        <button className={`nav-link ${activeTab === 'plan' ? 'active' : ''}`} onClick={() => setActiveTab('plan')}>
                            Trip Planner
                        </button>
                        <button className={`nav-link ${activeTab === 'trips' ? 'active' : ''}`} onClick={() => setActiveTab('trips')}>
                            My Trips
                        </button>
                        <button className={`nav-link ${activeTab === 'assistant' ? 'active' : ''}`} onClick={() => setActiveTab('assistant')}>
                            AI Assistant
                        </button>
                        <button className={`nav-link ${activeTab === 'pricing' ? 'active' : ''}`} onClick={() => setActiveTab('pricing')}>
                            Subscription <span className={`tier-badge tier-${tier}`}>{tier.toUpperCase()}</span>
                        </button>
                        {user.role === 'admin' && (
                            <button className={`nav-link ${activeTab === 'admin' ? 'active' : ''}`} onClick={() => setActiveTab('admin')}>
                                Admin
                            </button>
                        )}
                    </>
                )}
            </nav>

            <div className="navbar-actions">
                {user ? (
                    <>
                        <button className="icon-button notif-button" onClick={onOpenNotifications} aria-label="Notifications" title="Notifications">
                            <span className="bell-icon">🔔</span>
                            {unreadCount > 0 && <span className="notif-badge">{unreadCount}</span>}
                        </button>
                        <button className={`nav-link ${activeTab === 'preferences' ? 'active' : ''}`} onClick={() => setActiveTab('preferences')} title="Settings">
                            ⚙️
                        </button>
                        <div className="user-profile-chip">
                            <span className="user-avatar">{user.full_name?.charAt(0).toUpperCase() || 'U'}</span>
                            <span className="user-name-display">{user.full_name}</span>
                        </div>
                        <button className="button button-outline-sm" onClick={onLogout}>
                            Sign Out
                        </button>
                    </>
                ) : (
                    <div className="auth-action-group">
                        <button className="button button-outline-sm" onClick={onOpenAuth}>
                            Sign In
                        </button>
                        <button className="button button-primary-sm" onClick={onOpenAuth}>
                            Get Started
                        </button>
                    </div>
                )}
            </div>
        </header>
    )
}
