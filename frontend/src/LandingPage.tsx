import { useEffect, useState } from 'react'
import type { LanguageCode } from './api/queries'
import MarketingChrome from './MarketingChrome'
import './LandingPage.css'
import { marketingLabels, type PolicyType } from './marketingContent'

interface LandingPageProps {
  onGetStarted: () => void
  onLogin: () => void
  language: LanguageCode
  onLanguageChange: (lang: LanguageCode) => void
  onNavigate: (page: PolicyType) => void
}

const content = {
  en: {
    heroTagline: 'Your companion for',
    heroHighlight: 'mental wellness',
    heroSub: 'A safe space to talk, reflect, and grow. Elevana listens without judgment.',
    getStarted: 'Begin your journey',
    learnMore: 'Learn more',
    heroEyebrow: 'Mental Health Support',
    features: [
      {
        title: 'Always here for you',
        desc: '24/7 support whenever you need someone to talk to. No appointments, no waiting rooms.',
      },
      {
        title: 'Judgment-free zone',
        desc: 'Express yourself openly. Your thoughts and feelings are safe with us.',
      },
      {
        title: 'Personalized care',
        desc: 'Conversations adapted to your needs, pace, and emotional state.',
      },
    ],
    sectionTitle: 'Why Elevana?',
    sectionSubtitle: 'More than a conversation',
    sectionDesc: 'We believe everyone deserves access to mental health support. Elevana bridges the gap between needing help and finding it.',
    testimonial: '"Having Elevana to talk to during difficult nights has been incredibly comforting. It feels like having a wise friend who truly listens."',
    testimonialAuthor: '- A. M., Dar es Salaam',
    stats: [
      { value: '50K+', label: 'conversations daily' },
      { value: '98%', label: 'feel more supported' },
      { value: '24/7', label: 'always available' },
    ],
    ctaTitle: 'Ready to feel heard?',
    ctaSubtitle: 'Take the first step toward better mental wellness.',
    userBubble: "I've been feeling anxious lately and I don't know why...",
    assistantBubble: 'It takes courage to say that out loud. Would you like to explore what might be sitting underneath those feelings?',
  },
  sw: {
    heroTagline: 'Mshiriki wako kwa',
    heroHighlight: 'afya ya akili',
    heroSub: 'Nafasi salama ya kuongea, kufikiri, na kukua. Elevana husikiliza bila hukumu.',
    getStarted: 'Anza safari yako',
    learnMore: 'Jifunze zaidi',
    heroEyebrow: 'Msaada wa Afya ya Akili',
    features: [
      {
        title: 'Daima hapa kwa ajili yako',
        desc: 'Msaada wa saa zote unapohitaji mtu wa kuzungumza naye. Hakuna miadi wala kusubiri.',
      },
      {
        title: 'Nafasi bila hukumu',
        desc: 'Jieleze kwa uhuru. Mawazo na hisia zako ziko salama nasi.',
      },
      {
        title: 'Huduma ya kibinafsi',
        desc: 'Mazungumzo yanayoendana na mahitaji yako, mwendo wako, na hali yako ya kihisia.',
      },
    ],
    sectionTitle: 'Kwa nini Elevana?',
    sectionSubtitle: 'Zaidi ya mazungumzo',
    sectionDesc: 'Tunaamini kila mtu anastahili kupata msaada wa afya ya akili. Elevana inaziba pengo kati ya kuhitaji msaada na kuupata.',
    testimonial: '"Kuwa na Elevana wa kuongea naye wakati wa usiku mgumu kumekuwa faraja kubwa. Ni kama kuwa na rafiki mwerevu anayesikiliza kweli."',
    testimonialAuthor: '- A. M., Dar es Salaam',
    stats: [
      { value: '50K+', label: 'mazungumzo kila siku' },
      { value: '98%', label: 'wanahisi kusaidiwa' },
      { value: '24/7', label: 'ipo kila saa' },
    ],
    ctaTitle: 'Uko tayari kusikilizwa?',
    ctaSubtitle: 'Chukua hatua ya kwanza kuelekea ustawi bora wa afya ya akili.',
    userBubble: 'Nimekuwa nikihisi wasiwasi siku hizi na sijui kwa nini...',
    assistantBubble: 'Inahitaji ujasiri kusema hilo kwa sauti. Je, ungependa tuangalie kilicho nyuma ya hisia hizo?',
  },
}

