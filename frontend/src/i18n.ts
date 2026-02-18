import type { LanguageCode } from './api/queries'

type TranslationMap = Record<string, string>

const translations: Record<LanguageCode, TranslationMap> = {
  en: {
    appName: 'AI Niru',
    subtitle: 'Conversational research assistant',
    login: 'Sign in',
    signup: 'Create account',
    logout: 'Log out',
    email: 'Email',
    password: 'Password',
    displayName: 'Display name',
    authHint: 'Secure access with your email and token-based session.',
    newConversation: 'New conversation',
    conversations: 'Conversations',
    noConversations: 'No conversations yet',
    placeholder: 'Type a message...',
    startPrompt: 'Ask anything to begin a new thread.',
    send: 'Send',
    thinking: 'Thinking...',
    welcome: 'How can I help today?',
    language: 'Language',
    sw: 'Swahili',
    en: 'English',
    requiredFields: 'Email and password are required.',
  },
  sw: {
    appName: 'AI Niru',
    subtitle: 'Msaidizi wa mazungumzo na utafiti',
    login: 'Ingia',
    signup: 'Fungua akaunti',
    logout: 'Toka',
    email: 'Barua pepe',
    password: 'Nenosiri',
    displayName: 'Jina la kuonyesha',
    authHint: 'Ufikiaji salama kwa barua pepe na tokeni ya kikao.',
    newConversation: 'Mazungumzo mapya',
    conversations: 'Mazungumzo',
    noConversations: 'Bado hakuna mazungumzo',
    placeholder: 'Andika ujumbe...',
    startPrompt: 'Uliza chochote kuanza mazungumzo mapya.',
    send: 'Tuma',
    thinking: 'Ninafikiria...',
    welcome: 'Ninawezaje kusaidia leo?',
    language: 'Lugha',
    sw: 'Kiswahili',
    en: 'Kiingereza',
    requiredFields: 'Barua pepe na nenosiri vinahitajika.',
  },
}

export const getLanguageLabel = (language: LanguageCode) => translations[language][language]

export const t = (language: LanguageCode, key: string): string =>
  translations[language][key] ?? translations.en[key] ?? key
