import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../components/AppShell.vue'
import LoginView from '../views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/register', redirect: '/login?mode=sms' },
    {
      path: '/', component: AppShell, children: [
        { path: '', name: 'home', component: () => import('../views/HomeView.vue') },
        { path: 'notes', name: 'notes', component: () => import('../views/NotesView.vue') },
        { path: 'community', name: 'community', component: () => import('../views/CommunityView.vue') },
        { path: 'mine', name: 'mine', component: () => import('../views/MineView.vue') },
        { path: 'profile', name: 'profile', component: () => import('../views/ProfileView.vue'), meta: { hideNav: true } },
        { path: 'settings', name: 'settings', component: () => import('../views/SettingsView.vue'), meta: { hideNav: true } },
        { path: 'notices', name: 'notices', component: () => import('../views/NoticesView.vue'), meta: { hideNav: true } },
        { path: 'notes/new', name: 'note-new', component: () => import('../views/NoteEditorView.vue'), meta: { hideNav: true } },
        { path: 'notes/:id', name: 'note-edit', component: () => import('../views/NoteEditorView.vue'), meta: { hideNav: true } },
        { path: 'reports/generate', name: 'report-generate', component: () => import('../views/ReportView.vue'), meta: { hideNav: true } },
        { path: 'reports/output', name: 'report-output', component: () => import('../views/GenerateOutputView.vue'), meta: { hideNav: true, kind: 'report' } },
        { path: 'reports', name: 'report-history', component: () => import('../views/HistoryListView.vue'), meta: { hideNav: true, kind: 'report' } },
        { path: 'reports/:id', name: 'report-detail', component: () => import('../views/DocumentDetailView.vue'), meta: { hideNav: true, kind: 'report' } },
        { path: 'questions/new', name: 'question-new', component: () => import('../views/QuestionCreateView.vue'), meta: { hideNav: true } },
        { path: 'questions/:id', name: 'question-detail', component: () => import('../views/QuestionDetailView.vue'), meta: { hideNav: true } },
        { path: 'lesson-design', name: 'lesson-design', component: () => import('../views/LessonDesignView.vue'), meta: { hideNav: true } },
        { path: 'lesson-plans/output', name: 'lesson-output', component: () => import('../views/GenerateOutputView.vue'), meta: { hideNav: true, kind: 'lesson' } },
        { path: 'lesson-plans', name: 'lesson-history', component: () => import('../views/HistoryListView.vue'), meta: { hideNav: true, kind: 'lesson' } },
        { path: 'lesson-plans/:id', name: 'lesson-detail', component: () => import('../views/DocumentDetailView.vue'), meta: { hideNav: true, kind: 'lesson' } },
        { path: 'assistant', name: 'assistant', component: () => import('../views/AssistantView.vue'), meta: { hideNav: true } },
        { path: 'lesson-review', name: 'lesson-review', component: () => import('../views/LessonReviewView.vue'), meta: { hideNav: true } },
        { path: 'lesson-reviews', name: 'review-history', component: () => import('../views/HistoryListView.vue'), meta: { hideNav: true, kind: 'review' } },
        { path: 'lesson-reviews/:id', name: 'review-detail', component: () => import('../views/DocumentDetailView.vue'), meta: { hideNav: true, kind: 'review' } },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  if (!to.meta.public && !token) return '/login'
  if ((to.path === '/login' || to.path === '/register') && token) return '/'
})

export default router
