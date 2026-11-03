<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSession } from '../composables/useSession'

const route = useRoute()
const router = useRouter()
const { login } = useSession()

const identifier = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  if (!login(identifier.value)) {
    error.value = 'Renseignez votre identifiant.'
    return
  }
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  // Only follow in-app paths: "//host" or "https://host" would turn the login page into an open redirect.
  await router.push(redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : { name: 'catalogue' })
}
</script>

<template>
  <DsfrHeader
    service-title="Croquembouche"
    service-description="Recherche de motifs dans vos documents"
    :logo-text="['République', 'Française']"
  />

  <main id="contenu" class="fr-container fr-py-8w">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-6">
        <h1 class="fr-h3">Connexion</h1>
        <DsfrAlert
          type="info"
          small
          description="Connexion simulée : n’importe quel identifiant fonctionne pour l’instant. « admin » donne les droits d’administrateur."
          class="fr-mb-3w"
        />
        <form novalidate @submit.prevent="submit">
          <DsfrInputGroup
            v-model="identifier"
            label="Identifiant"
            :label-visible="true"
            :error-message="error"
            :is-invalid="!!error"
            autocomplete="username"
            class="fr-mb-2w"
          />
          <DsfrInput
            v-model="password"
            label="Mot de passe"
            label-visible
            type="password"
            autocomplete="current-password"
            class="fr-mb-3w"
          />
          <DsfrButton type="submit" label="Se connecter" />
        </form>
      </div>
    </div>
  </main>
</template>
