import { create } from 'zustand'
import { getMe, login as apiLogin } from '@/lib/api'

export type Role = 'student' | 'lecturer' | 'admin'

export interface User {
  id: number
  username: string
  email: string | null
  full_name: string
  role: Role
  is_active: boolean
  has_face_registered: boolean
  enrolled_module_ids: number[]
  taught_module_ids: number[]
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
  initialize: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('token'),
  user: null,
  isAuthenticated: !!localStorage.getItem('token'),
  isLoading: true,

  login: async (username: string, password: string) => {
    const data = await apiLogin(username, password)
    localStorage.setItem('token', data.access_token)
    set({ token: data.access_token, isAuthenticated: true })
    await get().fetchUser()
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ token: null, user: null, isAuthenticated: false })
  },

  fetchUser: async () => {
    try {
      const user = await getMe()
      set({ user, isAuthenticated: true })
    } catch {
      get().logout()
    }
  },

  initialize: async () => {
    const token = localStorage.getItem('token')
    if (token) {
      try {
        await get().fetchUser()
      } catch {
        get().logout()
      }
    }
    set({ isLoading: false })
  },
}))

// Initialize on load
useAuthStore.getState().initialize()
