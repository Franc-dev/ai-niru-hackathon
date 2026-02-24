import { useEffect, useState } from 'react'
import './PolicyPage.css'

type LanguageCode = 'en' | 'sw'

export type PolicyType = 'privacy' | 'terms' | 'cookie'

interface PolicyPageProps {
  onBack: () => void
  language: LanguageCode
  onLanguageChange: (lang: LanguageCode) => void
  policyType: PolicyType
}

const content = {
  en: {
    privacy: {
      title: 'Privacy Policy',
      lastUpdated: 'Last Updated: February 2026',
      sections: [
        {
          heading: '1. Information We Collect',
          body: 'We collect information you provide directly to us when using Elevana. This includes conversation history, account details, and preferences. We use this to personalize your mental health support experience.',
        },
        {
          heading: '2. How We Use Your Information',
          body: 'Your information helps us improve our AI models to provide better, more empathetic responses. We prioritize your privacy and do not sell your personal data to third parties. All conversation data is anonymized where possible.',
        },
        {
          heading: '3. Data Security',
          body: 'We implement robust, state-of-the-art security measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction. We use industry-standard encryption for data at rest and in transit.',
        },
        {
          heading: '4. Your Rights',
          body: 'You have the right to access, update, or delete your personal information at any time. If you have questions about our data practices, please contact our support team.',
        }
      ]
    },
    terms: {
      title: 'Terms of Use',
      lastUpdated: 'Last Updated: February 2026',
      sections: [
        {
          heading: '1. Acceptance of Terms',
          body: 'By accessing or using Elevana, you agree to be bound by these Terms of Use and all applicable laws and regulations. If you do not agree with any of these terms, you are prohibited from using or accessing this site.',
        },
        {
          heading: '2. Not Medical Advice',
          body: 'Elevana is an AI companion designed for mental wellness support. It is NOT a replacement for professional medical advice, diagnosis, or treatment. If you are experiencing a crisis or emergency, please contact your local emergency services immediately.',
        },
        {
          heading: '3. User Conduct',
          body: 'You agree to use Elevana only for lawful purposes. You are responsible for all content you provide during your interactions and must not use the service to transmit harmful, threatening, or illegal material.',
        },
        {
          heading: '4. Limitation of Liability',
          body: 'In no event shall Elevana be liable for any damages arising out of the use or inability to use the materials on our platform, even if authorized representatives have been notified orally or in writing of the possibility of such damage.',
        }
      ]
    },
    cookie: {
      title: 'Cookie Policy',
      lastUpdated: 'Last Updated: February 2026',
      sections: [
        {
          heading: '1. What Are Cookies',
          body: 'Cookies are small text files that are placed on your computer or mobile device when you visit our website. They are widely used to make websites work more efficiently and provide information to the owners of the site.',
        },
        {
          heading: '2. How We Use Cookies',
          body: 'We use essential cookies to maintain your login session and language preferences. These are necessary for the core functionality of Elevana and cannot be disabled in our systems.',
        },
        {
          heading: '3. Analytics and Performance',
          body: 'With your consent, we may use performance cookies to understand how visitors interact with our website, helping us improve the user experience and application responsiveness.',
        },
        {
          heading: '4. Managing Cookies',
          body: 'You can control and/or delete cookies as you wish via your browser settings. You can delete all cookies that are already on your computer and set most browsers to prevent them from being placed. However, this may degrade some functionality of Elevana.',
        }
      ]
    },
    back: 'Back to Home'
  },
  sw: {
    privacy: {
      title: 'Sera ya Faragha',
      lastUpdated: 'Ilisasishwa Mwisho: Februari 2026',
      sections: [
        {
          heading: '1. Taarifa Tunazokusanya',
          body: 'Tunakusanya taarifa unazotupatia moja kwa moja unapotumia Elevana. Hii inajumuisha historia ya mazungumzo, maelezo ya akaunti, na mapendeleo. Tunatumia hili kubinafsisha uzoefu wako wa msaada wa afya ya akili.',
        },
        {
          heading: '2. Jinsi Tunavyotumia Taarifa Zako',
          body: 'Taarifa zako zinatusaidia kuboresha mifumo yetu ya AI kutoa majibu bora na yenye uelewa zaidi. Tunathamini faragha yako na hatuuzi data yako ya kibinafsi kwa wahusika wengine. Data yote ya mazungumzo inafichwa utambulisho inapowezekana.',
        },
        {
          heading: '3. Usalama wa Data',
          body: 'Tunatekeleza hatua madhubuti, za kisasa za usalama kulinda taarifa zako za kibinafsi dhidi ya ufikiaji, ubadilishaji, ufichuzi au uharibifu usioidhinishwa. Tunatumia usimbaji fiche wa kiwango cha tasnia kwa data iliyohifadhiwa na inayosafirishwa.',
        },
        {
          heading: '4. Haki Zako',
          body: 'Una haki ya kufikia, kusasisha, au kufuta taarifa zako za kibinafsi wakati wowote. Ikiwa una maswali kuhusu mbinu zetu za data, tafadhali wasiliana na timu yetu ya msaada.',
        }
      ]
    },
    terms: {
      title: 'Masharti ya Matumizi',
      lastUpdated: 'Ilisasishwa Mwisho: Februari 2026',
      sections: [
        {
          heading: '1. Kukubalika kwa Masharti',
          body: 'Kwa kufikia au kutumia Elevana, unakubali kufungwa na Masharti haya ya Matumizi na sheria na kanuni zote zinazotumika. Ikiwa hukubaliani na mojawapo ya masharti haya, unazuiwa kutumia au kufikia tovuti hii.',
        },
        {
          heading: '2. Siyo Ushauri wa Kimatibabu',
          body: 'Elevana ni mshiriki wa AI aliyebuniwa kwa msaada wa afya ya akili. SIO mbadala wa ushauri wa kitaalam wa kimatibabu, utambuzi, au matibabu. Ikiwa unapitia dhiki au dharura, tafadhali wasiliana na huduma za dharura za eneo lako mara moja.',
        },
        {
          heading: '3. Mwenendo wa Mtumiaji',
          body: 'Unakubali kutumia Elevana kwa madhumuni halali pekee. Unawajibika kwa maudhui yote unayotoa wakati wa mwingiliano wako na hupaswi kutumia huduma kusambaza nyenzo hatari, zinazotisha, au haramu.',
        },
        {
          heading: '4. Kikomo cha Dhima',
          body: 'Kwa vyovyote vile Elevana haitawajibika kwa uharibifu wowote unaotokana na matumizi au kushindwa kutumia nyenzo kwenye jukwaa letu, hata kama wawakilishi walioidhinishwa wamearifiwa kwa mdomo au kwa maandishi juu ya uwezekano wa uharibifu huo.',
        }
      ]
    },
    cookie: {
      title: 'Sera ya Vidakuzi (Cookies)',
      lastUpdated: 'Ilisasishwa Mwisho: Februari 2026',
      sections: [
        {
          heading: '1. Vidakuzi ni Nini',
          body: 'Vidakuzi ni faili ndogo za maandishi zinazowekwa kwenye kompyuta yako au kifaa cha mkononi unapotembelea tovuti yetu. Vinatumiwa sana kufanya tovuti zifanye kazi kwa ufanisi zaidi na kutoa taarifa kwa wamiliki wa tovuti.',
        },
        {
          heading: '2. Jinsi Tunavyotumia Vidakuzi',
          body: 'Tunatumia vidakuzi muhimu ili kudumisha kipindi chako cha kuingia na mapendeleo ya lugha. Haya ni muhimu kwa utendaji mkuu wa Elevana na hayawezi kulemazwa katika mifumo yetu.',
        },
        {
          heading: '3. Uchanganuzi na Utendaji',
          body: 'Kwa idhini yako, tunaweza kutumia vidakuzi vya utendaji kuelewa jinsi wageni wanavyotumiliana na tovuti yetu, kutusaidia kuboresha uzoefu wa mtumiaji na uitikiaji wa maombi.',
        },
        {
          heading: '4. Kudhibiti Vidakuzi',
          body: 'Unaweza kudhibiti na/au kufuta vidakuzi upendavyo kupitia mipangilio ya kivinjari chako. Unaweza kufuta vidakuzi vyote ambavyo tayari vipo kwenye kompyuta yako na kuweka vivinjari vingi ili kuzuia visiwekwe. Hata hivyo, hii inaweza kushusha baadhi ya utendaji wa Elevana.',
        }
      ]
    },
    back: 'Rudi Nyumbani'
  },
}

