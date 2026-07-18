import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'

const LogoIcon = () => (
  <svg className="logo-icon" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="40" height="40" rx="12" fill="url(#logoGrad)"/>
    <path d="M10 14a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H22l-4 4-4-4h-2a2 2 0 0 1-2-2V14Z" fill="white" fillOpacity="0.95"/>
    <circle cx="15" cy="19" r="1.8" fill="url(#logoGrad)"/>
    <circle cx="20" cy="19" r="1.8" fill="url(#logoGrad)"/>
    <circle cx="25" cy="19" r="1.8" fill="url(#logoGrad)"/>
    <defs>
      <linearGradient id="logoGrad" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
        <stop stopColor="#7c5cfc"/>
        <stop offset="1" stopColor="#c084fc"/>
      </linearGradient>
    </defs>
  </svg>
)

const BotIcon = () => (
  <svg className="avatar-icon" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="32" height="32" rx="10" fill="currentColor" fillOpacity="0.15"/>
    <rect x="8" y="10" width="16" height="12" rx="3" stroke="currentColor" strokeWidth="1.8"/>
    <circle cx="12.5" cy="16" r="1.5" fill="currentColor"/>
    <circle cx="19.5" cy="16" r="1.5" fill="currentColor"/>
    <path d="M13 22v2M19 22v2M16 10V7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    <circle cx="16" cy="6" r="1.5" fill="currentColor"/>
  </svg>
)

const UserIcon = () => (
  <svg className="avatar-icon" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="32" height="32" rx="10" fill="currentColor" fillOpacity="0.15"/>
    <circle cx="16" cy="13" r="4.5" stroke="currentColor" strokeWidth="1.8"/>
    <path d="M7 26c0-4.418 4.03-8 9-8s9 3.582 9 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
  </svg>
)

const ENDPOINTS = {
  ollama: { label: 'Ollama', path: '/askMe', stream: true },
  sap:    { label: 'Anthropic', path: '/sapAgent', stream: false },
}

function InterruptCard({ interrupt, onDecide }) {
  const actions = interrupt.action_requests ?? []
  return (
    <div className="interrupt-card">
      <div className="interrupt-header">Tool approval required</div>
      {actions.map((action) => (
        <div key={action.name} className="interrupt-action">
          <div className="interrupt-tool">{action.name}</div>
          <pre className="interrupt-args">{JSON.stringify(action.args, null, 2)}</pre>
        </div>
      ))}
      <div className="interrupt-buttons">
        <button className="interrupt-btn approve" onClick={() => onDecide('approve')}>Approve</button>
        <button className="interrupt-btn reject"  onClick={() => onDecide('reject')}>Reject</button>
      </div>
    </div>
  )
}

function Message({ role, text, progress, endpoint, interrupts, onDecide }) {
  const isUser = role === 'user'
  return (
    <div className={`message ${role}`}>
      {!isUser && <div className="avatar bot-avatar"><BotIcon /></div>}
      <div className="bubble">
        {isUser ? (
          <div className="user-message-wrap">
            {endpoint && <span className={`endpoint-tag endpoint-tag--${endpoint}`}>{ENDPOINTS[endpoint].label}</span>}
            {text}
          </div>
        ) : (
          <>
            {progress && <div className="progress-text">{progress}</div>}
            {interrupts?.map((interrupt) => (
              <InterruptCard key={interrupt.action_requests?.[0]?.name ?? 'interrupt'} interrupt={interrupt} onDecide={onDecide} />
            ))}
            {text && <ReactMarkdown>{text}</ReactMarkdown>}
          </>
        )}
      </div>
      {isUser && <div className="avatar user-avatar"><UserIcon /></div>}
    </div>
  )
}

