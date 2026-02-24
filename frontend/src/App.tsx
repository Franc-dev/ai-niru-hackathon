import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { clearStoredToken, getStoredToken, setStoredToken } from './api/client'
import {
  type ChatMessage,
  type LanguageCode,
  useArchiveConversationMutation,
  useChatHistory,
  useChatMutation,
  useConversationListQuery,
  useDeleteConversationMutation,
  useDeleteMessageMutation,
  useEditConversationTitleMutation,
  useEditMessageMutation,
  useLoginMutation,
  useMeQuery,
  usePinConversationMutation,
  useSignupMutation,
  useUpdateLanguageMutation,
import { getLanguageLabel, t } from './i18n'
import LandingPage from './LandingPage'
import PolicyPage, { PolicyType } from './PolicyPage'
import VoiceOrb from './VoiceOrb'

const LANGUAGE_STORAGE_KEY = 'ai_niru_language'
const SKELETON_COUNT = 5

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

function MarkdownContent({ content }: { content: string }) {
  const formatInline = (text: string): React.ReactNode => {
    const parts: React.ReactNode[] = []
    let rest = text
    let key = 0
    while (rest.length > 0) {
      const boldMatch = rest.match(/\*\*(.+?)\*\*/)
      if (boldMatch && boldMatch.index !== undefined) {
        if (boldMatch.index > 0) parts.push(<span key={key++}>{rest.slice(0, boldMatch.index)}</span>)
        parts.push(<strong key={key++}>{boldMatch[1]}</strong>)
        rest = rest.slice(boldMatch.index + boldMatch[0].length)
      } else {
        parts.push(<span key={key++}>{rest}</span>)
        break
      }
    }
    return parts.length === 1 ? parts[0] : <>{parts}</>
  }
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []
  let listItems: { text: string; ordered: boolean }[] = []
  const flushList = () => {
    if (listItems.length === 0) return
    const ordered = listItems[0].ordered
    const ListTag = ordered ? 'ol' : 'ul'
    elements.push(
      <ListTag key={elements.length} className="md-list">
        {listItems.map((item, i) => (
          <li key={i}>{formatInline(item.text)}</li>
        ))}
      </ListTag>
    )
    listItems = []
  }
  for (const line of lines) {
    const olMatch = line.match(/^(\d+)\.\s+(.+)$/)
    const ulMatch = line.match(/^[-*]\s+(.+)$/)
    if (olMatch) {
      if (listItems.length > 0 && !listItems[0].ordered) flushList()
      listItems.push({ text: olMatch[2], ordered: true })
    } else if (ulMatch) {
      if (listItems.length > 0 && listItems[0].ordered) flushList()
      listItems.push({ text: ulMatch[1], ordered: false })
    } else {
      flushList()
      if (line.trim()) elements.push(<p key={elements.length}>{formatInline(line)}</p>)
    }
  }
  flushList()
  return <div className="md-content">{elements}</div>
}

function TypingDots() {
  return (
    <span className="typing-dots">
      <span />
      <span />
      <span />
    </span>
  )
}

function MessageSkeleton({ align }: { align: 'left' | 'right' }) {
  return (
    <div className={`message-wrapper ${align === 'right' ? 'message-wrapper-user' : ''}`}>
      <div className={`message message-${align === 'right' ? 'user' : 'assistant'}`}>
        <div className="skeleton-role" />
        <div className={`skeleton-bubble skeleton-bubble-${align}`}>
          <div className="skeleton-line" style={{ width: '85%' }} />
          <div className="skeleton-line" style={{ width: '60%' }} />
        </div>
      </div>
    </div>
  )
}

function ChatSkeleton() {
  return (
    <>
      {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
        <MessageSkeleton key={i} align={i % 2 === 0 ? 'right' : 'left'} />
      ))}
    </>
  )
}

function ConfirmDialog({
  message,
  language,
  onConfirm,
  onCancel,
}: {
  message: string
  language: LanguageCode
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div className="confirm-dialog-overlay" onClick={onCancel}>
      <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
        <p>{message}</p>
        <div className="confirm-dialog-actions">
          <button type="button" className="btn-cancel" onClick={onCancel}>
            {t(language, 'cancel')}
          </button>
          <button type="button" className="btn-danger" onClick={onConfirm}>
            {t(language, 'delete')}
          </button>
        </div>
      </div>
    </div>
  )
}

