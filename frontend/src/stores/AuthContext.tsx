import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, type User } from '../services/api'

type AuthContextValue = {
    user: User | null
    token: string | null
    isRestoring: boolean
    restoreMessage: string
    login: (email: string, password: string) => Promise<void>
    register: (email: string, password: string, fullName: string) => Promise<void>
    logout: () => void
}

const TOKEN_KEY = 'travelmind.session-token'
const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
    const [user, setUser] = useState<User | null>(null)
    const [isRestoring, setIsRestoring] = useState(true)
    const [restoreMessage, setRestoreMessage] = useState('')

    useEffect(() => {
        let active = true
        if (!token) {
            setUser(null)
            setIsRestoring(false)
            return () => { active = false }
        }
        setIsRestoring(true)
        api.currentUser(token).then(({ user: currentUser }) => {
            if (active) setUser(currentUser)
        }).catch(() => {
            if (active) {
                localStorage.removeItem(TOKEN_KEY)
                setToken(null)
                setUser(null)
                setRestoreMessage('Your session expired. Sign in to continue.')
            }
        }).finally(() => {
            if (active) setIsRestoring(false)
        })
        return () => { active = false }
    }, [token])

    async function acceptSession(authenticate: () => Promise<{ user: User; token: string }>) {
        const session = await authenticate()
        localStorage.setItem(TOKEN_KEY, session.token)
        setUser(session.user)
        setToken(session.token)
        setRestoreMessage('')
    }

    async function login(email: string, password: string) {
        await acceptSession(() => api.login(email, password))
    }

    async function register(email: string, password: string, fullName: string) {
        await acceptSession(() => api.register(email, password, fullName))
    }

    function logout() {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
    }

    return (
        <AuthContext.Provider value={{ user, token, isRestoring, restoreMessage, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) throw new Error('useAuth must be used inside AuthProvider')
    return context
}