async function readStream(res, botId, setMessages) {
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (!line.trim()) continue
      const chunk = JSON.parse(line)
      if (chunk.type === 'progress') {
        setMessages(prev => prev.map(m =>
          m.id === botId ? { ...m, progress: chunk.content } : m
        ))
      } else if (chunk.type === 'message') {
        setMessages(prev => prev.map(m =>
          m.id === botId ? { ...m, text: m.text + chunk.content, progress: null } : m
        ))
      }
    }
  }
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [theme, setTheme] = useState('dark')
  const [activeEndpoint, setActiveEndpoint] = useState('ollama')
  const [pendingUserId, setPendingUserId] = useState(null)
  const bottomRef = useRef(null)
  const nextId = useRef(0)
  const textareaRef = useRef(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
  }, [input])

  const handleDecision = useCallback(async (decision) => {
    if (!pendingUserId) return
    setLoading(true)
    // Remove interrupt card from last bot message
    setMessages(prev => prev.map((m, i) =>
      i === prev.length - 1 ? { ...m, interrupts: null, text: '' } : m
    ))
    const botId = nextId.current++
    setMessages(prev => [...prev, { id: botId, role: 'assistant', text: '' }])

    try {
      const res = await fetch('/sapAgent/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: pendingUserId, decisions: [{ type: decision }] }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      setMessages(prev => prev.map(m =>
        m.id === botId ? { ...m, text: data.message } : m
      ))
    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === botId ? { ...m, text: `Error: ${err.message}` } : m
      ))
    } finally {
      setPendingUserId(null)
      setLoading(false)
    }
  }, [pendingUserId])

  const sendMessage = useCallback(async () => {
    const text = input.trim()
    if (!text || loading) return

    const ep = ENDPOINTS[activeEndpoint]
    const userId = 'RK01'
    setMessages(prev => [...prev, { id: nextId.current++, role: 'user', text, endpoint: activeEndpoint }])
    setInput('')
    setLoading(true)

    const botId = nextId.current++
    setMessages(prev => [...prev, { id: botId, role: 'assistant', text: '' }])

    try {
      const res = await fetch(ep.path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, user_id: userId }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)

      if (ep.stream) {
        await readStream(res, botId, setMessages)
      } else {
        const data = await res.json()
        // Check if response is an interrupt
        try {
          const parsed = JSON.parse(data.message)
          if (parsed.type === 'interrupt') {
            const allActions = parsed.interrupts.flat().flatMap(i => i.action_requests ?? [])
            setPendingUserId(userId)
            setMessages(prev => prev.map(m =>
              m.id === botId ? { ...m, interrupts: allActions.length ? [{ action_requests: allActions }] : null } : m
            ))
            return
          }
        } catch (parseErr) {
          console.debug('Response is not JSON interrupt payload:', parseErr)
        }
        setMessages(prev => prev.map(m =>
          m.id === botId ? { ...m, text: data.message } : m
        ))
      }
    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === botId ? { ...m, text: `Error: ${err.message}` } : m
      ))
    } finally {
      setLoading(false)
    }
  }, [input, loading, activeEndpoint])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-app">
      <header className="chat-header">
        <div className="header-left">
          <LogoIcon />
          <h1><span className="brand-chat">Chat</span> with <span className="brand-me">Agent</span></h1>
        </div>
        <button
          className="theme-toggle"
          onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </header>

      <main className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <BotIcon />
            <p>How can I help you today?</p>
          </div>
        )}
        {messages.map(m => (
          <Message
            key={m.id}
            role={m.role}
            text={m.text}
            progress={m.progress}
            endpoint={m.endpoint}
            interrupts={m.interrupts}
            onDecide={handleDecision}
          />
        ))}
        {loading && (
          <div className="message assistant">
            <div className="avatar bot-avatar"><BotIcon /></div>
            <div className="bubble typing">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </main>

      <div className="chat-input-bar">
        <div className="endpoint-switcher">
          {Object.entries(ENDPOINTS).map(([key, ep]) => (
            <button
              key={key}
              className={`endpoint-btn ${activeEndpoint === key ? 'active' : ''}`}
              onClick={() => setActiveEndpoint(key)}
              disabled={loading}
            >
              {ep.label}
            </button>
          ))}
        </div>
        <div className="input-row">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${ENDPOINTS[activeEndpoint].label}… (Shift+Enter for new line)`}
            disabled={loading || !!pendingUserId}
            rows={1}
            autoFocus
          />
          <button onClick={sendMessage} disabled={loading || !input.trim() || !!pendingUserId} aria-label="Send">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
