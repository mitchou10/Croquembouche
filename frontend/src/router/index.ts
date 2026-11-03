import { createRouter, createWebHistory, type RouteLocationNormalized, type RouteLocationRaw } from 'vue-router'
import { useSession } from '../composables/useSession'

export function requireAuth(to: RouteLocationNormalized): true | RouteLocationRaw {
  const { isAuthenticated, isAdmin } = useSession()
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && isAuthenticated.value) return { name: 'catalogue' }
  // The administrator's pages: anyone else is sent to the analyses.
  if (to.meta.requiresAdmin && !isAdmin.value) return { name: 'analyses' }
  return true
}

export const routes = [
  { path: '/', name: 'landing', component: () => import('../views/LandingView.vue') },
  { path: '/connexion', name: 'login', component: () => import('../views/LoginView.vue') },
  {
    path: '/',
    component: () => import('../components/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: 'catalogue', name: 'catalogue', component: () => import('../views/CatalogueView.vue') },
      { path: 'catalogue/nouveau', name: 'catalogue-new', component: () => import('../views/TemplateFormView.vue') },
      { path: 'catalogue/:id', name: 'catalogue-detail', component: () => import('../views/TemplateDetailView.vue') },
      { path: 'catalogue/:id/modifier', name: 'catalogue-edit', component: () => import('../views/TemplateFormView.vue') },
      { path: 'analyses', name: 'analyses', component: () => import('../views/AnalysesView.vue') },
      { path: 'analyses/nouvelle', name: 'analysis-new', component: () => import('../views/NewAnalysisView.vue') },
      { path: 'analyses/:id', name: 'analysis-detail', component: () => import('../views/AnalysisDashboardView.vue') },
      { path: 'vue-d-ensemble', name: 'overview', meta: { requiresAdmin: true }, component: () => import('../views/OverviewView.vue') },
      { path: 'parametres', name: 'settings', component: () => import('../views/SettingsView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: { name: 'landing' } },
]

export const router = createRouter({ history: createWebHistory(), routes })
router.beforeEach(requireAuth)
