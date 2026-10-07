export type User = {
    id: string
    email: string
    full_name: string
    role: string
}

export type AgentOutput = {
    name: string
    status: string
    summary: string
    data: Record<string, any>
    recommendations: string[]
    errors: string[]
}

export type ItineraryDay = {
    day: number
    title?: string
    activities: string[]
    morning?: { activity: string; location?: string; time?: string; cost?: number }
    afternoon?: { activity: string; location?: string; time?: string; cost?: number }
    evening?: { activity: string; location?: string; time?: string; cost?: number }
}

export type TripRecord = {
    id: string
    trip_id?: string
    user_id: string
    origin: string
    destination: string
    departure_date: string | null
    return_date: string | null
    duration_days: number | null
    travelers: number
    budget: number | null
    currency: string
    status: string
    summary: string | null
    preferences: Record<string, any>
    plan_results: {
        itinerary?: {
            destination?: string
            duration_days?: number
            source?: string
            days?: ItineraryDay[]
        }
        flight_intelligence?: AgentOutput
        accommodation_intelligence?: AgentOutput
        destination_discovery?: AgentOutput
        transportation_route?: AgentOutput
        budget_intelligence?: AgentOutput
        personalization_recommendation?: AgentOutput
        travel_support?: AgentOutput
        agent_execution?: Record<string, { status: string; attempts: number; duration_ms: number; error: string }>
        [key: string]: any
    }
    created_at: string
}

export type TripInput = {
    origin: string
    destination: string
    departure_date: string
    return_date?: string
    duration_days?: number
    travelers: number
    budget: number
    currency: string
    interests: string[]
    preferences: Record<string, any>
}

export type SubscriptionInfo = {
    id: string
    tier: 'free' | 'pro' | 'enterprise'
    status: string
    limits: {
        trip_limit: number
        ai_model: string
        features: string[]
    }
}

export type NotificationItem = {
    id: string
    type: string
    title: string
    message: string
    status: 'unread' | 'read'
    created_at: string
}

export type ChatMessage = {
    id: string
    role: 'user' | 'assistant'
    content: string
    created_at: string
}

export type AdminStats = {
    total_users: number
    total_trips: number
    subscriptions: Record<string, number>
    recent_users: Array<{ id: string; email: string; full_name: string; role: string; created_at: string }>
    recent_logs: Array<{ id: string; agent_name: string; status: string; duration_ms: number; error?: string; created_at: string }>
    system_status: string
    database: string
}

type AuthResponse = { user: User; token: string }
const API_BASE_URL = (typeof window !== 'undefined' && (window as any).__RUNTIME_CONFIG__?.VITE_API_BASE_URL)
    || import.meta.env.VITE_API_BASE_URL
    || 'http://localhost:8000'

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
    const headers = new Headers(options.headers)
    if (options.body) headers.set('Content-Type', 'application/json')
    if (token) headers.set('Authorization', `Bearer ${token}`)

    const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
    const body = await response.json().catch(() => null) as { detail?: unknown } | null
    if (!response.ok) {
        const message = typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`
        throw new Error(message)
    }
    return body as T
}

export const api = {
    login: (email: string, password: string) => request<AuthResponse>('/api/v1/auth/login', {
        method: 'POST', body: JSON.stringify({ email, password }),
    }),
    register: (email: string, password: string, full_name: string) => request<AuthResponse>('/api/v1/auth/register', {
        method: 'POST', body: JSON.stringify({ email, password, full_name }),
    }),
    currentUser: (token: string) => request<{ user: User; subscription?: SubscriptionInfo }>('/api/v1/auth/me', {}, token),

    // Trips
    trips: (token: string) => request<TripRecord[]>('/api/v1/trips', {}, token),
    trip: (token: string, id: string) => request<TripRecord>(`/api/v1/trips/${encodeURIComponent(id)}`, {}, token),
    createTrip: (token: string, input: TripInput) => request<TripRecord>('/api/v1/trips', {
        method: 'POST', body: JSON.stringify(input),
    }, token),
    updateTrip: (token: string, id: string, input: Partial<TripInput>) => request<TripRecord>(`/api/v1/trips/${encodeURIComponent(id)}`, {
        method: 'PATCH', body: JSON.stringify(input),
    }, token),
    deleteTrip: (token: string, id: string) => request<{ status: string; success: boolean }>(`/api/v1/trips/${encodeURIComponent(id)}`, {
        method: 'DELETE',
    }, token),
    exportTripUrl: (id: string, format = 'html') => `${API_BASE_URL}/api/v1/trips/${encodeURIComponent(id)}/export?format=${format}`,

    // Assistant Chat
    conversations: (token: string, trip_id?: string) => request<ChatMessage[]>(
        trip_id ? `/api/v1/conversations?trip_id=${encodeURIComponent(trip_id)}` : '/api/v1/conversations', {}, token
    ),
    sendMessage: (token: string, content: string, trip_id?: string) => request<ChatMessage>('/api/v1/conversations', {
        method: 'POST', body: JSON.stringify({ content, trip_id }),
    }, token),

    // Preferences
    preferences: (token: string) => request<Record<string, any>>('/api/v1/preferences', {}, token),
    savePreferences: (token: string, prefs: Record<string, any>) => request<Record<string, any>>('/api/v1/preferences', {
        method: 'PUT', body: JSON.stringify(prefs),
    }, token),

    // Notifications
    notifications: (token: string) => request<NotificationItem[]>('/api/v1/notifications', {}, token),
    markNotificationRead: (token: string, id: string) => request<{ id: string; status: string }>(
        `/api/v1/notifications/${encodeURIComponent(id)}/read`, { method: 'PATCH' }, token
    ),

    // Subscriptions
    subscriptionTiers: () => request<Array<{ tier: string; name: string; price_usd: number; interval: string; popular?: boolean; features: string[] }>>('/api/v1/subscriptions/tiers'),
    currentSubscription: (token: string) => request<SubscriptionInfo>('/api/v1/subscriptions/current', {}, token),
    upgradeSubscription: (token: string, tier: string) => request<SubscriptionInfo>('/api/v1/subscriptions/upgrade', {
        method: 'POST', body: JSON.stringify({ tier }),
    }, token),

    // Admin
    adminStats: (token: string) => request<AdminStats>('/api/v1/admin/stats', {}, token),
    adminUsers: (token: string) => request<User[]>('/api/v1/admin/users', {}, token),
}