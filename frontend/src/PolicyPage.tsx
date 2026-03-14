import { useEffect, useState } from 'react'
import type { LanguageCode } from './api/queries'
import MarketingChrome from './MarketingChrome'
import './PolicyPage.css'
import { marketingLabels, policyContent, type PolicyType } from './marketingContent'

interface PolicyPageProps {
  onBack: () => void
  onLogin: () => void
  onNavigate: (policy: PolicyType) => void
  language: LanguageCode
  onLanguageChange: (lang: LanguageCode) => void
  policyType: PolicyType
}

function FloatingShape({ className, delay = 0 }: { className: string; delay?: number }) {
  return <div className={`floating-shape ${className}`} style={{ animationDelay: `${delay}s` }} />
}

export { type PolicyType }

export default function PolicyPage({
  onBack,
  onLogin,
  onNavigate,
  language,
  onLanguageChange,
  policyType,
}: PolicyPageProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    setIsVisible(true)
    window.scrollTo(0, 0)
  }, [policyType])

  const labels = marketingLabels[language]
  const policy = policyContent[language][policyType]

  return (
    <div className={`landing-page policy-page-wrapper ${isVisible ? 'visible' : ''}`}>
      <FloatingShape className="shape-1 opacity-reduced" delay={0} />
      <FloatingShape className="shape-2 opacity-reduced" delay={0.5} />
      <FloatingShape className="shape-3 opacity-reduced" delay={1} />

      <MarketingChrome
        language={language}
        onLanguageChange={onLanguageChange}
        onNavigatePolicy={onNavigate}
        onLogin={onLogin}
        onBrandClick={onBack}
        labels={labels}
        footerTagline={labels.footerTagline}
        primaryAction={{ label: labels.home, onClick: onBack }}
        activePolicy={policyType}
      >
        <main className="policy-main">
          <div className="landing-container">
            <div className="policy-content-card visual-card">
              <div className="policy-intro">
                <p className="policy-kicker">{labels.legal}</p>
                <h1 className="policy-title hero-title">{policy.title}</h1>
                <p className="policy-updated">{policy.lastUpdated}</p>
              </div>

              <div className="policy-body">
                {policy.sections.map((section) => (
                  <section key={section.heading} className="policy-section">
                    <h2 className="policy-heading">{section.heading}</h2>
                    <p className="policy-paragraph">{section.body}</p>
                  </section>
                ))}
              </div>
            </div>
          </div>
        </main>
      </MarketingChrome>
    </div>
  )
}
