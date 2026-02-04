/**
 * TanStack Query hooks for API calls
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'

// Types
export interface ChatMessage {
  role: string
  content: string
  timestamp?: string
}

export interface ChatRequest {
  message: string
  conversation_id?: string
  history?: ChatMessage[]
}

export interface ChatResponse {
  response: string
  conversation_id: string
  timestamp: string
}

// Health check query
export const useHealthCheck = () => {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await apiClient.get('/health/')
      return response.data
    },
  })
}

// Chat mutation
export const useChatMutation = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: ChatRequest) => {
      const response = await apiClient.post<ChatResponse>('/chat/', data)
      return response.data
    },
    onSuccess: () => {
      // Invalidate chat history queries
      queryClient.invalidateQueries({ queryKey: ['chat', 'history'] })
    },
  })
}

// Chat history query
export const useChatHistory = (conversationId: string) => {
  return useQuery({
    queryKey: ['chat', 'history', conversationId],
    queryFn: async () => {
      const response = await apiClient.get(`/chat/history/${conversationId}`)
      return response.data
    },
    enabled: !!conversationId,
  })
}
