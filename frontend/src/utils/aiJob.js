const KEY = 'tc_ai_job'

export function saveAiJob(job) {
  sessionStorage.setItem(KEY, JSON.stringify(job))
}

export function takeAiJob() {
  try {
    const raw = sessionStorage.getItem(KEY)
    sessionStorage.removeItem(KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}