type AppScreen = 'landing' | 'auth' | 'app' | 'policy'

function App() {
  const [screen, setScreen] = useState<AppScreen>(() => {
    if (getStoredToken()) return 'app'
    return 'landing'
  })
  const [activePolicy, setActivePolicy] = useState<PolicyType>('privacy')
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
  const [optimisticMessages, setOptimisticMessages] = useState<ChatMessage[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const [editingTitleId, setEditingTitleId] = useState<string | null>(null)
  const [editingTitleValue, setEditingTitleValue] = useState('')
  const [isVoiceOpen, setIsVoiceOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<{ type: 'conversation' | 'message'; id: string; secondaryId?: string } | null>(null)
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editingMessageContent, setEditingMessageContent] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const userChangedLanguageRef = useRef(false)
  const initialLanguageSyncedRef = useRef(false)

  const signupMutation = useSignupMutation()
  const loginMutation = useLoginMutation()
  const updateLanguageMutation = useUpdateLanguageMutation()
  const chatMutation = useChatMutation()
  const deleteConversationMutation = useDeleteConversationMutation()
  const editTitleMutation = useEditConversationTitleMutation()
  const pinMutation = usePinConversationMutation()
  const archiveMutation = useArchiveConversationMutation()
  const deleteMessageMutation = useDeleteMessageMutation()
  const editMessageMutation = useEditMessageMutation()
  const { data: meData } = useMeQuery(isAuthenticated)
  const { data: conversationList = [] } = useConversationListQuery(isAuthenticated)
  const { data: historyData, isLoading: isHistoryLoading } = useChatHistory(conversationId ?? '', isAuthenticated && !!conversationId)

  // When in draft mode (new conversation), ignore stale historyData from keepPreviousData
  const apiMessages = isDraftConversation ? [] : (historyData?.messages ?? [])
  const displayMessages = useMemo(() => {
    if (optimisticMessages.length === 0) return apiMessages
    // Merge: show API messages + optimistic ones not yet in API response
    const apiContentSet = new Set(apiMessages.map((m) => `${m.role}:${m.content}`))
    const extras = optimisticMessages.filter((om) => !apiContentSet.has(`${om.role}:${om.content}`))
    return [...apiMessages, ...extras]
  }, [apiMessages, optimisticMessages])

  const sortedConversations = useMemo(() => {
    return [...conversationList].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1
      if (!a.pinned && b.pinned) return 1
      const aTime = a.updated_at ?? ''
      const bTime = b.updated_at ?? ''
      return bTime.localeCompare(aTime)
    })
  }, [conversationList])

  const activeConversation = useMemo(
    () => conversationList.find((item) => item.conversation_id === conversationId),
    [conversationId, conversationList]
  )
  const chatTitle = isDraftConversation
    ? t(language, 'newConversation')
    : (historyData?.title || activeConversation?.title || t(language, 'newConversation'))
  const isAuthLoading = signupMutation.isPending || loginMutation.isPending
  const translatedAuthHint = t(language, 'authHint')

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [displayMessages])

  // Only sync server language preference on initial load, never override explicit user choice
  useEffect(() => {
    if (!isAuthenticated || !meData?.preferred_language) return
    if (initialLanguageSyncedRef.current) return
    initialLanguageSyncedRef.current = true
    if (meData.preferred_language !== language) {
      setLanguage(meData.preferred_language)
      localStorage.setItem(LANGUAGE_STORAGE_KEY, meData.preferred_language)
    }
  }, [isAuthenticated, meData?.preferred_language]) // eslint-disable-line react-hooks/exhaustive-deps

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

  // Clear optimistic messages when API messages update
  useEffect(() => {
    if (apiMessages.length > 0 && optimisticMessages.length > 0) {
      setOptimisticMessages([])
    }
  }, [apiMessages, optimisticMessages.length])

  // Close menu when clicking outside
  useEffect(() => {
    if (!openMenuId) return
    const handler = () => setOpenMenuId(null)
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [openMenuId])

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
            setScreen('app')
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
          setScreen('app')
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
    userChangedLanguageRef.current = true
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
    // Optimistic: immediately show user message
    setOptimisticMessages((prev) => [...prev, { role: 'user', content: text }])
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
    setOptimisticMessages([])
    setInputValue('')
    setEditingMessageId(null)
    chatMutation.reset()
    setSidebarOpen(false)
  }

  const handleSelectConversation = (nextConversationId: string) => {
    setConversationId(nextConversationId)
    setIsDraftConversation(false)
    setOptimisticMessages([])
    setSidebarOpen(false)
  }

  const handleLogout = () => {
    clearStoredToken()
    setIsAuthenticated(false)
    setScreen('landing')
    setConversationId(null)
    setIsDraftConversation(false)
    resetAuthForm()
  }

  const handleDeleteConversation = useCallback((id: string) => {
    setConfirmDelete({ type: 'conversation', id })
    setOpenMenuId(null)
  }, [])

  const handleConfirmDelete = useCallback(() => {
    if (!confirmDelete) return
    if (confirmDelete.type === 'conversation') {
      deleteConversationMutation.mutate(confirmDelete.id, {
        onSuccess: () => {
          if (conversationId === confirmDelete.id) {
            setConversationId(null)
            setIsDraftConversation(true)
          }
        },
      })
    } else if (confirmDelete.type === 'message' && confirmDelete.secondaryId) {
      deleteMessageMutation.mutate({
        conversationId: confirmDelete.secondaryId,
        messageId: confirmDelete.id,
      })
    }
    setConfirmDelete(null)
  }, [confirmDelete, conversationId, deleteConversationMutation, deleteMessageMutation])

  const handleEditTitle = useCallback((id: string, currentTitle: string) => {
    setEditingTitleId(id)
    setEditingTitleValue(currentTitle)
    setOpenMenuId(null)
  }, [])

  const handleSaveTitle = useCallback(() => {
    if (!editingTitleId || !editingTitleValue.trim()) return
    editTitleMutation.mutate({ conversationId: editingTitleId, title: editingTitleValue.trim() })
    setEditingTitleId(null)
    setEditingTitleValue('')
  }, [editingTitleId, editingTitleValue, editTitleMutation])

  const handleTogglePin = useCallback(
    (id: string, currentPinned: boolean) => {
      pinMutation.mutate({ conversationId: id, pinned: !currentPinned })
      setOpenMenuId(null)
    },
    [pinMutation]
  )

  const handleToggleArchive = useCallback(
    (id: string, currentArchived: boolean) => {
      archiveMutation.mutate({ conversationId: id, archived: !currentArchived })
      setOpenMenuId(null)
      if (!currentArchived && conversationId === id) {
        setConversationId(null)
        setIsDraftConversation(true)
      }
    },
    [archiveMutation, conversationId]
  )

  const handleDeleteMessage = useCallback(
    (messageId: string) => {
      if (!conversationId) return
      setConfirmDelete({ type: 'message', id: messageId, secondaryId: conversationId })
    },
    [conversationId]
  )

  const handleEditMessage = useCallback((messageId: string, content: string) => {
    setEditingMessageId(messageId)
    setEditingMessageContent(content)
  }, [])

  const handleSaveMessageEdit = useCallback(() => {
    if (!editingMessageId || !conversationId || !editingMessageContent.trim()) return
    editMessageMutation.mutate({
      conversationId,
      messageId: editingMessageId,
      content: editingMessageContent.trim(),
    })
    setEditingMessageId(null)
    setEditingMessageContent('')
  }, [editingMessageId, conversationId, editingMessageContent, editMessageMutation])

  const handleRetry = useCallback(
    (messageId: string, precedingUserMessage: ChatMessage | undefined) => {
      if (!conversationId || !precedingUserMessage) return
      // Delete the assistant message, then resend the user message
      deleteMessageMutation.mutate(
        { conversationId, messageId },
        {
          onSuccess: () => {
            chatMutation.mutate(
              { message: precedingUserMessage.content, conversation_id: conversationId, language },
              {
                onSuccess: (data) => {
                  setConversationId(data.conversation_id)
                },
              }
            )
          },
        }
      )
    },
    [conversationId, deleteMessageMutation, chatMutation, language]
  )

  const handleGetStarted = () => {
    setScreen('auth')
  }

  if (screen === 'landing') {
    return (
      <LandingPage
        onGetStarted={handleGetStarted}
        language={language}
        onLanguageChange={handleLanguageChange}
        onNavigate={(policy) => {
          setActivePolicy(policy)
          setScreen('policy')
        }}
      />
    )
  }

  if (screen === 'policy') {
    return (
      <PolicyPage
        onBack={() => setScreen('landing')}
        language={language}
        onLanguageChange={handleLanguageChange}
        policyType={activePolicy}
      />
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="auth-screen">
        <div className="auth-visual">
          <div className="auth-visual-content">
            <div className="auth-visual-icon">e</div>
            <h2>{t(language, 'appName')}</h2>
            <p>{language === 'en' ? 'Your companion for mental wellness. A safe space to talk, reflect, and grow.' : 'Mshiriki wako kwa afya ya akili. Nafasi salama ya kuongea, kufikiri, na kukua.'}</p>
          </div>
        </div>
        <div className="auth-form-container">
          <div className="auth-card">
            <button
              type="button"
              className="auth-back"
              onClick={() => setScreen('landing')}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              {language === 'en' ? 'Back' : 'Rudi'}
            </button>
            <p className="auth-kicker">{authMode === 'login' ? (language === 'en' ? 'Welcome back' : 'Karibu tena') : (language === 'en' ? 'Create account' : 'Fungua akaunti')}</p>
            <h1>{authMode === 'login' ? (language === 'en' ? 'Sign in to your account' : 'Ingia kwenye akaunti yako') : (language === 'en' ? 'Create your account' : 'Fungua akaunti yako')}</h1>
            <p className="auth-subtitle">{translatedAuthHint}</p>
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
                placeholder={language === 'en' ? 'Enter your email' : 'Weka barua pepe yako'}
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
                  placeholder={language === 'en' ? 'Your name (optional)' : 'Jina lako (si lazima)'}
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
                placeholder={language === 'en' ? 'Enter your password' : 'Weka nenosiri lako'}
              />
            </label>
            {(authError || loginMutation.isError || signupMutation.isError) && (
              <p className="error-message">
                {authError || getApiError(loginMutation.error || signupMutation.error)}
              </p>
            )}
            <button type="button" className="auth-submit" onClick={handleAuthSubmit} disabled={isAuthLoading}>
              {isAuthLoading
                ? (language === 'en' ? 'Please wait...' : 'Tafadhali subiri...')
                : (authMode === 'login' ? t(language, 'login') : t(language, 'signup'))}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      {/* Mobile hamburger toggle */}
      <button
        type="button"
        className="sidebar-toggle"
        onClick={() => setSidebarOpen((prev) => !prev)}
        aria-label="Toggle sidebar"
      >
        {sidebarOpen ? '\u2715' : '\u2630'}
      </button>

      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
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
          {sortedConversations.length === 0 && <p className="empty-panel">{t(language, 'noConversations')}</p>}
          {sortedConversations.map((conversation) => {
            const title = conversation.title || t(language, 'newConversation')
            const isEditing = editingTitleId === conversation.conversation_id
            return (
              <div className="conversation-item-wrapper" key={conversation.conversation_id}>
                <button
                  type="button"
                  className={`conversation-item ${conversationId === conversation.conversation_id ? 'active' : ''}`}
                  onClick={() => handleSelectConversation(conversation.conversation_id)}
                >
                  <div className="conversation-title-row">
                    {isEditing ? (
                      <input
                        className="edit-title-input"
                        value={editingTitleValue}
                        onChange={(e) => setEditingTitleValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveTitle()
                          if (e.key === 'Escape') setEditingTitleId(null)
                        }}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                      />
                    ) : (
                      <span className="conversation-title">{title}</span>
                    )}
                    {conversation.pinned && <span className="pinned-badge" title="Pinned">&#128204;</span>}
                  </div>
                  {!isEditing && (
                    <span className="conversation-preview">{conversation.preview || '...'}</span>
                  )}
                </button>

                {/* 3-dot actions menu */}
                <div className="conversation-actions">
                  <button
                    type="button"
                    className={`conversation-actions-trigger ${openMenuId === conversation.conversation_id ? 'open' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation()
                      setOpenMenuId(openMenuId === conversation.conversation_id ? null : conversation.conversation_id)
                    }}
                    aria-label="Actions"
                  >
                    &#8942;
                  </button>
                  {openMenuId === conversation.conversation_id && (
                    <div className="conversation-actions-menu" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => handleEditTitle(conversation.conversation_id, conversation.title || '')}
                      >
                        {t(language, 'editTitle')}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleTogglePin(conversation.conversation_id, !!conversation.pinned)}
                      >
                        {conversation.pinned ? t(language, 'unpin') : t(language, 'pin')}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleToggleArchive(conversation.conversation_id, !!conversation.archived)}
                      >
                        {conversation.archived ? t(language, 'unarchive') : t(language, 'archive')}
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => handleDeleteConversation(conversation.conversation_id)}
                      >
                        {t(language, 'delete')}
                      </button>
                    </div>
                  )}
                </div>
              </div>
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
          {/* Skeleton loader while fetching chat history */}
          {isHistoryLoading && conversationId && !isDraftConversation && (
            <ChatSkeleton />
          )}
          {/* Empty state — only when not loading and no messages */}
          {!isHistoryLoading && displayMessages.length === 0 && !chatMutation.isPending && (
            <div className="empty-chat-state">
              <h3>{t(language, 'welcome')}</h3>
              <p>{t(language, 'startPrompt')}</p>
            </div>
          )}
          {!isHistoryLoading && displayMessages.map((message, index) => {
            const isEditingThis = editingMessageId === message.message_id
            const isUser = message.role === 'user'
            const isAssistant = message.role === 'assistant'
            const precedingUserMsg = isAssistant && index > 0 ? displayMessages[index - 1] : undefined

            return (
              <div
                key={message.message_id || `${message.role}-${index}`}
                className={`message-wrapper ${isUser ? 'message-wrapper-user' : ''}`}
              >
                <div className={`message message-${message.role}`}>
                  <p className="message-role">{message.role === 'assistant' ? 'Elevana' : message.role}</p>
                  {isEditingThis ? (
                    <div className="message-editing">
                      <textarea
                        value={editingMessageContent}
                        onChange={(e) => setEditingMessageContent(e.target.value)}
                      />
                      <div className="message-editing-actions">
                        <button
                          type="button"
                          className="btn-cancel"
                          onClick={() => setEditingMessageId(null)}
                        >
                          {t(language, 'cancel')}
                        </button>
                        <button
                          type="button"
                          className="btn-save"
                          onClick={handleSaveMessageEdit}
                        >
                          {t(language, 'save')}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="message-content">
                      {isAssistant ? <MarkdownContent content={message.content} /> : message.content}
                    </div>
                  )}
                </div>

                {/* Hover toolbar */}
                {message.message_id && !isEditingThis && (
                  <div className="message-toolbar">
                    <button
                      type="button"
                      onClick={() => handleEditMessage(message.message_id!, message.content)}
                      title={t(language, 'edit')}
                    >
                      {t(language, 'edit')}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteMessage(message.message_id!)}
                      title={t(language, 'delete')}
                    >
                      {t(language, 'delete')}
                    </button>
                    {isAssistant && precedingUserMsg && precedingUserMsg.role === 'user' && (
                      <button
                        type="button"
                        onClick={() => handleRetry(message.message_id!, precedingUserMsg)}
                        title={t(language, 'retry')}
                      >
                        {t(language, 'retry')}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )
          })}
          {!isHistoryLoading && chatMutation.isPending && (
            <div className="message-wrapper">
              <div className="message message-assistant pending">
                <p className="message-role">Elevana</p>
                <div className="message-content">
                  <TypingDots />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </section>

        <footer className="composer">
          {chatMutation.isError && <p className="error-message">{getApiError(chatMutation.error)}</p>}
          <div className="composer-row">
            <button
              type="button"
              className="voice-trigger-btn"
              onClick={() => setIsVoiceOpen(true)}
              aria-label={t(language, 'voiceMode')}
              title={t(language, 'voiceMode')}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <rect x="9" y="2" width="6" height="12" rx="3" fill="currentColor" />
                <path d="M5 10a7 7 0 0 0 14 0" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <line x1="12" y1="19" x2="12" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <line x1="9" y1="22" x2="15" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
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

      {/* Voice orb modal */}
      {isVoiceOpen && (
        <VoiceOrb
          language={language}
          conversationId={conversationId}
          onClose={() => setIsVoiceOpen(false)}
          onConversationId={(newConvId) => {
            setConversationId(newConvId)
            setIsDraftConversation(false)
          }}
          onLanguageChange={handleLanguageChange}
        />
      )}

      {/* Confirm delete dialog */}
      {confirmDelete && (
        <ConfirmDialog
          message={t(language, 'confirmDelete')}
          language={language}
          onConfirm={handleConfirmDelete}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  )
}

export default App
