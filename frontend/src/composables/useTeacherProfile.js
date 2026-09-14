import { useAuthStore } from '../stores/auth'

function isAccountPlaceholder(user, name) {
  const value = String(name || '').trim()
  if (!value) return true
  if (user?.username && value === user.username) return true
  if (/^1\d{10}$/.test(value)) return true
  return false
}

export function teacherProfileFields(user) {
  const profile = user?.profile || {}
  const name = String(user?.first_name || '').trim()
    || (isAccountPlaceholder(user, user?.display_name) ? '' : String(user?.display_name || '').trim())
  return {
    display_name: name,
    teacher_name: name,
    school_name: profile.school_name || '',
    department: profile.department || '',
    subject: profile.subject || '',
    grade: profile.grade || '',
  }
}

export async function loadTeacherProfile() {
  const auth = useAuthStore()
  await auth.fetchMe()
  return teacherProfileFields(auth.user)
}
