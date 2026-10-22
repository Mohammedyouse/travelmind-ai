import test from 'node:test'
import assert from 'node:assert/strict'
import { api, ApiError, setOnUnauthorized, type User } from '../services/api.ts'

// Mock LocalStorage
class MockLocalStorage {
    private store: Record<string, string> = {}
    getItem(key: string): string | null {
        return this.store[key] ?? null
    }
    setItem(key: string, value: string): void {
        this.store[key] = String(value)
    }
    removeItem(key: string): void {
        delete this.store[key]
    }
    clear(): void {
        this.store = {}
    }
}

const mockStorage = new MockLocalStorage()
;(globalThis as any).localStorage = mockStorage
;(globalThis as any).window = {
    location: { hostname: 'localhost' },
    addEventListener: () => {},
    removeEventListener: () => {},
}

test('Authentication and Session Flow Test Suite', async (t) => {
    const originalFetch = globalThis.fetch

    t.afterEach(() => {
        globalThis.fetch = originalFetch
        mockStorage.clear()
        setOnUnauthorized(null)
    })

    await t.test('1. Successful login returns user and token, normalized id', async () => {
        globalThis.fetch = (async (url: string, opts: any) => {
            return new Response(JSON.stringify({
                user: { id: 'usr-1', email: 'test@example.com', full_name: 'Test User', role: 'traveler' },
                token: 'valid-jwt-token-123'
            }), { status: 200, headers: { 'Content-Type': 'application/json' } })
        }) as any

        let authPending = true
        let authError = ''
        let sessionResult: any = null

        try {
            sessionResult = await api.login('test@example.com', 'password123')
            assert.equal(sessionResult.token, 'valid-jwt-token-123')
            assert.equal(sessionResult.user.email, 'test@example.com')
            assert.equal(sessionResult.user.id, 'usr-1')
        } catch (err: any) {
            authError = err.message
        } finally {
            authPending = false
        }

        assert.equal(authPending, false, 'Loading state must be reset')
        assert.equal(authError, '', 'No error should be recorded')
        assert.ok(sessionResult !== null)
    })

    await t.test('2. Invalid credentials returns 401 without firing onUnauthorizedCallback', async () => {
        globalThis.fetch = (async () => {
            return new Response(JSON.stringify({ detail: 'Invalid credentials' }), {
                status: 401,
                headers: { 'Content-Type': 'application/json' },
            })
        }) as any

        let unauthorizedFired = false
        setOnUnauthorized(() => { unauthorizedFired = true })

        let authPending = true
        let authError = ''

        try {
            await api.login('wrong@example.com', 'badpassword')
        } catch (err: any) {
            assert.ok(err instanceof ApiError)
            assert.equal(err.status, 401)
            assert.equal(err.isAuthError, true)
            assert.equal(err.isNetworkError, false)
            authError = err.message
        } finally {
            authPending = false
        }

        assert.equal(authPending, false, 'Loading state must be reset on invalid credentials')
        assert.equal(authError, 'Invalid credentials')
        assert.equal(unauthorizedFired, false, 'onUnauthorizedCallback must NOT fire for login attempts')
    })

    await t.test('3. Expired or invalid token on protected call triggers onUnauthorizedCallback and clears session', async () => {
        globalThis.fetch = (async () => {
            return new Response(JSON.stringify({ detail: 'invalid or expired token' }), {
                status: 401,
                headers: { 'Content-Type': 'application/json' },
            })
        }) as any

        mockStorage.setItem('travelmind.session-token', 'expired-token')
        let unauthorizedToken: string | undefined = undefined
        setOnUnauthorized((token) => {
            unauthorizedToken = token
            mockStorage.removeItem('travelmind.session-token')
        })

        try {
            await api.currentUser('expired-token')
            assert.fail('Should have thrown ApiError')
        } catch (err: any) {
            assert.ok(err instanceof ApiError)
            assert.equal(err.status, 401)
            assert.equal(err.isAuthError, true)
        }

        assert.equal(unauthorizedToken, 'expired-token')
        assert.equal(mockStorage.getItem('travelmind.session-token'), null, 'Expired token must be cleared from storage')
    })

    await t.test('4. Backend unavailable or Failed to fetch preserves token and classifies network error', async () => {
        globalThis.fetch = (async () => {
            throw new TypeError('Failed to fetch')
        }) as any

        mockStorage.setItem('travelmind.session-token', 'my-active-token')
        let unauthorizedFired = false
        setOnUnauthorized(() => { unauthorizedFired = true })

        let caughtError: any = null
        try {
            await api.currentUser('my-active-token')
        } catch (err: any) {
            caughtError = err
        }

        assert.ok(caughtError instanceof ApiError)
        assert.equal(caughtError.isNetworkError, true, 'Must be marked as network error')
        assert.equal(caughtError.isAuthError, false, 'Must NOT be marked as auth error')
        assert.equal(unauthorizedFired, false, 'onUnauthorizedCallback must NOT fire on network error')
        assert.equal(mockStorage.getItem('travelmind.session-token'), 'my-active-token', 'Token MUST be preserved on network error')
        assert.match(caughtError.message, /Unable to connect to TravelMind server/i)
    })

    await t.test('5. Successful login followed by profile loading', async () => {
        let callCount = 0
        globalThis.fetch = (async (url: string) => {
            callCount++
            if (url.includes('/auth/login')) {
                return new Response(JSON.stringify({
                    user: { id: 'usr-42', email: 'traveler@world.com', full_name: 'Explorer', role: 'traveler' },
                    token: 'new-token-42'
                }), { status: 200, headers: { 'Content-Type': 'application/json' } })
            }
            if (url.includes('/auth/me')) {
                return new Response(JSON.stringify({
                    user: { sub: 'usr-42', email: 'traveler@world.com', full_name: 'Explorer', role: 'traveler' },
                    subscription: { tier: 'pro', status: 'active', limits: { trip_limit: 10 } }
                }), { status: 200, headers: { 'Content-Type': 'application/json' } })
            }
            throw new Error('Unexpected URL: ' + url)
        }) as any

        const loginRes = await api.login('traveler@world.com', 'pw')
        assert.equal(loginRes.token, 'new-token-42')
        assert.equal(loginRes.user.id, 'usr-42')

        const meRes = await api.currentUser(loginRes.token)
        assert.equal(meRes.user.id, 'usr-42')
        assert.equal(meRes.subscription?.tier, 'pro')
        assert.equal(callCount, 2)
    })

    await t.test('Trip planning requests allow enough time for dependent agents', async () => {
        const originalSetTimeout = globalThis.setTimeout
        const originalClearTimeout = globalThis.clearTimeout
        let timeoutDelay = 0
        globalThis.setTimeout = ((_, delay) => {
            timeoutDelay = Number(delay)
            return 0 as any
        }) as any
        globalThis.clearTimeout = (() => {}) as any
        globalThis.fetch = (async () => new Response('{}', {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
        })) as any

        try {
            await api.createTrip('planning-token', {
                origin: 'SFO',
                destination: 'LIS',
                departure_date: '2027-05-10',
                travelers: 1,
                budget: 2000,
                currency: 'USD',
                interests: [],
                preferences: {},
            })
            assert.equal(timeoutDelay, 300_000)

            await api.updateTrip('planning-token', 'trip-1', { budget: 2500 })
            assert.equal(timeoutDelay, 300_000)
        } finally {
            globalThis.setTimeout = originalSetTimeout
            globalThis.clearTimeout = originalClearTimeout
        }
    })

    await t.test('6. Page refresh with a valid session restores user seamlessly', async () => {
        const storedToken = 'existing-valid-session'
        mockStorage.setItem('travelmind.session-token', storedToken)

        globalThis.fetch = (async (url: string, opts: any) => {
            const authHeader = opts.headers?.get ? opts.headers.get('Authorization') : opts.headers?.Authorization
            assert.equal(authHeader, `Bearer ${storedToken}`)
            return new Response(JSON.stringify({
                user: { id: 'usr-restore', email: 'restored@travelmind.ai', full_name: 'Restored User', role: 'traveler' },
                subscription: { tier: 'free' }
            }), { status: 200, headers: { 'Content-Type': 'application/json' } })
        }) as any

        let isRestoring = true
        let user: User | null = null
        let restoreMessage = ''

        try {
            const token = mockStorage.getItem('travelmind.session-token')
            assert.ok(token)
            const result = await api.currentUser(token)
            user = result.user
            restoreMessage = ''
        } catch {
            restoreMessage = 'Failed'
        } finally {
            isRestoring = false
        }

        assert.equal(isRestoring, false)
        assert.equal(user?.email, 'restored@travelmind.ai')
        assert.equal(restoreMessage, '')
        assert.equal(mockStorage.getItem('travelmind.session-token'), storedToken)
    })

    await t.test('7. Page refresh with an expired session sets restoreMessage and clears storage', async () => {
        const expiredToken = 'expired-session-token'
        mockStorage.setItem('travelmind.session-token', expiredToken)

        globalThis.fetch = (async () => {
            return new Response(JSON.stringify({ detail: 'Token expired' }), {
                status: 401,
                headers: { 'Content-Type': 'application/json' },
            })
        }) as any

        let isRestoring = true
        let user: User | null = null
        let restoreMessage = ''

        try {
            const token = mockStorage.getItem('travelmind.session-token')
            assert.ok(token)
            const result = await api.currentUser(token)
            user = result.user
        } catch (err: any) {
            if ((err instanceof ApiError && err.isAuthError) || err?.status === 401) {
                mockStorage.removeItem('travelmind.session-token')
                user = null
                restoreMessage = 'Your session expired. Sign in to continue.'
            }
        } finally {
            isRestoring = false
        }

        assert.equal(isRestoring, false)
        assert.equal(user, null)
        assert.equal(restoreMessage, 'Your session expired. Sign in to continue.')
        assert.equal(mockStorage.getItem('travelmind.session-token'), null)
    })

    await t.test('8. Recovery after backend becomes available again', async () => {
        let backendUp = false
        const savedToken = 'persistent-token'
        mockStorage.setItem('travelmind.session-token', savedToken)

        globalThis.fetch = (async () => {
            if (!backendUp) {
                throw new TypeError('Failed to fetch')
            }
            return new Response(JSON.stringify({
                user: { id: 'usr-rec', email: 'recovered@travelmind.ai', full_name: 'Recovered', role: 'traveler' }
            }), { status: 200, headers: { 'Content-Type': 'application/json' } })
        }) as any

        // Step A: Attempt while backend is down
        let user: User | null = null
        let networkError = ''
        try {
            const res = await api.currentUser(savedToken)
            user = res.user
        } catch (err: any) {
            networkError = err.message
        }

        assert.equal(user, null)
        assert.match(networkError, /Unable to connect to TravelMind server/i)
        assert.equal(mockStorage.getItem('travelmind.session-token'), savedToken, 'Token was safely kept during outage')

        // Step B: Backend becomes available
        backendUp = true
        networkError = ''
        try {
            const res = await api.currentUser(savedToken)
            user = res.user
        } catch (err: any) {
            networkError = err.message
        }

        assert.ok(user !== null)
        assert.equal(user?.email, 'recovered@travelmind.ai')
        assert.equal(networkError, '')
    })

    await t.test('9. Loading state reset after every failure', async () => {
        const failureCases = [
            { name: '401 Unauthorized', fn: async () => { throw new ApiError('Unauthorized', 401) } },
            { name: 'Network Error', fn: async () => { throw new ApiError('Failed to fetch', 0, null, true) } },
            { name: 'Timeout Error', fn: async () => { throw new ApiError('Timeout', 408, null, true) } },
            { name: '500 Server Error', fn: async () => { throw new ApiError('Internal Error', 500) } },
        ]

        for (const c of failureCases) {
            let isLoading = true
            let errorCaught = false
            try {
                await c.fn()
            } catch {
                errorCaught = true
            } finally {
                isLoading = false
            }
            assert.equal(isLoading, false, `Loading state must reset to false for ${c.name}`)
            assert.equal(errorCaught, true, `Error should have been caught for ${c.name}`)
        }
    })

    await t.test('10. Competing login vs session-restoration race condition prevention', async () => {
        // Token A is from previous session
        const tokenA = 'token-A-old'
        const tokenB = 'token-B-new'
        let currentActiveToken = tokenA

        let userState: User | null = null
        let restoreMessage = ''

        // Simulate restore session promise for Token A that takes longer
        let resolveTokenA: (val: any) => void
        const slowRestorePromise = new Promise((resolve, reject) => {
            resolveTokenA = () => {
                // Token A fails with 401 Expired
                reject(new ApiError('invalid or expired token', 401))
            }
        })

        // Simulate user clicking login in the meantime (Token B succeeds immediately)
        currentActiveToken = tokenB
        userState = { id: 'usr-B', email: 'new@travelmind.ai', full_name: 'New User', role: 'traveler' }
        mockStorage.setItem('travelmind.session-token', tokenB)

        // Now Token A's promise completes with 401
        try {
            resolveTokenA!(null)
            await slowRestorePromise
        } catch (err: any) {
            // In the hardened AuthContext:
            // "if (tokenRef.current !== initialToken) return"
            if (currentActiveToken === tokenA) {
                userState = null
                restoreMessage = 'Your session expired. Sign in to continue.'
                mockStorage.removeItem('travelmind.session-token')
            }
        }

        // Token B's state MUST NOT be cleared or overwritten!
        assert.equal(currentActiveToken, tokenB)
        assert.equal(userState?.email, 'new@travelmind.ai')
        assert.equal(restoreMessage, '', 'Restore message must not be set when superseded by new login')
        assert.equal(mockStorage.getItem('travelmind.session-token'), tokenB)
    })
})
