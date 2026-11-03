<script setup lang="ts">
import { ref } from 'vue'
import { useSession } from '../composables/useSession'

const { displayName: accountName, logout } = useSession()

const displayName = ref(accountName.value ?? '')
const language = ref('fr')
const notifications = ref(true)
const saved = ref(false)

// Nothing is persisted yet: the form only shows what the settings page will offer.
function save() {
  saved.value = true
}

// The backend ends the session, then Keycloak's own sign-out brings the browser back to the landing page.
function signOut() {
  return logout()
}
</script>

<template>
  <h1 class="fr-h3">Paramètres</h1>

  <DsfrAlert v-if="saved" type="success" small description="Vos paramètres ont été enregistrés." class="fr-mb-3w" />

  <form class="settings-form" @submit.prevent="save">
    <DsfrInput v-model="displayName" label="Nom affiché" label-visible class="fr-mb-3w" @update:model-value="saved = false" />
    <DsfrSelect
      v-model="language"
      label="Langue"
      :options="[
        { value: 'fr', text: 'Français' },
        { value: 'en', text: 'English' },
      ]"
      class="fr-mb-3w"
    />
    <DsfrToggleSwitch v-model="notifications" label="Recevoir un e-mail à la fin d’une analyse" class="fr-mb-3w" />
    <ul class="fr-btns-group fr-btns-group--inline-md">
      <li><DsfrButton type="submit" label="Enregistrer" /></li>
      <li><DsfrButton type="button" label="Se déconnecter" secondary @click="signOut" /></li>
    </ul>
  </form>
</template>

<style scoped>
.settings-form {
  max-width: 32rem;
}
</style>
