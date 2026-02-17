/**
 * TanStack Query hooks for API calls
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'

export type LanguageCode = 'en' | 'sw'

export interface ChatMessage {
  role: string
  content: string
  timestamp?: string
}

export interface ChatRequest {
  message: string
  conversation_id?: string
  history?: ChatMessage[]
  language?: LanguageCode
}

export interface ChatResponse {
  response: string
  conversation_id: string
  conversation_title?: string | null
  language?: LanguageCode
  timestamp: string
}

export interface ConversationHistory {
  conversation_id: string
  title?: string | null
  language?: LanguageCode
  messages: ChatMessage[]
}

export interface ConversationListItem {
  conversation_id: string
  title?: string | null
  language?: LanguageCode
  created_at?: string
  updated_at?: string
  preview: string
}

export interface AuthUser {
  id: string
  email: string
  display_name?: string | null
  preferred_language: LanguageCode
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export interface SignupRequest {
  email: string
  password: string
  display_name?: string
}

export interface LoginRequest {
  email: string
  password: string
}

export const useSignupMutation = () => {
  return useMutation({
    mutationFn: async (data: SignupRequest) => {
      const response = await apiClient.post<AuthResponse>('/auth/signup', data)
      return response.data
    },
  })
}

export const useLoginMutation = () => {
  return useMutation({
    mutationFn: async (data: LoginRequest) => {
      const response = await apiClient.post<AuthResponse>('/auth/login', data)
      return response.data
    },
  })
}

export const useMeQuery = (enabled: boolean) => {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const response = await apiClient.get<AuthUser>('/auth/me')
      return response.data
    },
    enabled,
    retry: false,
  })
}

export const useUpdateLanguageMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (language: LanguageCode) => {
      const response = await apiClient.patch<AuthUser>('/auth/me/language', {
        preferred_language: language,
      })
      return response.data
    },
    onSuccess: (user) => {
      queryClient.setQueryData(['auth', 'me'], user)
    },
  })
}

export const useChatMutation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: ChatRequest) => {
      const response = await apiClient.post<ChatResponse>('/chat/', data)
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['chat', 'history', data.conversation_id] })
      queryClient.invalidateQueries({ queryKey: ['chat', 'conversations'] })
    },
  })
}

export const useConversationListQuery = (enabled: boolean) => {
  return useQuery({
    queryKey: ['chat', 'conversations'],
    queryFn: async () => {
      const response = await apiClient.get<ConversationListItem[]>('/chat/conversations')
      return response.data
    },
    enabled,
  })
}

export const useChatHistory = (conversationId: string, enabled: boolean) => {
  return useQuery({
    queryKey: ['chat', 'history', conversationId],
    queryFn: async () => {
      const response = await apiClient.get<ConversationHistory>(`/chat/history/${conversationId}`)
      return response.data
    },
    enabled: enabled && !!conversationId,
  })
}
