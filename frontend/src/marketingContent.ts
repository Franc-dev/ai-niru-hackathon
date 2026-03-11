import type { LanguageCode } from './api/queries'

export type PolicyType = 'privacy' | 'terms' | 'cookie'

type PolicySection = {
  heading: string
  body: string
}

type PolicyDocument = {
  title: string
  lastUpdated: string
  sections: PolicySection[]
}

export type MarketingLabels = {
  footerTagline: string
  privacy: string
  terms: string
  cookie: string
  login: string
  contact: string
  menu: string
  closeMenu: string
  legal: string
  home: string
  language: string
}

export const marketingLabels: Record<LanguageCode, MarketingLabels> = {
  en: {
    footerTagline: 'Elevana - Mental health support, elevated.',
    privacy: 'Privacy Policy',
    terms: 'Terms of Service',
    cookie: 'Cookie Policy',
    login: 'Login',
    contact: 'Contact',
    menu: 'Menu',
    closeMenu: 'Close menu',
    legal: 'Legal',
    home: 'Back to home',
    language: 'Language',
  },
  sw: {
    footerTagline: 'Elevana - Msaada wa afya ya akili, ulioboreshwa.',
    privacy: 'Sera ya Faragha',
    terms: 'Masharti ya Huduma',
    cookie: 'Sera ya Vidakuzi',
    login: 'Ingia',
    contact: 'Mawasiliano',
    menu: 'Menyu',
    closeMenu: 'Funga menyu',
    legal: 'Kisheria',
    home: 'Rudi nyumbani',
    language: 'Lugha',
  },
}

