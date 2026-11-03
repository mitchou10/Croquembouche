<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useSession } from '../composables/useSession'

const route = useRoute()
const { login } = useSession()

// Back to where the visitor was going; the backend and `login` keep to in-app paths.
function signIn() {
  login(typeof route.query.redirect === 'string' ? route.query.redirect : undefined)
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
        <p>Vous allez être redirigé vers le service d’authentification pour vous identifier.</p>
        <DsfrButton label="Se connecter" icon="fr-icon-lock-line" @click="signIn" />
      </div>
    </div>
  </main>
</template>
