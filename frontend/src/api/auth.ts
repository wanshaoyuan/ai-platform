import http from './http'

export interface LoginResult {
  access_token: string
  token_type: string
  user: {
    id: number
    username: string
    email: string | null
    role: string
    is_active: boolean
    created_at: string
  }
}

export const authApi = {
  login(username: string, password: string) {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return http.post<LoginResult>('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  me() {
    return http.get('/auth/me')
  },
  changePassword(oldPassword: string, newPassword: string) {
    return http.post('/auth/change-password', null, {
      params: { old_password: oldPassword, new_password: newPassword },
    })
  },
}