export const policyContent: Record<LanguageCode, Record<PolicyType, PolicyDocument>> = {
  en: {
    privacy: {
      title: 'Privacy Policy',
      lastUpdated: 'Last updated: March 11, 2026',
      sections: [
        {
          heading: '1. Information We Collect',
          body: 'We collect the information you choose to share with Elevana, including account details, preferences, and conversation history. We use this information to operate the service, personalize your experience, and support account security.',
        },
        {
          heading: '2. How We Use Your Information',
          body: 'We use personal information to provide mental wellness support, improve product performance, maintain service quality, and respond to support requests. We do not sell your personal data to third parties, and we limit internal access to people and systems that need it for these purposes.',
        },
        {
          heading: '3. Sensitive Health Information and HIPAA-Style Safeguards',
          body: 'When users share health-related or emotionally sensitive information, we handle it with administrative, technical, and physical safeguards designed to support confidentiality, integrity, and controlled access. References to HIPAA in this policy describe our privacy and security approach for sensitive information and do not, by themselves, constitute a claim of formal HIPAA certification or covered-entity status.',
        },
        {
          heading: '4. Kenya Data Protection Act (DPA) Considerations',
          body: 'For users in Kenya, we aim to handle personal data in a manner consistent with the Data Protection Act, 2019, including principles of lawful processing, purpose limitation, data minimization, security, and respect for user rights. Where required, we support requests relating to access, correction, deletion, and objections to processing through our support channels.',
        },
        {
          heading: '5. Retention, Security, and International Access',
          body: 'We retain information only for as long as reasonably necessary for service delivery, safety, legal obligations, and system integrity. We use encryption in transit and at rest where appropriate, monitor for unauthorized access, and review our security practices regularly as the platform evolves.',
        },
        {
          heading: '6. Your Rights and Contact',
          body: 'You may request access to, correction of, or deletion of your information, subject to applicable law and legitimate operational requirements. Questions about privacy, cookies, data handling, or compliance requests can be sent to hello@elevana.com.',
        },
      ],
    },
    terms: {
      title: 'Terms of Service',
      lastUpdated: 'Last updated: March 11, 2026',
      sections: [
        {
          heading: '1. Acceptance of Terms',
          body: 'By accessing or using Elevana, you agree to these Terms of Service and to applicable laws and regulations. If you do not agree, you should not use the service.',
        },
        {
          heading: '2. Not Medical Advice',
          body: 'Elevana is an AI companion for mental wellness support. It is not a substitute for professional medical advice, diagnosis, or treatment. If you are experiencing a crisis or emergency, contact local emergency services or a qualified clinician immediately.',
        },
        {
          heading: '3. Acceptable Use',
          body: 'You agree to use the service lawfully and responsibly. You must not use Elevana to transmit harmful, abusive, threatening, deceptive, or illegal material, or to interfere with the platform or other users.',
        },
        {
          heading: '4. Availability and Liability',
          body: 'We work to keep Elevana available and useful, but we do not guarantee uninterrupted service. To the extent permitted by law, Elevana is not liable for indirect, incidental, or consequential damages arising from use of or inability to use the platform.',
        },
      ],
    },
    cookie: {
      title: 'Cookie Policy',
      lastUpdated: 'Last updated: March 11, 2026',
      sections: [
        {
          heading: '1. What Cookies Are',
          body: 'Cookies are small text files stored on your device when you visit a website. They help the site remember useful information between sessions.',
        },
        {
          heading: '2. How We Use Cookies',
          body: 'We use essential cookies to support core functions such as login state, session continuity, and language preferences. These cookies are necessary for core product behavior.',
        },
        {
          heading: '3. Performance and Analytics',
          body: 'Where permitted, we may use performance-related technologies to understand how visitors use the site, measure reliability, and improve responsiveness and usability.',
        },
        {
          heading: '4. Managing Cookies',
          body: 'You can control or delete cookies through your browser settings. Disabling some cookies may reduce functionality, including saved preferences and session continuity.',
        },
      ],
    },
  },
  sw: {
    privacy: {
      title: 'Sera ya Faragha',
      lastUpdated: 'Ilisasishwa mwisho: Machi 11, 2026',
      sections: [
        {
          heading: '1. Taarifa Tunazokusanya',
          body: 'Tunakusanya taarifa unazoamua kushiriki na Elevana, ikiwemo maelezo ya akaunti, mapendeleo, na historia ya mazungumzo. Tunazitumia kuendesha huduma, kubinafsisha uzoefu wako, na kusaidia usalama wa akaunti.',
        },
        {
          heading: '2. Jinsi Tunavyotumia Taarifa Zako',
          body: 'Tunatumia taarifa binafsi kutoa msaada wa afya ya akili, kuboresha utendaji wa bidhaa, kudumisha ubora wa huduma, na kujibu maombi ya usaidizi. Hatuuzi data yako binafsi kwa wahusika wengine na tunapunguza ufikiaji wa ndani kwa watu na mifumo inayohitaji data hiyo pekee.',
        },
        {
          heading: '3. Taarifa Nyeti za Afya na Ulinzi wa Aina ya HIPAA',
          body: 'Watumiaji wanaposhiriki taarifa za kiafya au hisia nyeti, tunazitunza kwa hatua za kiutawala, kiufundi, na kimwili zinazolenga usiri, uadilifu, na ufikiaji uliodhibitiwa. Marejeo ya HIPAA katika sera hii yanaeleza mbinu yetu ya faragha na usalama kwa taarifa nyeti, na hayamaanishi moja kwa moja kuwa tuna uthibitisho rasmi wa HIPAA au hadhi ya covered entity.',
        },
        {
          heading: '4. Mambo ya Kuzingatia Chini ya Sheria ya Kenya ya Ulinzi wa Data',
          body: 'Kwa watumiaji walioko Kenya, tunalenga kushughulikia data binafsi kwa namna inayolingana na Data Protection Act, 2019, ikiwemo uchakataji wa kisheria, kikomo cha madhumuni, kupunguza data, usalama, na kuheshimu haki za mtumiaji. Pale inapohitajika, tunaunga mkono maombi ya ufikiaji, masahihisho, ufutaji, na pingamizi dhidi ya uchakataji kupitia njia zetu za usaidizi.',
        },
        {
          heading: '5. Uhifadhi, Usalama, na Ufikiaji wa Kimataifa',
          body: 'Tunatunza taarifa kwa muda unaohitajika kwa utoaji wa huduma, usalama, wajibu wa kisheria, na uadilifu wa mfumo. Tunatumia usimbaji fiche wakati wa usafirishaji na uhifadhi inapofaa, tunafuatilia ufikiaji usioidhinishwa, na tunapitia mbinu zetu za usalama mara kwa mara kadri jukwaa linavyokua.',
        },
        {
          heading: '6. Haki Zako na Mawasiliano',
          body: 'Unaweza kuomba ufikiaji, masahihisho, au ufutaji wa taarifa zako kulingana na sheria inayotumika na mahitaji halali ya uendeshaji. Maswali kuhusu faragha, vidakuzi, jinsi tunavyoshughulikia data, au maombi ya uzingatiaji yanaweza kutumwa kwa hello@elevana.com.',
        },
      ],
    },
    terms: {
      title: 'Masharti ya Huduma',
      lastUpdated: 'Ilisasishwa mwisho: Machi 11, 2026',
      sections: [
        {
          heading: '1. Kukubali Masharti',
          body: 'Kwa kufikia au kutumia Elevana, unakubali Masharti haya ya Huduma pamoja na sheria na kanuni zinazotumika. Ikiwa hukubaliani nayo, hupaswi kutumia huduma.',
        },
        {
          heading: '2. Sio Ushauri wa Kimatibabu',
          body: 'Elevana ni mshirika wa AI kwa msaada wa ustawi wa afya ya akili. Sio mbadala wa ushauri wa kitaalamu wa kimatibabu, utambuzi, au matibabu. Ikiwa uko kwenye dharura au hatari, wasiliana na huduma za dharura au mtaalamu wa afya mara moja.',
        },
        {
          heading: '3. Matumizi Yanayokubalika',
          body: 'Unakubali kutumia huduma kwa njia ya kisheria na yenye uwajibikaji. Huruhusiwi kutumia Elevana kusambaza taarifa hatari, za matusi, za vitisho, za udanganyifu, au zisizo halali, wala kuingilia jukwaa au watumiaji wengine.',
        },
        {
          heading: '4. Upatikanaji na Dhima',
          body: 'Tunafanya kazi kuhakikisha Elevana inapatikana na inasaidia, lakini hatuhakikishi huduma isiyokatika kila wakati. Kwa kiwango kinachoruhusiwa na sheria, Elevana haiwajibiki kwa hasara zisizo za moja kwa moja, za ziada, au za matokeo zinazotokana na matumizi au kutoweza kutumia jukwaa.',
        },
      ],
    },
    cookie: {
      title: 'Sera ya Vidakuzi',
      lastUpdated: 'Ilisasishwa mwisho: Machi 11, 2026',
      sections: [
        {
          heading: '1. Vidakuzi ni Nini',
          body: 'Vidakuzi ni faili ndogo za maandishi zinazohifadhiwa kwenye kifaa chako unapozuru tovuti. Husaidia tovuti kukumbuka taarifa muhimu kati ya vipindi vya matumizi.',
        },
        {
          heading: '2. Jinsi Tunavyotumia Vidakuzi',
          body: 'Tunatumia vidakuzi muhimu kusaidia kazi za msingi kama hali ya kuingia, mwendelezo wa kipindi, na mapendeleo ya lugha. Vidakuzi hivi ni muhimu kwa tabia kuu ya bidhaa.',
        },
        {
          heading: '3. Utendaji na Uchambuzi',
          body: 'Pale panaporuhusiwa, tunaweza kutumia teknolojia za utendaji kuelewa jinsi wageni wanavyotumia tovuti, kupima uthabiti, na kuboresha kasi ya majibu pamoja na urahisi wa matumizi.',
        },
        {
          heading: '4. Kusimamia Vidakuzi',
          body: 'Unaweza kudhibiti au kufuta vidakuzi kupitia mipangilio ya kivinjari chako. Kuzima baadhi ya vidakuzi kunaweza kupunguza utendaji, ikiwemo mapendeleo yaliyohifadhiwa na mwendelezo wa kipindi.',
        },
      ],
    },
  },
}
