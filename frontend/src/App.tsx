import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { clearStoredToken, getStoredToken, setStoredToken } from './api/client'
import {
  type LanguageCode,
  useChatHistory,
  useChatMutation,
  useConversationListQuery,
  useLoginMutation,
  useMeQuery,
  useSignupMutation,
  useUpdateLanguageMutation,
} from './api/queries'
import { getLanguageLabel, t } from './i18n'

const LANGUAGE_STORAGE_KEY = 'ai_niru_language'

type AuthMode = 'login' | 'signup'

const getApiError = (error: unknown, fallback = 'Request failed'): string => {
  if (error && typeof error === 'object' && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
    if (detail) return detail
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}

const getInitialLanguage = (): LanguageCode => {
  const storedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY)
  return storedLanguage === 'sw' ? 'sw' : 'en'
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => Boolean(getStoredToken()))
  const [authMode, setAuthMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [authError, setAuthError] = useState('')
  const [language, setLanguage] = useState<LanguageCode>(getInitialLanguage)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [isDraftConversation, setIsDraftConversation] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const signupMutation = useSignupMutation()
  const loginMutation = useLoginMutation()
  const updateLanguageMutation = useUpdateLanguageMutation()
  const chatMutation = useChatMutation()
  const { data: meData } = useMeQuery(isAuthenticated)
  const { data: conversationList = [] } = useConversationListQuery(isAuthenticated)
  const { data: historyData } = useChatHistory(conversationId ?? '', isAuthenticated && !!conversationId)

  const messages = historyData?.messages ?? []
  const activeConversation = useMemo(
    () => conversationList.find((item) => item.conversation_id === conversationId),
    [conversationId, conversationList]
  )
  const chatTitle = historyData?.title || activeConversation?.title || t(language, 'newConversation')
  const isAuthLoading = signupMutation.isPending || loginMutation.isPending
  const translatedAuthHint = t(language, 'authHint')

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!isAuthenticated || !meData?.preferred_language) return
    if (meData.preferred_language === language) return
    setLanguage(meData.preferred_language)
    localStorage.setItem(LANGUAGE_STORAGE_KEY, meData.preferred_language)
  }, [isAuthenticated, language, meData?.preferred_language])

  useEffect(() => {
    if (conversationId || isDraftConversation) return
    if (conversationList.length === 0) return
    setConversationId(conversationList[0].conversation_id)
  }, [conversationId, conversationList, isDraftConversation])

  useEffect(() => {
    const handleUnauthorized = () => {
      clearStoredToken()
      setIsAuthenticated(false)
      setConversationId(null)
      setIsDraftConversation(false)
    }
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [])

  const resetAuthForm = () => {
    setAuthError('')
    setEmail('')
    setPassword('')
    setDisplayName('')
  }

  const handleAuthSubmit = () => {
    if (!email.trim() || !password.trim()) {
      setAuthError(t(language, 'requiredFields'))
      return
    }
    setAuthError('')

    if (authMode === 'signup') {
      signupMutation.mutate(
        {
          email: email.trim(),
          password,
          display_name: displayName.trim() || undefined,
        },
        {
          onSuccess: (data) => {
            setStoredToken(data.access_token)
            setIsAuthenticated(true)
            setLanguage(data.user.preferred_language)
            localStorage.setItem(LANGUAGE_STORAGE_KEY, data.user.preferred_language)
            resetAuthForm()
          },
          onError: (error) => setAuthError(getApiError(error)),
        }
      )
      return
    }

    loginMutation.mutate(
      {
        email: email.trim(),
        password,
      },
      {
        onSuccess: (data) => {
          setStoredToken(data.access_token)
          setIsAuthenticated(true)
          setLanguage(data.user.preferred_language)
          localStorage.setItem(LANGUAGE_STORAGE_KEY, data.user.preferred_language)
          resetAuthForm()
        },
        onError: (error) => setAuthError(getApiError(error)),
      }
    )
  }

  const handleLanguageChange = (nextLanguage: LanguageCode) => {
    if (nextLanguage === language) return
    setLanguage(nextLanguage)
    localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage)
    if (isAuthenticated) {
      updateLanguageMutation.mutate(nextLanguage)
    }
  }

  const handleSend = () => {
    const text = inputValue.trim()
    if (!text || chatMutation.isPending) return
    setInputValue('')
    chatMutation.mutate(
      { message: text, conversation_id: conversationId ?? undefined, language },
      {
        onSuccess: (data) => {
          setConversationId(data.conversation_id)
          setIsDraftConversation(false)
        },
      }
    )
  }

  const handleNewConversation = () => {
    setConversationId(null)
    setIsDraftConversation(true)
  }

  const handleSelectConversation = (nextConversationId: string) => {
    setConversationId(nextConversationId)
    setIsDraftConversation(false)
  }

  const handleLogout = () => {
    clearStoredToken()
    setIsAuthenticated(false)
    setConversationId(null)
    setIsDraftConversation(false)
    resetAuthForm()
  }

  if (!isAuthenticated) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <p className="auth-kicker">{t(language, 'appName')}</p>
          <h1>{translatedAuthHint}</h1>
          <div className="language-switch auth-language">
            <button
              type="button"
              onClick={() => handleLanguageChange('en')}
              className={language === 'en' ? 'active' : ''}
            >
              EN
            </button>
            <button
              type="button"
              onClick={() => handleLanguageChange('sw')}
              className={language === 'sw' ? 'active' : ''}
            >
              SW
            </button>
          </div>
          <div className="auth-tabs">
            <button
              type="button"
              className={authMode === 'login' ? 'active' : ''}
              onClick={() => {
                setAuthMode('login')
                setAuthError('')
              }}
            >
              {t(language, 'login')}
            </button>
            <button
              type="button"
              className={authMode === 'signup' ? 'active' : ''}
              onClick={() => {
                setAuthMode('signup')
                setAuthError('')
              }}
            >
              {t(language, 'signup')}
            </button>
          </div>

          <label>
            {t(language, 'email')}
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              disabled={isAuthLoading}
            />
          </label>
          {authMode === 'signup' && (
            <label>
              {t(language, 'displayName')}
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                autoComplete="name"
                disabled={isAuthLoading}
              />
            </label>
          )}
          <label>
            {t(language, 'password')}
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={authMode === 'login' ? 'current-password' : 'new-password'}
              disabled={isAuthLoading}
              onKeyDown={(e) => e.key === 'Enter' && handleAuthSubmit()}
            />
          </label>
          {(authError || loginMutation.isError || signupMutation.isError) && (
            <p className="error-message">
              {authError || getApiError(loginMutation.error || signupMutation.error)}
            </p>
          )}
          <button type="button" className="auth-submit" onClick={handleAuthSubmit} disabled={isAuthLoading}>
            {authMode === 'login' ? t(language, 'login') : t(language, 'signup')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <h1>{t(language, 'appName')}</h1>
          <p>{t(language, 'subtitle')}</p>
        </div>

        <div className="language-group">
          <span>{t(language, 'language')}</span>
          <div className="language-switch">
            <button
              type="button"
              onClick={() => handleLanguageChange('en')}
              className={language === 'en' ? 'active' : ''}
            >
              EN
            </button>
            <button
              type="button"
              onClick={() => handleLanguageChange('sw')}
              className={language === 'sw' ? 'active' : ''}
            >
              SW
            </button>
          </div>
        </div>

        <button type="button" className="new-conversation-btn" onClick={handleNewConversation}>
          {t(language, 'newConversation')}
        </button>

        <div className="conversation-panel">
          <p className="panel-title">{t(language, 'conversations')}</p>
          {conversationList.length === 0 && <p className="empty-panel">{t(language, 'noConversations')}</p>}
          {conversationList.map((conversation) => {
            const title = conversation.title || t(language, 'newConversation')
            return (
              <button
                type="button"
                key={conversation.conversation_id}
                className={`conversation-item ${conversationId === conversation.conversation_id ? 'active' : ''}`}
                onClick={() => handleSelectConversation(conversation.conversation_id)}
              >
                <span className="conversation-title">{title}</span>
                <span className="conversation-preview">{conversation.preview || '...'}</span>
              </button>
            )
          })}
        </div>

        <div className="sidebar-footer">
          <span>{meData?.email}</span>
          <button type="button" onClick={handleLogout}>
            {t(language, 'logout')}
          </button>
        </div>
      </aside>

      <main className="chat-canvas">
        <header className="chat-header">
          <div>
            <h2>{chatTitle}</h2>
            <p>{getLanguageLabel(language)}</p>
          </div>
        </header>

        <section className="messages-container">
          {messages.length === 0 && !chatMutation.isPending && (
            <div className="empty-chat-state">
              <h3>{t(language, 'welcome')}</h3>
              <p>{t(language, 'startPrompt')}</p>
            </div>
          )}
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`message message-${message.role}`}>
              <p className="message-role">{message.role}</p>
              <div className="message-content">{message.content}</div>
            </div>
          ))}
          {chatMutation.isPending && (
            <div className="message message-assistant pending">
              <p className="message-role">assistant</p>
              <div className="message-content">{t(language, 'thinking')}</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </section>

        <footer className="composer">
          {chatMutation.isError && <p className="error-message">{getApiError(chatMutation.error)}</p>}
          <div className="composer-row">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder={t(language, 'placeholder')}
              disabled={chatMutation.isPending}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!inputValue.trim() || chatMutation.isPending}
            >
              {t(language, 'send')}
            </button>
          </div>
        </footer>
      </main>
    </div>
  )
}

export default App
