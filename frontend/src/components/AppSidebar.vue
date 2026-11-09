<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSession } from '../composables/useSession'
import { useVersions } from '../composables/useVersions'

const route = useRoute()
const { displayName, isAdmin, logout } = useSession()
const { frontend, backend, differ } = useVersions()

const everyone = [
  { name: 'catalogue', path: '/catalogue', label: 'Catalogue', icon: 'fr-icon-folder-2-line' },
  { name: 'analyses', path: '/analyses', label: 'Analyses', icon: 'fr-icon-search-line' },
  { name: 'search', path: '/recherche', label: 'Recherche', icon: 'fr-icon-bubble-chart-line' },
  { name: 'evaluation', path: '/evaluation', label: 'Évaluation', icon: 'fr-icon-checkbox-circle-line' },
]
// What only the administrator has.
const administrator = [{ name: 'overview', path: '/vue-d-ensemble', label: 'Vue d’ensemble', icon: 'fr-icon-line-chart-line' }]
const items = computed(() => (isAdmin.value ? [...everyone, ...administrator] : everyone))

// The menu of the account, opened from the name: what is about the person (their profile, what they consumed, signing
// out) and, at the bottom, the versions of the application.
const open = ref(false)
const account = useTemplateRef<HTMLElement>('account')
const trigger = useTemplateRef<HTMLButtonElement>('trigger')

async function toggle() {
  open.value = !open.value
  if (open.value) {
    await nextTick()
    account.value?.querySelector<HTMLElement>('[role="menuitem"]')?.focus()
  }
}

function close(giveFocusBack = false) {
  if (!open.value) return
  open.value = false
  if (giveFocusBack) trigger.value?.focus()
}

// It closes on a click elsewhere, on Escape (the focus goes back to the name), and on going to another page.
const clickedElsewhere = (event: Event) => {
  if (open.value && !account.value?.contains(event.target as Node)) close()
}
const escaped = (event: KeyboardEvent) => {
  if (event.key === 'Escape') close(true)
}
onMounted(() => document.addEventListener('pointerdown', clickedElsewhere))
onBeforeUnmount(() => document.removeEventListener('pointerdown', clickedElsewhere))
watch(() => route.fullPath, () => close())

// The backend ends the session, then Keycloak's own sign-out brings the browser back to the landing page.
function signOut() {
  close()
  return logout()
}
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

    <div ref="account" class="app-sidebar__account" @keydown="escaped">
      <div v-if="open" id="account-menu" class="app-sidebar__menu" data-testid="account-menu">
        <ul class="app-sidebar__menu-list" role="menu" aria-label="Mon compte">
          <li role="none">
            <RouterLink class="app-sidebar__menu-item fr-icon-leaf-line" role="menuitem" :to="{ name: 'my-consumption' }" data-testid="menu-consumption">Ma consommation</RouterLink>
          </li>
          <li role="none">
            <RouterLink class="app-sidebar__menu-item fr-icon-account-line" role="menuitem" :to="{ name: 'settings' }" data-testid="menu-profile">Mon profil</RouterLink>
          </li>
          <li role="none">
            <button type="button" class="app-sidebar__menu-item fr-icon-logout-box-r-line" role="menuitem" data-testid="menu-logout" @click="signOut">Se déconnecter</button>
          </li>
        </ul>
        <p
          class="app-sidebar__version fr-text--xs fr-mb-0"
          :class="{ 'app-sidebar__version--differ': differ }"
          :title="differ ? 'Le frontend et le backend ne sont pas de la même version.' : 'Les versions de l’application.'"
          data-testid="app-versions"
        >
          Front <span data-testid="app-version-frontend">v{{ frontend }}</span> · API <span data-testid="app-version-backend">{{ backend === '…' || backend === 'indisponible' ? backend : `v${backend}` }}</span>
        </p>
      </div>

      <button
        ref="trigger"
        type="button"
        class="app-sidebar__user fr-btn fr-btn--tertiary-no-outline fr-icon-account-circle-line fr-btn--icon-left"
        aria-haspopup="menu"
        :aria-expanded="open"
        aria-controls="account-menu"
        title="Mon compte"
        @click="toggle"
      >
        <span class="app-sidebar__user-id">{{ displayName }}</span>
        <DsfrBadge v-if="isAdmin" label="Admin" type="info" small data-testid="admin-badge" class="app-sidebar__role" />
      </button>
    </div>
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

.app-sidebar__account {
  position: relative;
  margin-top: 1rem;
}

.app-sidebar__user {
  width: 100%;
  justify-content: flex-start;
}

/* Opens above the name, as the name is at the bottom of the page. */
.app-sidebar__menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 0.25rem);
  left: 0;
  z-index: 10;
  padding: 0.25rem 0 0.5rem;
  border: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
  box-shadow: 0 6px 18px rgb(0 0 18 / 16%);
}

.app-sidebar__menu-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.app-sidebar__menu-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.625rem 0.75rem;
  border: 0;
  background: none;
  background-image: none;
  color: var(--text-default-grey);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.app-sidebar__menu-item:hover {
  background-color: var(--background-default-grey-hover);
}

.app-sidebar__role {
  margin-left: auto;
}

.app-sidebar__version {
  margin-top: 0.25rem;
  padding: 0.5rem 0.75rem 0;
  border-top: 1px solid var(--border-default-grey);
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
