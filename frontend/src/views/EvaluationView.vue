<script setup lang="ts">
import { computed, ref } from 'vue'
import FixedPage from '../components/FixedPage.vue'
import QualityOverviewPanel from '../components/QualityOverviewPanel.vue'
import TabList from '../components/TabList.vue'
import { useSession } from '../composables/useSession'

// How right the analysis is, from what people decide of its predictions: the person's own tests, and for an
// administrator everyone's. No set of documents is needed: the figures grow with every decision.
const { isAdmin } = useSession()
const tab = ref<'mine' | 'everyone'>('mine')
const tabs = computed(() => [
  { id: 'mine', label: 'Mes décisions' },
  ...(isAdmin.value ? [{ id: 'everyone', label: 'Tous les utilisateurs' }] : []),
])
</script>

<template>
  <FixedPage>
    <template #header>
      <div class="evaluation__title">
        <h1 class="fr-h3 fr-mb-0">Évaluation</h1>
        <p class="fr-mb-0">La qualité de l’analyse, d’après ce que vous validez et corrigez.</p>
      </div>
    </template>
    <TabList v-if="tabs.length > 1" v-model="tab" :tabs="tabs" label="Périmètre de l’évaluation" />
    <QualityOverviewPanel :key="tab" :scope="tab" />
  </FixedPage>
</template>

<style scoped>
.evaluation__title {
  margin-right: auto;
}
</style>
