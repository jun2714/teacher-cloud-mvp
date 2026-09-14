import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../components/AppShell.vue'
import HomeView from '../views/HomeView.vue'
import NotesView from '../views/NotesView.vue'
import CommunityView from '../views/CommunityView.vue'
import MineView from '../views/MineView.vue'
import LoginView from '../views/LoginView.vue'
import NoteEditorView from '../views/NoteEditorView.vue'
import ReportView from '../views/ReportView.vue'
import GenerateOutputView from '../views/GenerateOutputView.vue'
import DocumentDetailView from '../views/DocumentDetailView.vue'
import HistoryListView from '../views/HistoryListView.vue'
import QuestionCreateView from '../views/QuestionCreateView.vue'
import QuestionDetailView from '../views/QuestionDetailView.vue'
import LessonDesignView from '../views/LessonDesignView.vue'
import LessonReviewView from '../views/LessonReviewView.vue'
import AssistantView from '../views/AssistantView.vue'
import ProfileView from '../views/ProfileView.vue'
import SettingsView from '../views/SettingsView.vue'
import NoticesView from '../views/NoticesView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/register', redirect: '/login?mode=sms' },
    {
      path: '/', component: AppShell, children: [
        { path: '', name: 'home', component: HomeView },
        { path: 'notes', name: 'notes', component: NotesView },
        { path: 'community', name: 'community', component: CommunityView },
        { path: 'mine', name: 'mine', component: MineView },
        { path: 'profile', name: 'profile', component: ProfileView, meta: { hideNav: true } },
        { path: 'settings', name: 'settings', component: SettingsView, meta: { hideNav: true } },
        { path: 'notices', name: 'notices', component: NoticesView, meta: { hideNav: true } },
        { path: 'notes/new', name: 'note-new', component: NoteEditorView, meta: { hideNav: true } },
        { path: 'notes/:id', name: 'note-edit', component: NoteEditorView, meta: { hideNav: true } },
        { path: 'reports/generate', name: 'report-generate', component: ReportView, meta: { hideNav: true } },
        { path: 'reports/output', name: 'report-output', component: GenerateOutputView, meta: { hideNav: true, kind: 'report' } },
        { path: 'reports', name: 'report-history', component: HistoryListView, meta: { hideNav: true, kind: 'report' } },
        { path: 'reports/:id', name: 'report-detail', component: DocumentDetailView, meta: { hideNav: true, kind: 'report' } },
        { path: 'questions/new', name: 'question-new', component: QuestionCreateView, meta: { hideNav: true } },
        { path: 'questions/:id', name: 'question-detail', component: QuestionDetailView, meta: { hideNav: true } },
        { path: 'lesson-design', name: 'lesson-design', component: LessonDesignView, meta: { hideNav: true } },
        { path: 'lesson-plans/output', name: 'lesson-output', component: GenerateOutputView, meta: { hideNav: true, kind: 'lesson' } },
        { path: 'lesson-plans', name: 'lesson-history', component: HistoryListView, meta: { hideNav: true, kind: 'lesson' } },
        { path: 'lesson-plans/:id', name: 'lesson-detail', component: DocumentDetailView, meta: { hideNav: true, kind: 'lesson' } },
        { path: 'assistant', name: 'assistant', component: AssistantView, meta: { hideNav: true } },
        { path: 'lesson-review', name: 'lesson-review', component: LessonReviewView, meta: { hideNav: true } },
        { path: 'lesson-reviews', name: 'review-history', component: HistoryListView, meta: { hideNav: true, kind: 'review' } },
        { path: 'lesson-reviews/:id', name: 'review-detail', component: DocumentDetailView, meta: { hideNav: true, kind: 'review' } },
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