function FloatingShape({ className, delay = 0 }: { className: string; delay?: number }) {
  return <div className={`floating-shape ${className}`} style={{ animationDelay: `${delay}s` }} />
}

export default function LandingPage({
  onGetStarted,
  onLogin,
  language,
  onLanguageChange,
  onNavigate,
}: LandingPageProps) {
  const [isVisible, setIsVisible] = useState(false)
  const t = content[language]
  const labels = marketingLabels[language]

  useEffect(() => {
    setIsVisible(true)
    window.scrollTo(0, 0)
  }, [])

  const scrollToFeatures = () => {
    document.querySelector('.features-section')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className={`landing-page ${isVisible ? 'visible' : ''}`}>
      <FloatingShape className="shape-1" delay={0} />
      <FloatingShape className="shape-2" delay={0.5} />
      <FloatingShape className="shape-3" delay={1} />
      <FloatingShape className="shape-4" delay={1.5} />
      <FloatingShape className="shape-5" delay={2} />

      <MarketingChrome
        language={language}
        onLanguageChange={onLanguageChange}
        onNavigatePolicy={onNavigate}
        onLogin={onLogin}
        onBrandClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        labels={labels}
        footerTagline={labels.footerTagline}
        primaryAction={{ label: t.getStarted, onClick: onGetStarted }}
      >
        <section className="hero-section">
          <div className="landing-container">
            <div className="hero-content">
              <p className="hero-eyebrow">{t.heroEyebrow}</p>
              <h1 className="hero-title">
                {t.heroTagline}{' '}
                <span className="hero-highlight">{t.heroHighlight}</span>
              </h1>
              <p className="hero-subtitle">{t.heroSub}</p>
              <div className="hero-actions">
                <button type="button" className="btn-primary" onClick={onGetStarted}>
                  {t.getStarted}
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 10H16M16 10L11 5M16 10L11 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                <button type="button" className="btn-secondary" onClick={scrollToFeatures}>
                  {t.learnMore}
                </button>
              </div>
            </div>

            <div className="hero-visual">
              <div className="visual-card">
                <div className="chat-preview">
                  <div className="chat-bubble user">
                    <span>{t.userBubble}</span>
                  </div>
                  <div className="chat-bubble assistant">
                    <span>{t.assistantBubble}</span>
                  </div>
                </div>
              </div>
              <div className="visual-glow" />
            </div>
          </div>
        </section>

        <section className="features-section">
          <div className="landing-container">
            <div className="section-header">
              <p className="section-eyebrow">{t.sectionTitle}</p>
              <h2 className="section-title">{t.sectionSubtitle}</h2>
              <p className="section-desc">{t.sectionDesc}</p>
            </div>

            <div className="features-grid">
              {t.features.map((feature, index) => (
                <div key={feature.title} className="feature-card" style={{ animationDelay: `${index * 0.15}s` }}>
                  <div className="feature-number">0{index + 1}</div>
                  <h3 className="feature-title">{feature.title}</h3>
                  <p className="feature-desc">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="stats-section">
          <div className="landing-container">
            <div className="stats-grid">
              {t.stats.map((stat) => (
                <div key={stat.label} className="stat-item">
                  <span className="stat-value">{stat.value}</span>
                  <span className="stat-label">{stat.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="testimonial-section">
          <div className="landing-container">
            <blockquote className="testimonial">
              <p>{t.testimonial}</p>
              <cite>{t.testimonialAuthor}</cite>
            </blockquote>
          </div>
        </section>

        <section className="cta-section">
          <div className="landing-container">
            <div className="cta-content">
              <h2>{t.ctaTitle}</h2>
              <p>{t.ctaSubtitle}</p>
              <button type="button" className="btn-primary large" onClick={onGetStarted}>
                {t.getStarted}
              </button>
            </div>
          </div>
        </section>
      </MarketingChrome>
    </div>
  )
}
