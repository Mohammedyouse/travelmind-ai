import React, { useState } from 'react'
import type { SubscriptionInfo } from '../services/api'

type SubscriptionsViewProps = {
    subscription?: SubscriptionInfo
    onUpgrade: (tier: string) => Promise<void>
    isUpgrading: boolean
}

export function SubscriptionsView({ subscription, onUpgrade, isUpgrading }: SubscriptionsViewProps) {
    const currentTier = subscription?.tier || 'free'
    const [upgradeMessage, setUpgradeMessage] = useState('')

    async function handleUpgradeClick(tier: string) {
        if (tier === currentTier) return
        setUpgradeMessage('')
        try {
            await onUpgrade(tier)
            setUpgradeMessage(`Successfully switched to the ${tier.toUpperCase()} plan!`)
        } catch (err: any) {
            setUpgradeMessage(err.message || 'Upgrade failed.')
        }
    }

    return (
        <div className="pricing-view-container">
            <div className="section-header-center">
                <span className="section-kicker">Transparent SaaS Pricing</span>
                <h2>Choose the Right Plan for Your Journeys</h2>
                <p>From solo leisure trips to high-frequency corporate and luxury expeditions.</p>
                {upgradeMessage && <div className="success-banner mt-3">{upgradeMessage}</div>}
            </div>

            <div className="pricing-cards-grid">
                {/* Free Tier */}
                <div className={`pricing-card ${currentTier === 'free' ? 'active-tier' : ''}`}>
                    {currentTier === 'free' && <div className="current-tier-tag">Current Plan</div>}
                    <h3 className="plan-name">Traveler Free</h3>
                    <div className="plan-price">
                        <strong>$0</strong>
                        <span>/ forever</span>
                    </div>
                    <p className="plan-desc">Perfect for planning occasional personal weekend getaways.</p>
                    <ul className="plan-features-list">
                        <li>✓ Up to 3 saved trip itineraries</li>
                        <li>✓ OpenStreetMap verified POIs</li>
                        <li>✓ Open-Meteo live weather forecasts</li>
                        <li>✓ Frankfurter live FX currency sync</li>
                        <li>✓ Standard day-by-day outline</li>
                    </ul>
                    <button
                        className="button button-outline button-block"
                        disabled={currentTier === 'free'}
                    >
                        {currentTier === 'free' ? 'Current Plan' : 'Downgrade to Free'}
                    </button>
                </div>

                {/* Pro Tier */}
                <div className={`pricing-card highlighted-card ${currentTier === 'pro' ? 'active-tier' : ''}`}>
                    <div className="popular-ribbon">Most Popular</div>
                    {currentTier === 'pro' && <div className="current-tier-tag">Current Plan</div>}
                    <h3 className="plan-name">TravelMind Pro</h3>
                    <div className="plan-price">
                        <strong>$14.99</strong>
                        <span>/ month</span>
                    </div>
                    <p className="plan-desc">For frequent flyers seeking live provider integration and AI synthesis.</p>
                    <ul className="plan-features-list">
                        <li>✓ <strong>Unlimited saved journeys</strong></li>
                        <li>✓ <strong>Amadeus live flight search</strong></li>
                        <li>✓ <strong>Curated boutique hotel directories</strong></li>
                        <li>✓ <strong>Gemini 2.0 Flash AI itinerary synthesis</strong></li>
                        <li>✓ <strong>Full HTML & PDF printable export</strong></li>
                        <li>✓ Decimal budget engine with 12% contingency</li>
                    </ul>
                    <button
                        className="button button-primary button-block"
                        onClick={() => handleUpgradeClick('pro')}
                        disabled={currentTier === 'pro' || isUpgrading}
                    >
                        {currentTier === 'pro' ? 'Active Plan' : isUpgrading ? 'Upgrading...' : 'Upgrade to Pro'}
                    </button>
                </div>

                {/* Enterprise Tier */}
                <div className={`pricing-card ${currentTier === 'enterprise' ? 'active-tier' : ''}`}>
                    {currentTier === 'enterprise' && <div className="current-tier-tag">Current Plan</div>}
                    <h3 className="plan-name">Concierge Elite</h3>
                    <div className="plan-price">
                        <strong>$49.99</strong>
                        <span>/ month</span>
                    </div>
                    <p className="plan-desc">The ultimate automated travel experience with WhatsApp concierge.</p>
                    <ul className="plan-features-list">
                        <li>✓ <strong>Everything in TravelMind Pro</strong></li>
                        <li>✓ <strong>WhatsApp Personal Travel Concierge</strong></li>
                        <li>✓ <strong>n8n event-driven travel reminders</strong></li>
                        <li>✓ Priority queue on all provider searches</li>
                        <li>✓ Multi-city routing & transit optimization</li>
                        <li>✓ 24/7 dedicated support</li>
                    </ul>
                    <button
                        className="button button-outline button-block"
                        onClick={() => handleUpgradeClick('enterprise')}
                        disabled={currentTier === 'enterprise' || isUpgrading}
                    >
                        {currentTier === 'enterprise' ? 'Active Plan' : isUpgrading ? 'Upgrading...' : 'Get Concierge Elite'}
                    </button>
                </div>
            </div>
        </div>
    )
}
