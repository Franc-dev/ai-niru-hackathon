/**
 * VoiceOrb — ElevenLabs Conversational AI (real-time, seamless)
 *
 * ElevenLabs handles everything in one WebSocket:
 *   Mic → ElevenLabs STT → configured LLM → ElevenLabs TTS → Speaker
 *
 * The backend issues a short-lived signed URL so the API key never reaches the browser.
 * The orb glows brighter as microphone / speaker volume rises.
 */
import { Conversation } from '@11labs/client'
import { useEffect, useRef, useState } from 'react'
import './VoiceOrb.css'
import { getStoredToken } from './api/client'
import type { LanguageCode } from './api/queries'
import { t } from './i18n'

/* ─── Types ─────────────────────────────────────────────────────────────── */
type Phase = 'connecting' | 'listening' | 'speaking' | 'error'

interface Bubble { role: 'user' | 'assistant'; text: string }

// Minimal shape we actually use from the SDK's returned session object
interface ConvSession {
  endSession(): Promise<void>
  getInputVolume(): number
  getOutputVolume(): number
}

interface Props {
  language: LanguageCode
  conversationId: string | null
  onClose: () => void
  onConversationId: (id: string) => void
  onLanguageChange: (lang: LanguageCode) => void
}

/* ─── Constants ─────────────────────────────────────────────────────────── */
const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/api/v1'

/* ─── Component ─────────────────────────────────────────────────────────── */
export default function VoiceOrb({
  language,
  onClose,
  onLanguageChange,
}: Props) {
  const [phase, setPhase]     = useState<Phase>('connecting')
  const [bubbles, setBubbles] = useState<Bubble[]>([])
  const [errMsg, setErrMsg]   = useState('')

  const sessionRef  = useRef<ConvSession | null>(null)
  const animRef     = useRef<number>()
  const phaseRef    = useRef<Phase>('connecting')
  const orbRef      = useRef<HTMLDivElement>(null)

  const go = (p: Phase) => { phaseRef.current = p; setPhase(p) }

  /* ── Volume animation: drive orb glow via CSS custom property ─────── */
  const startVolumeLoop = (session: ConvSession) => {
    const tick = () => {
      const vol =
        phaseRef.current === 'speaking'
          ? session.getOutputVolume()
          : session.getInputVolume()
      orbRef.current?.style.setProperty('--vol', String(vol))
      animRef.current = requestAnimationFrame(tick)
    }
    animRef.current = requestAnimationFrame(tick)
  }

  /* ── Main effect: connect to ElevenLabs Conversational AI ─────────── */
  useEffect(() => {
    let mounted = true

    const connect = async () => {
      go('connecting')
      setErrMsg('')

      /* 1. Get signed WebSocket URL from our backend (keeps API key safe) */
      let signedUrl: string
      try {
        const res = await fetch(`${API_BASE}/voice/convai/token?lang=${language}`, {
          headers: { Authorization: `Bearer ${getStoredToken() ?? ''}` },
        })
        if (!res.ok) {
          const body = await res.json().catch(() => ({})) as { detail?: string }
          throw new Error(body.detail ?? `Token error ${res.status}`)
        }
        const data = await res.json() as { signed_url: string }
        signedUrl = data.signed_url
      } catch (err) {
        if (mounted) {
          setErrMsg(err instanceof Error ? err.message : 'Could not connect')
          go('error')
        }
        return
      }

      if (!mounted) return

      /* 2. Open ElevenLabs Conversational AI session */
      try {
        const session = await Conversation.startSession({
          signedUrl,

          onConnect: () => {
            if (mounted) go('listening')
          },

          onDisconnect: () => {
            if (mounted && phaseRef.current !== 'error') go('listening')
          },

          onModeChange: ({ mode }) => {
            if (!mounted) return
            // SDK passes mode as a string: 'listening' | 'speaking'
            const m = typeof mode === 'object' ? (mode as { mode: string }).mode : mode
            go(m === 'speaking' ? 'speaking' : 'listening')
          },

          onMessage: ({ message, source }) => {
            if (!mounted) return
            setBubbles(prev => [
              ...prev,
              { role: source === 'user' ? 'user' : 'assistant', text: message },
            ])
          },

          onError: (msg) => {
            if (!mounted) return
            setErrMsg(typeof msg === 'string' ? msg : 'Voice error')
            go('error')
          },
        }) as ConvSession

        if (!mounted) { session.endSession(); return }

        sessionRef.current = session
        startVolumeLoop(session)
      } catch (err) {
        if (mounted) {
          setErrMsg(err instanceof Error ? err.message : 'Connection failed')
          go('error')
        }
      }
    }

    connect()

    return () => {
      mounted = false
      if (animRef.current) cancelAnimationFrame(animRef.current)
      sessionRef.current?.endSession()
      sessionRef.current = null
    }
  }, [language]) // reconnect with new agent when language toggles

  const handleClose = async () => {
    if (animRef.current) cancelAnimationFrame(animRef.current)
    await sessionRef.current?.endSession()
    onClose()
  }

  /* ─── Render ─────────────────────────────────────────────────────────── */
  const label = (): string => {
    if (errMsg)                    return errMsg
    if (phase === 'connecting')    return language === 'sw' ? 'Inaunganisha...' : 'Connecting...'
    if (phase === 'listening')     return t(language, 'listening')
    if (phase === 'speaking')      return t(language, 'speaking')
    return t(language, 'voiceError')
  }

  return (
    <div className="voice-orb-overlay" onClick={handleClose}>
      <div className="voice-orb-panel" onClick={e => e.stopPropagation()}>

        {/* Language toggle */}
        <div className="voice-lang-toggle">
          <button type="button" className={language === 'en' ? 'active' : ''} onClick={() => onLanguageChange('en')}>EN</button>
          <button type="button" className={language === 'sw' ? 'active' : ''} onClick={() => onLanguageChange('sw')}>SW</button>
        </div>

        {/* Orb + ripple rings */}
        <div className={`voice-orb-wrapper state-${phase}`}>
          <div className="voice-ripple" />
          <div className="voice-ripple" />
          <div className="voice-ripple" />
          <div
            ref={orbRef}
            className={`voice-orb state-${phase}`}
            style={{ '--vol': '0' } as React.CSSProperties}
          />
        </div>

        {/* Waveform bars */}
        <div className={`voice-waveform state-${phase}`}>
          {Array.from({ length: 12 }, (_, i) => (
            <span key={i} style={{ '--i': i } as React.CSSProperties} />
          ))}
        </div>

        {/* State label */}
        <div className="voice-state-label">{label()}</div>

        {/* Conversation bubbles */}
        {bubbles.length > 0 && (
          <div className="voice-history">
            {bubbles.slice(-6).map((b, i) => (
              <div key={i} className={`voice-bubble voice-bubble-${b.role}`}>{b.text}</div>
            ))}
          </div>
        )}

        {/* Stop */}
        <button type="button" className="voice-stop-btn" onClick={handleClose}>
          {t(language, 'stopVoice')}
        </button>

      </div>
    </div>
  )
}
