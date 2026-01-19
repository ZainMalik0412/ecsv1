import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

// Auth
export const login = async (username: string, password: string) => {
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)
  const response = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return response.data
}

export const getMe = async () => {
  const response = await api.get('/auth/me')
  return response.data
}

// Dashboard
export const getDashboardStats = async () => {
  const response = await api.get('/dashboard/stats')
  return response.data
}

// Users
export const getUsers = async (role?: string) => {
  const params = role ? { role } : {}
  const response = await api.get('/users', { params })
  return response.data
}

export const createUser = async (data: {
  username: string
  password: string
  full_name: string
  email?: string
  role: string
}) => {
  const response = await api.post('/users', data)
  return response.data
}

export const updateUser = async (id: number, data: Partial<{
  full_name: string
  email: string
  password: string
  is_active: boolean
}>) => {
  const response = await api.patch(`/users/${id}`, data)
  return response.data
}

export const deleteUser = async (id: number) => {
  await api.delete(`/users/${id}`)
}

// Modules
export const getModules = async () => {
  const response = await api.get('/modules')
  return response.data
}

export const getModule = async (id: number) => {
  const response = await api.get(`/modules/${id}`)
  return response.data
}

export const createModule = async (data: {
  code: string
  name: string
  description?: string
  lecturer_id?: number
}) => {
  const response = await api.post('/modules', data)
  return response.data
}

export const updateModule = async (id: number, data: Partial<{
  code: string
  name: string
  description: string
  lecturer_id: number
}>) => {
  const response = await api.patch(`/modules/${id}`, data)
  return response.data
}

export const deleteModule = async (id: number) => {
  await api.delete(`/modules/${id}`)
}

export const getModuleStudents = async (moduleId: number) => {
  const response = await api.get(`/modules/${moduleId}/students`)
  return response.data
}

// Enrolments
export const enrolStudent = async (studentId: number, moduleId: number) => {
  const response = await api.post('/enrolments', { student_id: studentId, module_id: moduleId })
  return response.data
}

export const enrolStudentsBulk = async (studentIds: number[], moduleId: number) => {
  const response = await api.post('/enrolments/bulk', { student_ids: studentIds, module_id: moduleId })
  return response.data
}

export const unenrolStudent = async (studentId: number, moduleId: number) => {
  await api.delete('/enrolments', { params: { student_id: studentId, module_id: moduleId } })
}

// Sessions
export const getSessions = async (params?: { module_id?: number; status?: string }) => {
  const response = await api.get('/sessions', { params })
  return response.data
}

export const getSession = async (id: number) => {
  const response = await api.get(`/sessions/${id}`)
  return response.data
}

export const createSession = async (data: {
  module_id: number
  title: string
  scheduled_start: string
  scheduled_end: string
  late_threshold_minutes?: number
}) => {
  const response = await api.post('/sessions', data)
  return response.data
}

export const updateSession = async (id: number, data: Partial<{
  title: string
  scheduled_start: string
  scheduled_end: string
  late_threshold_minutes: number
}>) => {
  const response = await api.patch(`/sessions/${id}`, data)
  return response.data
}

export const deleteSession = async (id: number) => {
  await api.delete(`/sessions/${id}`)
}

export const startSession = async (id: number) => {
  const response = await api.post(`/sessions/${id}/start`)
  return response.data
}

export const pauseSession = async (id: number) => {
  const response = await api.post(`/sessions/${id}/pause`)
  return response.data
}

export const resumeSession = async (id: number) => {
  const response = await api.post(`/sessions/${id}/resume`)
  return response.data
}

export const endSession = async (id: number) => {
  const response = await api.post(`/sessions/${id}/end`)
  return response.data
}

// Attendance
export const getSessionAttendance = async (sessionId: number) => {
  const response = await api.get(`/attendance/session/${sessionId}`)
  return response.data
}

export const getMyAttendance = async () => {
  const response = await api.get('/attendance/my')
  return response.data
}

export const updateAttendance = async (id: number, data: { status?: string; notes?: string }) => {
  const response = await api.patch(`/attendance/${id}`, data)
  return response.data
}

export const markAttendanceManual = async (sessionId: number, studentId: number, status: string) => {
  const response = await api.post('/attendance/mark-manual', null, {
    params: { session_id: sessionId, student_id: studentId, status },
  })
  return response.data
}

// Face Recognition
export const registerFace = async (imageBase64: string) => {
  const response = await api.post('/face/register', { image_base64: imageBase64 })
  return response.data
}

export const clearFaceRegistrations = async () => {
  const response = await api.delete('/face/register')
  return response.data
}

export const verifyFaceAndMarkAttendance = async (sessionId: number, imageBase64: string) => {
  const response = await api.post('/face/verify', { session_id: sessionId, image_base64: imageBase64 })
  return response.data
}

// Reports
export const getAttendanceReport = async (params?: {
  module_id?: number
  session_id?: number
  student_id?: number
  status?: string
  date_from?: string
  date_to?: string
}) => {
  const response = await api.get('/dashboard/reports/attendance', { params })
  return response.data
}

export const exportAttendanceCsv = async (params?: {
  module_id?: number
  session_id?: number
  date_from?: string
  date_to?: string
}) => {
  const response = await api.get('/dashboard/reports/attendance/csv', {
    params,
    responseType: 'blob',
  })
  return response.data
}

// Student Statistics (FR11)
export const getStudentStats = async () => {
  const response = await api.get('/dashboard/student-stats')
  return response.data
}

// Live Session (FR6-FR8)
export const getLiveSessionState = async (sessionId: number) => {
  const response = await api.get(`/sessions/${sessionId}/live-state`)
  return response.data
}

export const getLiveAttendance = async (sessionId: number) => {
  const response = await api.get(`/sessions/${sessionId}/live-attendance`)
  return response.data
}

export const recognizeFrame = async (sessionId: number, imageBase64: string) => {
  const response = await api.post(`/sessions/${sessionId}/recognize-frame`, {
    image_base64: imageBase64,
  })
  return response.data
}
