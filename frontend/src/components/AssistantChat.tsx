import React, { useState, useEffect, useRef } from 'react'
import { api, type ChatMessage } from '../services/api'

type AssistantChatProps = {
    token: string
    tripId?: string
}

const QUICK_PROMPTS = [
    'How do I optimize my trip budget to avoid overrunning?',
    'What are the best boutique stays near the historic center?',
    'What should I pack given the current weather forecast?',
    'How do I get from the airport to the city center easily?',
]

export function AssistantChat({ token, tripId }: AssistantChatProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        api.conversations(token, tripId).then(history => {
            if (history && history.length > 0) {
                setMessages(history)
            } else {
                setMessages([
                    {
                        id: 'welcome-0',
                        role: 'assistant',
                        content: 'Hello! I am your TravelMind AI Concierge. I can answer questions about your flights, boutique stays, daily schedule pacing, or budget guardrails. How can I assist you today?',
                        created_at: new Date().toISOString(),
                    },
                ])
            }
        }).catch(() => {})
    }, [token, tripId])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    async function handleSend(textToSend?: string) {
        const text = textToSend || input
        if (!text.trim() || isLoading) return

        const userMsg: ChatMessage = {
            id: `temp-${Date.now()}`,
            role: 'user',
            content: text.trim(),
            created_at: new Date().toISOString(),
        }
        setMessages(prev => [...prev, userMsg])
        setInput('')
        setIsLoading(true)

        try {
            const reply = await api.sendMessage(token, text.trim(), tripId)
            setMessages(prev => [...prev, reply])
        } catch (err: any) {
            setMessages(prev => [
                ...prev,
                {
                    id: `err-${Date.now()}`,
                    role: 'assistant',
                    content: 'Sorry, I encountered a temporary connection issue. Please try again.',
                    created_at: new Date().toISOString(),
                },
            ])
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="chat-container">
            <div className="chat-header">
                <div className="chat-title-group">
                    <span className="chat-avatar">🤖</span>
                    <div>
                        <h3>TravelMind AI Concierge</h3>
                        <small className="online-tag">● Live Multi-Agent Assistant</small>
                    </div>
                </div>
            </div>

            <div className="chat-messages-area">
                {messages.map(m => (
                    <div key={m.id} className={`chat-bubble ${m.role === 'user' ? 'user-bubble' : 'bot-bubble'}`}>
                        <div className="bubble-content">
                            <p>{m.content}</p>
                            <span className="bubble-time">
                                {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </div>
                    </div>
                ))}
                {isLoading && (
                    <div className="chat-bubble bot-bubble">
                        <div className="typing-dots">
                            <span /><span /><span />
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="quick-prompts-bar">
                {QUICK_PROMPTS.map(prompt => (
                    <button
                        key={prompt}
                        className="quick-chip-btn"
                        onClick={() => handleSend(prompt)}
                        disabled={isLoading}
                    >
                        {prompt}
                    </button>
                ))}
            </div>

            <form
                className="chat-input-bar"
                onSubmit={e => {
                    e.preventDefault()
                    handleSend()
                }}
            >
                <input
                    type="text"
                    placeholder="Ask about flights, stays, daily pacing, or budget..."
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    disabled={isLoading}
                />
                <button type="submit" className="button button-primary" disabled={!input.trim() || isLoading}>
                    Send &rarr;
                </button>
            </form>
        </div>
    )
}
