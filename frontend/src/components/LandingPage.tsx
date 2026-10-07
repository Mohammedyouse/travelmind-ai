import React from 'react'

type LandingPageProps = {
    onStartPlanning: () => void
    onViewPricing: () => void
}

export function LandingPage({ onStartPlanning, onViewPricing }: LandingPageProps) {
    return (
        <div className="landing-container">
            {/* Hero Section */}
            <section className="hero-section">
                <div className="hero-badge">
                    <span className="badge-glow" />
                    <span>Next-Generation Travel SaaS · Multi-Agent Swarm</span>
                </div>
                <h1 className="hero-title">
                    Intelligent Travel Planning, <br />
                    <span className="gradient-text">Grounded in Verified Reality.</span>
                </h1>
                <p className="hero-subtitle">
                    TravelMind AI orchestrates 8 specialized autonomous AI agents, queries live Amadeus flight feeds,
                    discovers real boutique stays and landmarks, and synthesizes structured daily itineraries with Gemini.
                </p>

                <div className="hero-cta-group">
                    <button className="button button-primary button-lg" onClick={onStartPlanning}>
                        Start Planning Free <span>&rarr;</span>
                    </button>
                    <button className="button button-glass button-lg" onClick={onViewPricing}>
                        Explore Subscription Plans
                    </button>
                </div>

                <div className="hero-stats-row">
                    <div className="stat-card">
                        <span className="stat-number">8</span>
                        <span className="stat-label">Specialist AI Agents</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-number">100%</span>
                        <span className="stat-label">Verified Providers</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-number">12%</span>
                        <span className="stat-label">Buffer Guardrail</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-number">11</span>
                        <span className="stat-label">n8n Workflows</span>
                    </div>
                </div>
            </section>

            {/* How It Works Section */}
            <section className="section-block">
                <div className="section-header-center">
                    <span className="section-kicker">Autonomous Intelligence Pipeline</span>
                    <h2>How TravelMind AI Plans Your Journey</h2>
                    <p>Unlike generic chatbots that hallucinate fake flights and closed restaurants, TravelMind executes a rigorous four-stage engineering pipeline.</p>
                </div>

                <div className="pipeline-grid">
                    <div className="pipeline-card">
                        <div className="step-circle">01</div>
                        <h3>Intake & Constraints</h3>
                        <p>The Travel Concierge validates your origin, destination, dates, party size, budget, and travel style.</p>
                    </div>
                    <div className="pipeline-card">
                        <div className="step-circle">02</div>
                        <h3>Multi-Agent Research</h3>
                        <p>Specialized agents concurrently search Amadeus flights, discover verified hotels, geocode attractions, and poll live weather.</p>
                    </div>
                    <div className="pipeline-card">
                        <div className="step-circle">03</div>
                        <h3>Gemini AI Synthesis</h3>
                        <p>Gemini 2.0 Flash ingests the retrieved real-world context and drafts an optimized morning, afternoon, and evening schedule.</p>
                    </div>
                    <div className="pipeline-card">
                        <div className="step-circle">04</div>
                        <h3>Deterministic Guardrails</h3>
                        <p>Decimal-based financial math calculates exact costs, validates budget limits, and triggers n8n workflow automations.</p>
                    </div>
                </div>
            </section>

            {/* Feature Showcase Grid */}
            <section className="section-block alt-bg">
                <div className="section-header-center">
                    <span className="section-kicker">Enterprise Capabilities</span>
                    <h2>Complete AI Travel Ecosystem</h2>
                </div>

                <div className="features-grid">
                    <div className="feature-box">
                        <div className="feature-icon">✈️</div>
                        <h3>Amadeus Flight Intelligence</h3>
                        <p>Real-time flight search with carrier names, flight segments, layover analysis, and honest error handling.</p>
                    </div>
                    <div className="feature-box">
                        <div className="feature-icon">🏨</div>
                        <h3>Curated Stays & Hotels</h3>
                        <p>Verified boutique accommodations, star ratings, nightly rates, and neighborhood proximity analysis.</p>
                    </div>
                    <div className="feature-box">
                        <div className="feature-icon">🗺️</div>
                        <h3>OpenStreetMap Discovery</h3>
                        <p>Real coordinates, architectural landmarks, scenic viewpoints, and local dining spots discovered without fake ratings.</p>
                    </div>
                    <div className="feature-box">
                        <div className="feature-icon">⛅</div>
                        <h3>Live Open-Meteo Weather</h3>
                        <p>Live destination forecasts drive proactive packing checklists, rain alerts, and weather-optimized activity scheduling.</p>
                    </div>
                    <div className="feature-box">
                        <div className="feature-icon">💱</div>
                        <h3>Frankfurter Currency Sync</h3>
                        <p>Live foreign exchange rates calculate transparent pricing across USD, EUR, GBP, CAD, AUD, and more.</p>
                    </div>
                    <div className="feature-box">
                        <div className="feature-icon">⚡</div>
                        <h3>n8n Operational Workflows</h3>
                        <p>11 production workflows automate travel orchestration, scheduled reminders, WhatsApp concierge, and recovery paths.</p>
                    </div>
                </div>
            </section>

            {/* Testimonials */}
            <section className="section-block">
                <div className="section-header-center">
                    <span className="section-kicker">Traveler Feedback</span>
                    <h2>Trusted by Global Explorers</h2>
                </div>

                <div className="testimonials-grid">
                    <div className="testimonial-card">
                        <p>“The budget breakdown was accurate down to the cent. No surprise fees and the itinerary clustered sights so we walked without getting exhausted.”</p>
                        <div className="testimonial-author">
                            <strong>Elena Rostova</strong>
                            <span>Lisbon Cultural Explorer</span>
                        </div>
                    </div>
                    <div className="testimonial-card">
                        <p>“The flight comparison showed real airlines and departure times instead of generic AI nonsense. Saved me 3 hours of planning time.”</p>
                        <div className="testimonial-author">
                            <strong>Marcus Vance</strong>
                            <span>Tokyo Solo Traveler</span>
                        </div>
                    </div>
                    <div className="testimonial-card">
                        <p>“The weather-tailored packing tips reminded us to bring light rain jackets for Paris, and the daily morning/evening slots were perfectly paced.”</p>
                        <div className="testimonial-author">
                            <strong>Sarah & David Chen</strong>
                            <span>Family Vacationers</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Banner */}
            <section className="cta-banner">
                <div className="cta-content">
                    <h2>Ready to plan your next journey?</h2>
                    <p>Join thousands of travelers using verified AI multi-agent intelligence.</p>
                    <button className="button button-primary button-lg" onClick={onStartPlanning}>
                        Launch Trip Studio Now
                    </button>
                </div>
            </section>
        </div>
    )
}
