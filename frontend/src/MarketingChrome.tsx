import { useEffect, useState, type ReactNode } from 'react'
import type { LanguageCode } from './api/queries'
import './MarketingChrome.css'
import type { MarketingLabels, PolicyType } from './marketingContent'

type ActionConfig = {
  label: string
  onClick: () => void
}

type MarketingChromeProps = {
  language: LanguageCode
  onLanguageChange: (lang: LanguageCode) => void
  onNavigatePolicy: (policy: PolicyType) => void
  onLogin: () => void
  onBrandClick: () => void
  labels: MarketingLabels
  footerTagline: string
  primaryAction: ActionConfig
  activePolicy?: PolicyType | null
  children: ReactNode
}

const policyOrder: PolicyType[] = ['privacy', 'cookie', 'terms']

export default function MarketingChrome({
  language,
  onLanguageChange,
  onNavigatePolicy,
  onLogin,
  onBrandClick,
  labels,
  footerTagline,
  primaryAction,
  activePolicy = null,
  children,
}: MarketingChromeProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 18)
    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    if (!menuOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpen(false)
      }
    }

    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [menuOpen])

  const policyLabelMap: Record<PolicyType, string> = {
    privacy: labels.privacy,
    cookie: labels.cookie,
    terms: labels.terms,
  }

  const policyButtons = policyOrder.map((policy) => (
    <button
      key={policy}
      type="button"
      className={`marketing-link ${activePolicy === policy ? 'active' : ''}`}
      onClick={() => {
        onNavigatePolicy(policy)
        setMenuOpen(false)
      }}
      aria-current={activePolicy === policy ? 'page' : undefined}
    >
      {policyLabelMap[policy]}
    </button>
  ))

  return (
    <>
      <header className={`marketing-header ${isScrolled ? 'is-scrolled' : ''}`}>
        <div className="landing-container marketing-header-inner">
          <button type="button" className="marketing-brand" onClick={onBrandClick}>
            <span className="brand-icon">e</span>
            <span className="brand-name">Elevana</span>
          </button>

          <div className="marketing-desktop-nav">
            <div className="marketing-link-row">{policyButtons}</div>
            <button type="button" className="marketing-link" onClick={onLogin}>
              {labels.login}
            </button>
            <div className="language-switcher marketing-language-switcher" aria-label={labels.language}>
              <button
                type="button"
                className={language === 'en' ? 'active' : ''}
                onClick={() => onLanguageChange('en')}
              >
                EN
              </button>
              <button
                type="button"
                className={language === 'sw' ? 'active' : ''}
                onClick={() => onLanguageChange('sw')}
              >
                SW
              </button>
            </div>
            <button type="button" className="nav-cta marketing-primary-cta" onClick={primaryAction.onClick}>
              {primaryAction.label}
            </button>
          </div>

          <div className="marketing-mobile-actions">
            <button type="button" className="nav-cta marketing-primary-cta mobile" onClick={primaryAction.onClick}>
              {primaryAction.label}
            </button>
            <button
              type="button"
              className={`marketing-menu-toggle ${menuOpen ? 'open' : ''}`}
              onClick={() => setMenuOpen((open) => !open)}
              aria-expanded={menuOpen}
              aria-controls="marketing-mobile-menu"
              aria-label={menuOpen ? labels.closeMenu : labels.menu}
            >
              <span />
              <span />
              <span />
            </button>
          </div>
        </div>
      </header>

      {menuOpen && (
        <div className="marketing-mobile-overlay" onClick={() => setMenuOpen(false)}>
          <div
            id="marketing-mobile-menu"
            className="marketing-mobile-sheet"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="marketing-mobile-top">
              <p className="marketing-mobile-eyebrow">{labels.legal}</p>
              <button
                type="button"
                className="marketing-mobile-close"
                onClick={() => setMenuOpen(false)}
                aria-label={labels.closeMenu}
              >
                {labels.closeMenu}
              </button>
            </div>

            <div className="marketing-mobile-links">{policyButtons}</div>

            <div className="marketing-mobile-language">
              <p>{labels.language}</p>
              <div className="language-switcher marketing-language-switcher" aria-label={labels.language}>
                <button
                  type="button"
                  className={language === 'en' ? 'active' : ''}
                  onClick={() => onLanguageChange('en')}
                >
                  EN
                </button>
                <button
                  type="button"
                  className={language === 'sw' ? 'active' : ''}
                  onClick={() => onLanguageChange('sw')}
                >
                  SW
                </button>
              </div>
            </div>

            <div className="marketing-mobile-cta-group">
              <button type="button" className="marketing-secondary-button" onClick={() => { onLogin(); setMenuOpen(false) }}>
                {labels.login}
              </button>
              <button
                type="button"
                className="nav-cta marketing-primary-cta mobile-sheet"
                onClick={() => {
                  primaryAction.onClick()
                  setMenuOpen(false)
                }}
              >
                {primaryAction.label}
              </button>
            </div>

            <a className="marketing-contact-link" href="mailto:hello@elevana.com">
              {labels.contact}
            </a>
          </div>
        </div>
      )}

      {children}

      <footer className="landing-footer marketing-footer">
        <div className="landing-container marketing-footer-inner">
          <p className="footer-tagline">{footerTagline}</p>
          <div className="footer-links marketing-footer-links">
            {policyButtons}
            <button type="button" className="marketing-link" onClick={onLogin}>
              {labels.login}
            </button>
            <a className="marketing-link marketing-link-anchor" href="mailto:hello@elevana.com">
              {labels.contact}
            </a>
          </div>
        </div>
      </footer>
    </>
  )
}
