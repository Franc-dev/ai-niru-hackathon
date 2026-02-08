import { useState, useRef, useEffect } from 'react'
import './App.css'
import { useChatMutation, useChatHistory } from './api/queries'

function App() {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const chatMutation = useChatMutation()
  const { data: historyData } = useChatHistory(conversationId ?? '')

  const messages = historyData?.messages ?? []

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const text = inputValue.trim()
    if (!text || chatMutation.isPending) return
    setInputValue('')
    chatMutation.mutate(
      { message: text, conversation_id: conversationId ?? undefined },
      {
        onSuccess: (data) => {
          setConversationId(data.conversation_id)
        },
      }
    )
  }

  const handleNewConversation = () => {
    setConversationId(null)
  }

  return (
    <div className="App">
      <header className="chat-header">
        <h1>AI Niru</h1>
        <button type="button" className="new-chat-btn" onClick={handleNewConversation}>
          New conversation
        </button>
      </header>

      <div className="messages-container">
        {messages.length === 0 && !chatMutation.isPending && (
          <p className="placeholder">Send a message to start. Ask about the project to try RAG.</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message message-${msg.role}`}>
            <span className="message-role">{msg.role}</span>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        {chatMutation.isPending && (
          <div className="message message-assistant">
            <span className="message-role">assistant</span>
            <div className="message-content typing">Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        {chatMutation.isError && (
          <p className="error">
            {chatMutation.error && typeof chatMutation.error === 'object' && 'response' in chatMutation.error
              ? (chatMutation.error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Request failed'
              : chatMutation.error instanceof Error
                ? chatMutation.error.message
                : 'Something went wrong'}
          </p>
        )}
        <div className="input-row">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Type a message..."
            disabled={chatMutation.isPending}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!inputValue.trim() || chatMutation.isPending}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
