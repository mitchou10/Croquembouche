<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSession } from '../composables/useSession'
import { useVersions } from '../composables/useVersions'

const route = useRoute()
const { displayName, isAdmin } = useSession()
const { frontend, backend, differ } = useVersions()

const everyone = [
  { name: 'catalogue', path: '/catalogue', label: 'Catalogue', icon: 'fr-icon-folder-2-line' },
  { name: 'analyses', path: '/analyses', label: 'Analyses', icon: 'fr-icon-search-line' },
  { name: 'evaluation', path: '/evaluation', label: 'Évaluation', icon: 'fr-icon-checkbox-circle-line' },
]
// What only the administrator has.
const administrator = [{ name: 'overview', path: '/vue-d-ensemble', label: 'Vue d’ensemble', icon: 'fr-icon-line-chart-line' }]
const items = computed(() => (isAdmin.value ? [...everyone, ...administrator] : everyone))
</script>

<template>
  <aside class="app-sidebar">
    <RouterLink class="app-sidebar__brand" :to="{ name: 'landing' }">
      <p class="fr-logo">République<br />Française</p>
      <span class="app-sidebar__title">Croquembouche</span>
    </RouterLink>

    <nav class="app-sidebar__nav" aria-label="Navigation principale">
      <ul class="app-sidebar__list">
        <li v-for="item in items" :key="item.name">
          <RouterLink
            class="app-sidebar__link"
            :class="[item.icon, { 'is-active': route.path.startsWith(item.path) }]"
            :aria-current="route.path.startsWith(item.path) ? 'page' : undefined"
            :to="{ name: item.name }"
          >
            {{ item.label }}
          </RouterLink>
        </li>
      </ul>
    </nav>

    <RouterLink
      class="app-sidebar__user fr-btn fr-btn--tertiary-no-outline fr-icon-account-circle-line fr-btn--icon-left"
      :to="{ name: 'settings' }"
      title="Ouvrir les paramètres"
    >
      <span class="app-sidebar__user-id">{{ displayName }}</span>
      <DsfrBadge v-if="isAdmin" label="Admin" type="info" small data-testid="admin-badge" class="app-sidebar__role" />
    </RouterLink>

    <p
      class="app-sidebar__version fr-text--xs fr-mb-0"
      :class="{ 'app-sidebar__version--differ': differ }"
      :title="differ ? 'Le frontend et le backend ne sont pas de la même version.' : 'Les versions de l’application.'"
      data-testid="app-versions"
    >
      Front <span data-testid="app-version-frontend">v{{ frontend }}</span> · API <span data-testid="app-version-backend">{{ backend === '…' || backend === 'indisponible' ? backend : `v${backend}` }}</span>
    </p>
  </aside>
</template>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  width: 16rem;
  flex-shrink: 0;
  padding: 1rem;
  border-right: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
}

.app-sidebar__brand {
  display: block;
  margin-bottom: 1.5rem;
  background-image: none;
}

.app-sidebar__title {
  display: block;
  margin-top: 0.5rem;
  font-weight: 700;
  color: var(--text-title-grey);
}

.app-sidebar__nav {
  flex: 1;
}

.app-sidebar__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.app-sidebar__link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 0.5rem;
  background-image: none;
  color: var(--text-default-grey);
}

.app-sidebar__link.is-active {
  background-color: var(--background-contrast-info);
  box-shadow: inset 2px 0 0 var(--border-action-high-blue-france);
  color: var(--text-action-high-blue-france);
  font-weight: 700;
}

.app-sidebar__user {
  width: 100%;
  justify-content: flex-start;
  margin-top: 1rem;
}

.app-sidebar__role {
  margin-left: auto;
}

.app-sidebar__version {
  margin-top: 0.5rem;
  padding-left: 0.5rem;
  color: var(--text-mention-grey);
}

.app-sidebar__version--differ {
  color: var(--text-default-warning);
  font-weight: 700;
}

.app-sidebar__user-id {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 47.98em) {
  .app-sidebar {
    width: 100%;
    border-right: 0;
    border-bottom: 1px solid var(--border-default-grey);
  }

  .app-sidebar__nav {
    flex: none;
  }
}
</style>
