import React, { useState, useEffect, type FormEvent } from 'react'
import { api, type TripInput } from '../services/api'

type TripWizardProps = {
    onSubmit: (input: TripInput) => Promise<void>
    onCancel: () => void
    isSubmitting: boolean
    error: string
    token?: string
}

const POPULAR_DESTINATIONS = [
    'Goa', 'Jaipur', 'Kerala', 'Manali', 'Udaipur', 'Varanasi', 'Mumbai', 'Delhi',
    'Paris', 'Tokyo', 'London', 'Lisbon', 'Dubai', 'New York', 'Rome', 'Bangkok'
]
const POPULAR_ORIGINS = ['Delhi', 'Mumbai', 'Bangalore', 'Hyderabad', 'Kolkata', 'New York', 'London', 'San Francisco']
const INTEREST_OPTIONS = ['Culture & Heritage', 'Culinary & Wine', 'Art & Museums', 'Nature & Parks', 'Architecture', 'Historic Sights', 'Local Markets', 'Scenic Viewpoints']
const TRAVEL_STYLES = ['Balanced Explorer', 'Value-Seeking & Smart', 'Comfort & Leisure', 'Paced Cultural Immersion']

export function TripWizard({ onSubmit, onCancel, isSubmitting, error, token }: TripWizardProps) {
    const [step, setStep] = useState<number>(1)

    const [origin, setOrigin] = useState('')
    const [destination, setDestination] = useState('')
    const [departureDate, setDepartureDate] = useState('')
    const [returnDate, setReturnDate] = useState('')
    const [travelers, setTravelers] = useState('2')
    const [budget, setBudget] = useState('45000')
    const [currency, setCurrency] = useState('INR')
    const [savedPreferredCurrency, setSavedPreferredCurrency] = useState<string | null>(null)
    const [dietary, setDietary] = useState<string>('None')
    const [selectedInterests, setSelectedInterests] = useState<string[]>(['Culture & Heritage', 'Culinary & Wine', 'Historic Sights'])
    const [travelStyle, setTravelStyle] = useState('Balanced Explorer')

    // Fetch user preferences on mount if token is provided
    useEffect(() => {
        if (!token) return
        api.preferences(token).then(prefs => {
            if (prefs && prefs.currency) {
                setSavedPreferredCurrency(prefs.currency)
                setCurrency(prefs.currency)
                if (prefs.currency === 'INR') {
                    setBudget('45000')
                } else {
                    setBudget('2500')
                }
            }
            if (prefs && prefs.travel_pace) {
                if (prefs.travel_pace === 'relaxed') setTravelStyle('Comfort & Leisure')
                else if (prefs.travel_pace === 'intensive') setTravelStyle('Paced Cultural Immersion')
                else if (prefs.travel_pace === 'moderate') setTravelStyle('Balanced Explorer')
            }
            if (prefs && prefs.dietary) {
                setDietary(prefs.dietary)
            }
        }).catch(() => {})
    }, [token])

    // Dynamically compute today's date in user's local timezone (YYYY-MM-DD)
    const todayStr = React.useMemo(() => {
        const d = new Date()
        const year = d.getFullYear()
        const month = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
    }, [])
    const [dateValidationMessage, setDateValidationMessage] = useState<string | null>(null)

    function handleDepartureChange(val: string) {
        setDepartureDate(val)
        if (!val) {
            setDateValidationMessage(null)
            return
        }
        if (val < todayStr) {
            setDateValidationMessage(`Departure date cannot be in the past. Earliest selectable departure date is today (${todayStr}).`)
            return
        }
        if (returnDate && val > returnDate) {
            setDateValidationMessage(`Departure date (${val}) is after selected return date (${returnDate}). Please adjust your return date.`)
            return
        }
        setDateValidationMessage(null)
    }

    function handleReturnChange(val: string) {
        setReturnDate(val)
        if (!val) {
            if (departureDate && departureDate < todayStr) {
                setDateValidationMessage(`Departure date cannot be in the past. Earliest selectable departure date is today (${todayStr}).`)
            } else {
                setDateValidationMessage(null)
            }
            return
        }
        if (departureDate && val < departureDate) {
            setDateValidationMessage(`Return date (${val}) cannot be before departure date (${departureDate}).`)
            return
        }
        setDateValidationMessage(null)
    }

    function toggleInterest(interest: string) {
        setSelectedInterests(prev =>
            prev.includes(interest) ? prev.filter(i => i !== interest) : [...prev, interest]
        )
    }

    function handleDestinationSelect(city: string) {
        setDestination(city)
        const indianCities = ['Goa', 'Jaipur', 'Kerala', 'Manali', 'Udaipur', 'Varanasi', 'Mumbai', 'Delhi']
        if (indianCities.includes(city)) {
            // Only force INR if user has not set an explicit foreign currency preference
            if (!savedPreferredCurrency || savedPreferredCurrency === 'INR') {
                setCurrency('INR')
                if (Number(budget) < 10000) {
                    setBudget('45000')
                }
            }
            if (!origin) {
                setOrigin('Delhi')
            }
        } else {
            if (currency === 'INR') {
                const targetCurr = savedPreferredCurrency || 'USD'
                setCurrency(targetCurr)
                setBudget(targetCurr === 'INR' ? '45000' : '2800')
            }
        }
    }

    async function handleFinalSubmit(e: FormEvent) {
        e.preventDefault()
        if (origin.trim().toLowerCase() === destination.trim().toLowerCase()) {
            setDateValidationMessage('Destination cannot be the same as origin. Please choose different departure and arrival locations.')
            setStep(1)
            return
        }
        if (departureDate < todayStr) {
            setDateValidationMessage(`Departure date cannot be in the past. Earliest selectable date is today (${todayStr}).`)
            setStep(2)
            return
        }
        if (returnDate && returnDate < departureDate) {
            setDateValidationMessage(`Return date (${returnDate}) cannot be before departure date (${departureDate}).`)
            setStep(2)
            return
        }
        const prefsPayload: Record<string, any> = { travel_style: travelStyle }
        if (dietary && dietary !== 'None') {
            prefsPayload.dietary = dietary
        }
        await onSubmit({
            origin: origin.trim().toUpperCase(),
            destination: destination.trim().toUpperCase(),
            departure_date: departureDate,
            return_date: returnDate || undefined,
            travelers: Number(travelers) || 1,
            budget: Number(budget) || 2000,
            currency: currency,
            interests: selectedInterests,
            preferences: prefsPayload,
            client_date: todayStr,
        })
    }

    return (
        <div className="wizard-shell">
            <div className="wizard-card">
                {/* Stepper Progress Bar */}
                <div className="wizard-progress-header">
                    <div>
                        <span className="section-kicker">Interactive Trip Studio</span>
                        <h2>Build Your Travel Itinerary</h2>
                    </div>
                    <div className="step-counter">Step {step} of 4</div>
                </div>

                <div className="stepper-dots">
                    <div className={`dot-bar ${step >= 1 ? 'completed' : ''}`} />
                    <div className={`dot-bar ${step >= 2 ? 'completed' : ''}`} />
                    <div className={`dot-bar ${step >= 3 ? 'completed' : ''}`} />
                    <div className={`dot-bar ${step >= 4 ? 'completed' : ''}`} />
                </div>

                {error && <div className="error-banner">{error}</div>}

                {/* Step 1: Origin & Destination */}
                {step === 1 && (
                    <div className="wizard-step-content">
                        <h3>1. Where are you traveling?</h3>
                        <p className="muted-text">Select popular hubs or type any city/airport in India or internationally.</p>

                        <div className="form-grid two-columns mt-3">
                            <label>
                                Departure Origin (Airport / City)
                                <input
                                    type="text"
                                    placeholder="e.g. Delhi, Mumbai, or SFO"
                                    value={origin}
                                    onChange={e => setOrigin(e.target.value)}
                                    required
                                />
                            </label>
                            <label>
                                Destination (Airport / City)
                                <input
                                    type="text"
                                    placeholder="e.g. Goa, Jaipur, or Paris"
                                    value={destination}
                                    onChange={e => setDestination(e.target.value)}
                                    required
                                />
                            </label>
                        </div>

                        <div className="quick-suggestions-box">
                            <span>Popular Origins:</span>
                            <div className="suggestion-chips mb-2">
                                {POPULAR_ORIGINS.map(city => (
                                    <button
                                        type="button"
                                        key={city}
                                        className={`chip-button ${origin.toLowerCase() === city.toLowerCase() ? 'active' : ''}`}
                                        onClick={() => setOrigin(city)}
                                    >
                                        {city}
                                    </button>
                                ))}
                            </div>
                            <span>Popular Destinations:</span>
                            <div className="suggestion-chips">
                                {POPULAR_DESTINATIONS.map(city => (
                                    <button
                                        type="button"
                                        key={city}
                                        className={`chip-button ${destination.toLowerCase() === city.toLowerCase() ? 'active' : ''}`}
                                        onClick={() => handleDestinationSelect(city)}
                                    >
                                        {city}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {origin.trim() && destination.trim() && origin.trim().toLowerCase() === destination.trim().toLowerCase() && (
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
                                <span>Destination cannot be the same as origin. Please select different departure and arrival locations.</span>
                            </div>
                        )}

                        <div className="wizard-actions-bar">
                            <button type="button" className="button button-quiet" onClick={onCancel}>
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="button button-primary"
                                disabled={!origin.trim() || !destination.trim() || (origin.trim().toLowerCase() === destination.trim().toLowerCase())}
                                onClick={() => setStep(2)}
                            >
                                Next: Travel Dates &rarr;
                            </button>
                        </div>
                    </div>
                )}

                {/* Step 2: Dates & Travelers */}
                {step === 2 && (
                    <div className="wizard-step-content">
                        <h3>2. When are you traveling and with whom?</h3>
                        <p className="muted-text">Flight searches and daily itineraries require specific travel windows.</p>

                        <div className="form-grid two-columns mt-3">
                            <label>
                                Departure Date
                                <input
                                    type="date"
                                    min={todayStr}
                                    value={departureDate}
                                    onChange={e => handleDepartureChange(e.target.value)}
                                    required
                                />
                            </label>
                            <label>
                                Return Date (Optional)
                                <input
                                    type="date"
                                    min={departureDate || todayStr}
                                    value={returnDate}
                                    onChange={e => handleReturnChange(e.target.value)}
                                />
                            </label>
                            <label>
                                Travelers (Adults)
                                <input
                                    type="number"
                                    min="1"
                                    max="20"
                                    value={travelers}
                                    onChange={e => setTravelers(e.target.value)}
                                    required
                                />
                            </label>
                        </div>

                        {dateValidationMessage && (
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
                                <span>{dateValidationMessage}</span>
                            </div>
                        )}

                        <div className="wizard-actions-bar">
                            <button type="button" className="button button-quiet" onClick={() => setStep(1)}>
                                &larr; Back
                            </button>
                            <button
                                type="button"
                                className="button button-primary"
                                disabled={!departureDate || departureDate < todayStr || Boolean(returnDate && returnDate < departureDate) || Boolean(dateValidationMessage)}
                                onClick={() => {
                                    if (departureDate < todayStr) {
                                        setDateValidationMessage(`Departure date cannot be in the past (${todayStr}).`)
                                        return
                                    }
                                    if (returnDate && returnDate < departureDate) {
                                        setDateValidationMessage(`Return date must be on or after departure date.`)
                                        return
                                    }
                                    setStep(3)
                                }}
                            >
                                Next: Financials & Budget &rarr;
                            </button>
                        </div>
                    </div>
                )}

                {/* Step 3: Budget & Currency */}
                {step === 3 && (
                    <div className="wizard-step-content">
                        <h3>3. Financial Ceiling & Currency</h3>
                        <p className="muted-text">Our deterministic budget engine allocates costs and preserves a 12% safety contingency.</p>

                        <div className="form-grid two-columns mt-3">
                            <label>
                                Total Trip Budget
                                <input
                                    type="number"
                                    min="100"
                                    step="50"
                                    placeholder="e.g. 2500"
                                    value={budget}
                                    onChange={e => setBudget(e.target.value)}
                                    required
                                />
                            </label>
                            <label>
                                Preferred Currency
                                <select value={currency} onChange={e => {
                                    const nextCurr = e.target.value
                                    setCurrency(nextCurr)
                                    if (nextCurr === 'INR' && Number(budget) < 10000) {
                                        setBudget('45000')
                                    } else if (nextCurr !== 'INR' && Number(budget) > 10000) {
                                        setBudget('2500')
                                    }
                                }}>
                                    <option value="INR">INR (₹ - Indian Rupee)</option>
                                    <option value="USD">USD ($ - US Dollar)</option>
                                    <option value="EUR">EUR (€ - Euro)</option>
                                    <option value="GBP">GBP (£ - British Pound)</option>
                                    <option value="CAD">CAD (C$ - Canadian Dollar)</option>
                                    <option value="AUD">AUD (A$ - Australian Dollar)</option>
                                </select>
                            </label>
                        </div>

                        <div className="budget-preview-box">
                            <div className="preview-line">
                                <span>Estimated Flight Reserve:</span>
                                <strong>~{currency === 'INR' ? '₹' : currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : '$'}{(Number(budget) * 0.30).toLocaleString()} {currency}</strong>
                            </div>
                            <div className="preview-line">
                                <span>Estimated Hotel Reserve:</span>
                                <strong>~{currency === 'INR' ? '₹' : currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : '$'}{(Number(budget) * 0.35).toLocaleString()} {currency}</strong>
                            </div>
                            <div className="preview-line">
                                <span>Dining & Activities:</span>
                                <strong>~{currency === 'INR' ? '₹' : currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : '$'}{(Number(budget) * 0.35).toLocaleString()} {currency}</strong>
                            </div>
                            <div className="preview-line contingency-line">
                                <span>12% Contingency Safety Buffer Included:</span>
                                <strong>✓ Active</strong>
                            </div>
                        </div>

                        <div className="wizard-actions-bar">
                            <button type="button" className="button button-quiet" onClick={() => setStep(2)}>
                                &larr; Back
                            </button>
                            <button
                                type="button"
                                className="button button-primary"
                                disabled={!budget || Number(budget) <= 0}
                                onClick={() => setStep(4)}
                            >
                                Next: Preferences & Style &rarr;
                            </button>
                        </div>
                    </div>
                )}

                {/* Step 4: Interests & Travel Style */}
                {step === 4 && (
                    <form onSubmit={handleFinalSubmit} className="wizard-step-content">
                        <h3>4. Personalize Your Experiences</h3>
                        <p className="muted-text">Select your interests to guide our OpenStreetMap discovery and recommendation algorithms.</p>

                        <div className="interests-grid mt-3">
                            {INTEREST_OPTIONS.map(interest => {
                                const isSelected = selectedInterests.includes(interest)
                                return (
                                    <button
                                        type="button"
                                        key={interest}
                                        className={`interest-tag-button ${isSelected ? 'selected' : ''}`}
                                        onClick={() => toggleInterest(interest)}
                                    >
                                        {isSelected ? '✓ ' : '+ '} {interest}
                                    </button>
                                )
                            })}
                        </div>

                        <div className="travel-style-group mt-3">
                            <label>Travel Pace & Style</label>
                            <div className="style-chips-row">
                                {TRAVEL_STYLES.map(style => (
                                    <button
                                        type="button"
                                        key={style}
                                        className={`chip-button ${travelStyle === style ? 'active-chip' : ''}`}
                                        onClick={() => setTravelStyle(style)}
                                    >
                                        {style}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="wizard-actions-bar mt-4">
                            <button type="button" className="button button-quiet" onClick={() => setStep(3)}>
                                &larr; Back
                            </button>
                            <button
                                type="submit"
                                className="button button-primary button-lg"
                                disabled={isSubmitting}
                            >
                                {isSubmitting ? 'Running 8-Agent Swarm...' : 'Generate Verified Plan ⚡'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    )
}