function FloatingShape({ className, delay = 0 }: { className: string; delay?: number }) {
  return (
    <div
      className={`floating-shape ${className}`}
      style={{ animationDelay: `${delay}s` }}
    />
  )
}

export default function PolicyPage({ onBack, language, onLanguageChange, policyType }: PolicyPageProps) {
  const [isVisible, setIsVisible] = useState(false)
  
  useEffect(() => {
    setIsVisible(true)
    window.scrollTo(0, 0)
  }, [policyType])

  const t = content[language][policyType]
  const commonT = content[language]

  return (
    <div className={`landing-page policy-page-wrapper ${isVisible ? 'visible' : ''}`}>
      <FloatingShape className="shape-1 opacity-reduced" delay={0} />
      <FloatingShape className="shape-2 opacity-reduced" delay={0.5} />
      <FloatingShape className="shape-3 opacity-reduced" delay={1} />
      
      <header className="landing-header">
        <div className="landing-container">
          <button className="brand nav-brand-btn" onClick={onBack}>
            <span className="brand-icon">e</span>
            <span className="brand-name">Elevana</span>
          </button>
          <nav className="landing-nav">
            <div className="language-switcher">
              <button
                className={language === 'en' ? 'active' : ''}
                onClick={() => onLanguageChange('en')}
              >
                EN
              </button>
              <button
                className={language === 'sw' ? 'active' : ''}
                onClick={() => onLanguageChange('sw')}
              >
                SW
              </button>
            </div>
            <button className="btn-secondary" onClick={onBack}>
               {commonT.back}
            </button>
          </nav>
        </div>
      </header>

      <main className="policy-main">
        <div className="landing-container">
          <div className="policy-content-card visual-card">
            <h1 className="policy-title hero-title">
              {t.title}
            </h1>
            <p className="policy-updated hero-eyebrow">{t.lastUpdated}</p>
            
            <div className="policy-body">
              {t.sections.map((section, idx) => (
                <section key={idx} className="policy-section">
                  <h2 className="policy-heading">{section.heading}</h2>
                  <p className="policy-paragraph">{section.body}</p>
                </section>
              ))}
            </div>
          </div>
        </div>
      </main>

      <footer className="landing-footer">
        <div className="landing-container">
          <p className="footer-tagline">Elevana — Mental health support, elevated.</p>
        </div>
      </footer>
    </div>
  )
}
