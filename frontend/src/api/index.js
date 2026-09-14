import http from './http'

const unwrap = (response) => response.data.results ?? response.data

export const authApi = {
  login: (payload) => http.post('/auth/token/', payload),
  captcha: () => http.get('/auth/captcha/'),
  sendSmsCode: (payload) => http.post('/auth/sms-code/', payload),
  smsLogin: (payload) => http.post('/auth/sms-login/', payload),
  register: (payload) => http.post('/auth/register/', payload),
  me: () => http.get('/me/'),
  updateMe: (payload) => {
    if (payload instanceof FormData) {
      return http.patch('/me/', payload)
    }
    return http.patch('/me/', payload)
  },
  stats: () => http.get('/me/stats/'),
  changePassword: (payload) => http.post('/me/change-password/', payload),
  logout: (refresh) => http.post('/auth/logout/', { refresh }),
}

export const notesApi = {
  list: () => http.get('/notes/').then(unwrap),
  detail: (id) => http.get(`/notes/${id}/`).then((res) => res.data),
  create: (payload) => http.post('/notes/', payload, { headers: payload instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : {} }),
  update: (id, payload) => http.patch(`/notes/${id}/`, payload, { headers: payload instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : {} }),
  extract: (payload) => http.post('/notes/extract/', payload, { headers: { 'Content-Type': 'multipart/form-data' } }),
  remove: (id) => http.delete(`/notes/${id}/`),
}

export const reportsApi = {
  list: () => http.get('/reports/').then(unwrap),
  detail: (id) => http.get(`/reports/${id}/`).then((res) => res.data),
  generate: (payload) => http.post('/reports/generate/', payload),
  exportDocx: (id) => http.get(`/reports/${id}/export/`, { responseType: 'blob' }),
  save: (id, payload) => http.patch(`/reports/${id}/save/`, payload).then((res) => res.data),
  remove: (id) => http.delete(`/reports/${id}/`),
}

export const lessonApi = {
  list: () => http.get('/lesson-plans/').then(unwrap),
  detail: (id) => http.get(`/lesson-plans/${id}/`).then((res) => res.data),
  generatePlan: (payload) => http.post('/lesson-plans/generate/', payload),
  generateReview: (payload) => http.post('/lesson-reviews/generate/', payload, {
    headers: payload instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : {},
    timeout: 180000,
  }),
  listReviews: () => http.get('/lesson-reviews/').then(unwrap),
  detailReview: (id) => http.get(`/lesson-reviews/${id}/`).then((res) => res.data),
  exportPlan: (id) => http.get(`/lesson-plans/${id}/export/`, { responseType: 'blob' }),
  exportReview: (id) => http.get(`/lesson-reviews/${id}/export/`, { responseType: 'blob' }),
  savePlan: (id, payload) => http.patch(`/lesson-plans/${id}/save/`, payload).then((res) => res.data),
  saveReview: (id, payload) => http.patch(`/lesson-reviews/${id}/save/`, payload).then((res) => res.data),
  remove: (id) => http.delete(`/lesson-plans/${id}/`),
  removeReview: (id) => http.delete(`/lesson-reviews/${id}/`),
}

export const assistantApi = {
  list: () => http.get('/assistant-chats/').then(unwrap),
  detail: (id) => http.get(`/assistant-chats/${id}/`).then((res) => res.data),
  remove: (id) => http.delete(`/assistant-chats/${id}/`),
}

export const communityApi = {
  list: (params) => http.get('/questions/', { params }).then(unwrap),
  detail: (id) => http.get(`/questions/${id}/`),
  create: (payload) => http.post('/questions/', payload),
  answer: (id, content) => http.post(`/questions/${id}/answer/`, { content }),
  toggleQuestionLike: (id) => http.post(`/questions/${id}/toggle-like/`),
  toggleAnswerLike: (id) => http.post(`/answers/${id}/toggle-like/`),
  markSolved: (id, answerId) => http.post(`/questions/${id}/mark-solved/`, { answer_id: answerId }),
}

export const noticeApi = {
  list: () => http.get('/notices/').then((res) => res.data),
  unread: () => http.get('/notices/unread/').then((res) => res.data),
  markRead: (ids) => http.post('/notices/mark-read/', ids ? { ids } : {}),
}

export const asrApi = {
  transcribe: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/asr/transcribe/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000,
    }).then((res) => res.data)
  },
}
