/**
 * API Service - Handles all HTTP requests including Guest Mode
 */

const API_BASE = '/api'

class ApiService {
  constructor() {
    this.token = localStorage.getItem('token')
  }

  setToken(token) {
    this.token = token
    if (token) {
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('token')
    }
  }

  getToken() {
    return this.token || localStorage.getItem('token')
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    }

    if (this.getToken()) {
      headers['Authorization'] = `Bearer ${this.getToken()}`
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Request failed')
      }

      return data
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error)
      throw error
    }
  }

  // Auth endpoints
  async signup(username, email, password) {
    const data = await this.request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ username, email, password })
    })
    this.setToken(data.access_token)
    return data
  }

  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    })
    this.setToken(data.access_token)
    return data
  }

  async guestLogin() {
    const data = await this.request('/auth/guest', {
      method: 'POST',
      body: JSON.stringify({})
    })
    this.setToken(data.access_token)
    return data
  }

  async getMe() {
    return this.request('/auth/me')
  }

  logout() {
    this.setToken(null)
    localStorage.removeItem('isGuest')
  }

  // Profile endpoints
  async updateProfile(data) {
    return this.request('/profile/update', {
      method: 'PUT',
      body: JSON.stringify(data)
    })
  }

  async changePassword(currentPassword, newPassword) {
    return this.request('/profile/change-password', {
      method: 'PUT',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword
      })
    })
  }

  async changeEmail(newEmail, password) {
    return this.request('/profile/change-email', {
      method: 'PUT',
      body: JSON.stringify({
        new_email: newEmail,
        password
      })
    })
  }

  async getGameHistory() {
    return this.request('/profile/history')
  }

  // Game endpoints
  async checkRoomExists(roomCode) {
    return this.request(`/rooms/${roomCode}/exists`)
  }

  async getQuestionCount() {
    return this.request('/questions/count')
  }

  // Competition endpoints
  async createCompetitionRoom(sessionId, timePerQuestion = 20, teacherQuestionCount = 0, studentQuestionIds = []) {
    return this.request('/competition/rooms', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        time_per_question: timePerQuestion,
        teacher_question_count: teacherQuestionCount,
        student_question_ids: studentQuestionIds
      })
    })
  }

  async getActiveCompetitionRooms() {
    return this.request('/competition/rooms/active')
  }

  async getCompetitionRoom(roomCode) {
    return this.request(`/competition/rooms/${roomCode}`)
  }

  async joinCompetitionRoom(roomCode, role = 'player') {
    return this.request(`/competition/rooms/${roomCode}/join`, {
      method: 'POST',
      body: JSON.stringify({ role })
    })
  }

  async getCompetitionLeaderboard(roomCode) {
    return this.request(`/competition/rooms/${roomCode}/leaderboard`)
  }

  async generateCompetitionQuestions(sessionId, count = 5, fileIds = []) {
    return this.request(`/competition/sessions/${sessionId}/generate-questions`, {
      method: 'POST',
      body: JSON.stringify({
        count,
        file_ids: fileIds
      })
    })
  }

  async getSessionQuestions(sessionId) {
    return this.request(`/competition/sessions/${sessionId}/questions`)
  }
}

export const api = new ApiService()
export default api
