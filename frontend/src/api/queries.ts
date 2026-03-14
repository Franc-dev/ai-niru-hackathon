/**
 * TanStack Query hooks for API calls
 */
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { apiClient } from './client'

export type LanguageCode = 'en' | 'sw'

export interface RecommendationCard {
  id: string
  kind: 'resource' | 'counselor' | 'crisis'
  title: string
  subtitle?: string
  description?: string
  badges?: string[]
  cta_label?: string
  cta_href?: string
  cta_kind?: 'external' | 'phone' | 'email' | string
  secondary_cta_label?: string
  secondary_cta_href?: string
  secondary_cta_kind?: 'external' | 'phone' | 'email' | string
  media_image?: string
}

export interface MessageMetadata {
  language?: LanguageCode
  safety_refusal?: boolean
  ui_type?: 'recommendations' | string
  recommendation_kind?: 'resources' | 'counselors' | 'crisis' | string
  recommendation_topic?: string
  recommendation_reason?: 'current_message' | 'history' | string
  cards?: RecommendationCard[]
}

export interface ChatMessage {
  role: string
  content: string
  timestamp?: string
  message_id?: string
  metadata?: MessageMetadata
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
  message_metadata?: MessageMetadata
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
  pinned?: boolean
  archived?: boolean
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
    placeholderData: keepPreviousData,
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
    placeholderData: keepPreviousData,
  })
}

export const useDeleteConversationMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (conversationId: string) => {
      const response = await apiClient.delete(`/chat/conversations/${conversationId}`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', 'conversations'] })
    },
  })
}

export const useEditConversationTitleMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ conversationId, title }: { conversationId: string; title: string }) => {
      const response = await apiClient.patch(`/chat/conversations/${conversationId}`, { title })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', 'conversations'] })
    },
  })
}

export const usePinConversationMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ conversationId, pinned }: { conversationId: string; pinned: boolean }) => {
      const response = await apiClient.patch(`/chat/conversations/${conversationId}/pin`, { pinned })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', 'conversations'] })
    },
  })
}

export const useArchiveConversationMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ conversationId, archived }: { conversationId: string; archived: boolean }) => {
      const response = await apiClient.patch(`/chat/conversations/${conversationId}/archive`, { archived })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', 'conversations'] })
    },
  })
}

export const useDeleteMessageMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ conversationId, messageId }: { conversationId: string; messageId: string }) => {
      const response = await apiClient.delete(`/chat/conversations/${conversationId}/messages/${messageId}`)
      return response.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['chat', 'history', variables.conversationId] })
    },
  })
}

export const useEditMessageMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ conversationId, messageId, content }: { conversationId: string; messageId: string; content: string }) => {
      const response = await apiClient.patch(`/chat/conversations/${conversationId}/messages/${messageId}`, { content })
      return response.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['chat', 'history', variables.conversationId] })
    },
  })
}

export interface STTResponse {
  transcript: string
  language: string
}

export const useSTTMutation = () => {
  return useMutation({
    mutationFn: async ({ audioBlob, language }: { audioBlob: Blob; language: LanguageCode }) => {
      const formData = new FormData()
      formData.append('file', audioBlob, 'audio.webm')
      formData.append('language', language)
      const response = await apiClient.post<STTResponse>('/voice/stt', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
  })
}

export const useTTSMutation = () => {
  return useMutation({
    mutationFn: async ({ text, language }: { text: string; language: LanguageCode }) => {
      const response = await apiClient.post<Blob>('/voice/tts', { text, language }, { responseType: 'blob' })
      return response.data
    },
  })
}
