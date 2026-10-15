import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

type PreferencesViewProps = {
    token: string
    theme: 'dark' | 'light'
    onThemeChange: (theme: 'dark' | 'light') => void
}

export function PreferencesView({ token, theme, onThemeChange }: PreferencesViewProps) {
    const [currency, setCurrency] = useState('USD')
    const [travelPace, setTravelPace] = useState('moderate')
    const [dietary, setDietary] = useState('None')
    const [savedMsg, setSavedMsg] = useState('')
    const [isSaving, setIsSaving] = useState(false)

    useEffect(() => {
        api.preferences(token).then(prefs => {
            if (prefs.currency) setCurrency(prefs.currency)
            if (prefs.travel_pace) setTravelPace(prefs.travel_pace)
            if (prefs.dietary) setDietary(prefs.dietary)
        }).catch(() => {})
    }, [token])

    async function handleSave(e: React.FormEvent) {
        e.preventDefault()
        setIsSaving(true)
        setSavedMsg('')
        try {
            await api.savePreferences(token, {
                currency,
                travel_pace: travelPace,
                dietary,
            })
            setSavedMsg('Preferences saved successfully!')
        } catch (err: any) {
            setSavedMsg('Could not save preferences.')
        } finally {
            setIsSaving(false)
        }
    }

    return (
        <div className="preferences-view">
            <div className="section-heading-bar">
                <div>
                    <span className="section-kicker">Account Settings</span>
                    <h2>Traveler Profile & Preferences</h2>
                </div>
            </div>

            {savedMsg && <div className="success-banner mt-2">{savedMsg}</div>}

            <form onSubmit={handleSave} className="surface-card mt-3">
                <div className="form-grid two-columns">
                    <label>
                        Interface Theme
                        <select value={theme} onChange={e => onThemeChange(e.target.value as 'dark' | 'light')}>
                            <option value="dark">Dark Theme (Night Sky & Deep Slate)</option>
                            <option value="light">Light Theme (Daylight & Clean Ice)</option>
                        </select>
                    </label>

                    <label>
                        Default Currency
                        <select value={currency} onChange={e => setCurrency(e.target.value)}>
                            <option value="INR">INR (₹ - Indian Rupee)</option>
                            <option value="USD">USD ($ - US Dollar)</option>
                            <option value="EUR">EUR (€ - Euro)</option>
                            <option value="GBP">GBP (£ - British Pound)</option>
                            <option value="CAD">CAD (C$ - Canadian Dollar)</option>
                            <option value="AUD">AUD (A$ - Australian Dollar)</option>
                        </select>
                    </label>

                    <label>
                        Preferred Travel Pace
                        <select value={travelPace} onChange={e => setTravelPace(e.target.value)}>
                            <option value="relaxed">Relaxed (1-2 main activities per day)</option>
                            <option value="moderate">Moderate (Balanced morning/evening pacing)</option>
                            <option value="intensive">Intensive (Pack the maximum sights into each day)</option>
                        </select>
                    </label>

                    <label>
                        Dietary Preferences & Requirements
                        <select value={dietary} onChange={e => setDietary(e.target.value)}>
                            <option value="None">No Restrictions</option>
                            <option value="Vegetarian">Vegetarian</option>
                            <option value="Vegan">Vegan</option>
                            <option value="Halal">Halal</option>
                            <option value="Kosher">Kosher</option>
                            <option value="Gluten-Free">Gluten-Free</option>
                        </select>
                    </label>
                </div>

                <div className="mt-4">
                    <button type="submit" className="button button-primary" disabled={isSaving}>
                        {isSaving ? 'Saving Preferences...' : 'Save Settings'}
                    </button>
                </div>
            </form>
        </div>
    )
}
