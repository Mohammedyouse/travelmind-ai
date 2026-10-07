import React, { useState, useEffect } from 'react'
import { api, type AdminStats } from '../services/api'

type AdminViewProps = {
    token: string
}

export function AdminView({ token }: AdminViewProps) {
    const [stats, setStats] = useState<AdminStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        setLoading(true)
        api.adminStats(token)
            .then(data => setStats(data))
            .catch(err => setError(err.message || 'Could not fetch admin statistics.'))
            .finally(() => setLoading(false))
    }, [token])

    if (loading) return <div className="loading-state"><p>Loading system metrics and telemetry...</p></div>
    if (error) return <div className="error-banner">{error}</div>
    if (!stats) return null

    return (
        <div className="admin-view-container">
            <div className="section-heading-bar">
                <div>
                    <span className="section-kicker">Platform Administration</span>
                    <h2>System Telemetry & Health Dashboard</h2>
                </div>
                <span className="health-badge status-healthy">● System {stats.system_status.toUpperCase()}</span>
            </div>

            {/* Quick KPI stats */}
            <div className="kpi-grid mt-3">
                <div className="kpi-card">
                    <span className="kpi-icon">👥</span>
                    <div className="kpi-info">
                        <span className="kpi-label">Registered Accounts</span>
                        <strong className="kpi-value">{stats.total_users}</strong>
                    </div>
                </div>

                <div className="kpi-card">
                    <span className="kpi-icon">🗺️</span>
                    <div className="kpi-info">
                        <span className="kpi-label">Total Generated Trips</span>
                        <strong className="kpi-value">{stats.total_trips}</strong>
                    </div>
                </div>

                <div className="kpi-card">
                    <span className="kpi-icon">🗄️</span>
                    <div className="kpi-info">
                        <span className="kpi-label">Primary Database</span>
                        <strong className="kpi-value">{stats.database.toUpperCase()}</strong>
                    </div>
                </div>

                <div className="kpi-card">
                    <span className="kpi-icon">💳</span>
                    <div className="kpi-info">
                        <span className="kpi-label">Subscriptions</span>
                        <div className="sub-counts-row">
                            {Object.entries(stats.subscriptions || {}).map(([tier, count]) => (
                                <span key={tier} className="sub-count-tag">{tier}: {count}</span>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Admin Grid */}
            <div className="admin-tables-grid mt-4">
                {/* Users List */}
                <div className="surface-card">
                    <h3>Recent Registered Travelers</h3>
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Role</th>
                                <th>Created</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(stats.recent_users || []).map(u => (
                                <tr key={u.id}>
                                    <td><strong>{u.full_name}</strong></td>
                                    <td>{u.email}</td>
                                    <td><span className={`role-tag role-${u.role}`}>{u.role}</span></td>
                                    <td><small>{new Date(u.created_at).toLocaleDateString()}</small></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* Execution Logs */}
                <div className="surface-card">
                    <h3>Multi-Agent Execution Audit Logs</h3>
                    <div className="logs-scroller">
                        {(stats.recent_logs || []).map(l => (
                            <div key={l.id} className="log-item-row">
                                <div className="log-top">
                                    <span className="agent-badge">{l.agent_name}</span>
                                    <span className={`log-status status-${l.status}`}>{l.status}</span>
                                    <span className="log-timing">{l.duration_ms}ms</span>
                                </div>
                                {l.error && <p className="log-error-text">⚠️ {l.error}</p>}
                                <small className="log-timestamp">{new Date(l.created_at).toLocaleTimeString()}</small>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
