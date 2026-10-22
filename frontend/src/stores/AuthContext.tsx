import { createContext, useContext, useEffect, useState, useRef, type ReactNode } from 'react'
import { api, type User, ApiError, setOnUnauthorized } from '../services/api'

type AuthContextValue = {
    user: User | null
    token: string | null
    isRestoring: boolean
    restoreMessage: string
    networkError: string
    clearRestoreMessage: () => void
    clearNetworkError: () => void
    login: (email: string, password: string) => Promise<void>
    register: (email: string, password: string, fullName: string) => Promise<void>
    logout: () => void
    retryRestore: () => Promise<void>
}

const TOKEN_KEY = 'travelmind.session-token'
const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(() => {
        try {
            return typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
        } catch {
            return null
        }
    })
    const [user, setUser] = useState<User | null>(null)
    const [isRestoring, setIsRestoring] = useState<boolean>(() => {
        try {
            return typeof window !== 'undefined' && Boolean(localStorage.getItem(TOKEN_KEY))
        } catch {
            return false
        }
    })
    const [restoreMessage, setRestoreMessage] = useState<string>('')
    const [networkError, setNetworkError] = useState<string>('')

    const tokenRef = useRef<string | null>(token)
    tokenRef.current = token
    const hasRestoredRef = useRef<boolean>(false)
    const inFlightRestorationRef = useRef<string | null>(null)

    // 1. Subscribe to 401 Unauthorized events from api.ts
    useEffect(() => {
        setOnUnauthorized((failedToken?: string) => {
            if (tokenRef.current && (!failedToken || failedToken === tokenRef.current)) {
                try {
                    localStorage.removeItem(TOKEN_KEY)
                } catch {}
                tokenRef.current = null
                setToken(null)
                setUser(null)
                setRestoreMessage('Your session expired. Sign in to continue.')
            }
        })
        return () => setOnUnauthorized(null)
    }, [])

    async function restoreSession(targetToken: string) {
        if (!targetToken) {
            setUser(null)
            setToken(null)
            setIsRestoring(false)
            return
        }
        inFlightRestorationRef.current = targetToken
        setIsRestoring(true)
        setNetworkError('')

        try {
            const { user: currentUser } = await api.currentUser(targetToken)
            // Guard: If user logged in with a different valid session while this was in-flight, ignore
            if (tokenRef.current !== null && tokenRef.current !== targetToken) return

            setUser(currentUser)
            setToken(targetToken)
            tokenRef.current = targetToken
            setRestoreMessage('')
            setNetworkError('')
        } catch (err: any) {
            // Guard: If user logged in with a different valid session while this was in-flight, ignore
            if (tokenRef.current !== null && tokenRef.current !== targetToken) return

            if ((err instanceof ApiError && err.isAuthError) || err?.status === 401) {
                try {
                    localStorage.removeItem(TOKEN_KEY)
                } catch {}
                tokenRef.current = null
                setToken(null)
                setUser(null)
                setRestoreMessage('Your session expired. Sign in to continue.')
            } else {
                // Connectivity / network issue: preserve token so user does not lose session on offline/restart
                setToken(targetToken)
                tokenRef.current = targetToken
                setNetworkError(err?.message || 'Unable to connect to TravelMind server. Please verify the backend is running.')
            }
        } finally {
            if (inFlightRestorationRef.current === targetToken) {
                inFlightRestorationRef.current = null
                setIsRestoring(false)
            }
        }
    }

    // 2. Perform initial session restoration ONCE on mount
    useEffect(() => {
        if (hasRestoredRef.current) return
        hasRestoredRef.current = true

        const initialToken = (() => {
            try {
                return localStorage.getItem(TOKEN_KEY)
            } catch {
                return null
            }
        })()

        if (initialToken) {
            restoreSession(initialToken)
        } else {
            setIsRestoring(false)
        }
    }, [])

    // 3. Auto-retry restoration when browser comes back online
    useEffect(() => {
        const handleOnline = () => {
            if (tokenRef.current && !user) {
                restoreSession(tokenRef.current)
            }
        }
        window.addEventListener('online', handleOnline)
        return () => window.removeEventListener('online', handleOnline)
    }, [user])

    async function acceptSession(authenticate: () => Promise<{ user: User; token: string }>) {
        const session = await authenticate()
        try {
            localStorage.setItem(TOKEN_KEY, session.token)
        } catch {}
        tokenRef.current = session.token
        setUser(session.user)
        setToken(session.token)
        setRestoreMessage('')
        setNetworkError('')
        setIsRestoring(false)
    }

    async function login(email: string, password: string) {
        await acceptSession(() => api.login(email, password))
    }

    async function register(email: string, password: string, fullName: string) {
        await acceptSession(() => api.register(email, password, fullName))
    }

    function logout() {
        try {
            localStorage.removeItem(TOKEN_KEY)
        } catch {}
        tokenRef.current = null
        setToken(null)
        setUser(null)
        setRestoreMessage('')
        setNetworkError('')
        setIsRestoring(false)
    }

    function clearRestoreMessage() {
        setRestoreMessage('')
    }

    function clearNetworkError() {
        setNetworkError('')
    }

    async function retryRestore() {
        const target = tokenRef.current || (() => {
            try {
                return localStorage.getItem(TOKEN_KEY)
            } catch {
                return null
            }
        })()
        if (target) {
            await restoreSession(target)
        }
    }

    return (
        <AuthContext.Provider value={{
            user,
            token,
            isRestoring,
            restoreMessage,
            networkError,
            clearRestoreMessage,
            clearNetworkError,
            login,
            register,
            logout,
            retryRestore,
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) throw new Error('useAuth must be used inside AuthProvider')
    return context
}