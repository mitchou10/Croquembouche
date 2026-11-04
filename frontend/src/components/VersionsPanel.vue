<script setup lang="ts">
import { ref, watch } from 'vue'
import { fetchVersions } from '../data/api'
import type { TemplateVersion } from '../data/mock'
import ConfirmButton from './ConfirmButton.vue'

/**
 * The history of a model: every version X.Y.Z it has had, the newest first. X is the example document, Y what describes
 * the model, Z its entities. The owner can go back to one, which makes a new version: history is never rewritten.
 */
const props = defineProps<{
  templateId: string
  /** The version the model is at now. */
  current: string
  canRestore: boolean
  /** Goes back to a version; says whether it went through. */
  restore: (version: string) => Promise<boolean>
}>()

const versions = ref<TemplateVersion[] | null>(null)
const failed = ref(false)

async function load() {
  failed.value = false
  try {
    versions.value = await fetchVersions(props.templateId)
  } catch {
    failed.value = true
  }
}

// Reloaded when the model changes: another model, or a version it just went up to (going back makes one).
watch(() => [props.templateId, props.current], load, { immediate: true })

async function goBack(version: string) {
  await props.restore(version)
}
</script>

<template>
  <div class="versions" data-testid="versions">
    <p v-if="failed" class="fr-error-text" role="alert">Impossible de charger les versions.</p>
    <p v-else-if="!versions" role="status">Chargement…</p>
    <ol v-else class="versions__list">
      <li v-for="item in versions" :key="item.version" class="versions__item" data-testid="version">
        <div class="versions__head">
          <strong data-testid="version-number">v{{ item.version }}</strong>
          <DsfrBadge v-if="item.version === current" label="Courante" type="success" small no-icon />
          <span class="versions__meta">{{ item.date }} · {{ item.authorName }}</span>
        </div>
        <p v-if="item.document" class="versions__document fr-mb-0">{{ item.document.name }}</p>
        <ConfirmButton
          v-if="canRestore && item.version !== current"
          label="Revenir à cette version"
          icon="fr-icon-arrow-go-back-line"
          question="Revenir à cette version ?"
          confirm-label="Oui, revenir"
          @confirm="goBack(item.version)"
        />
      </li>
    </ol>
    <p class="versions__hint fr-hint-text fr-mb-0">
      X : le document d’exemple · Y : ce qui décrit le modèle · Z : ses entités. Revenir à une version en crée une nouvelle.
    </p>
  </div>
</template>

<style scoped>
.versions {
  display: grid;
  gap: 0.75rem;
}

.versions__list {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.versions__item {
  display: grid;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-default-grey);
}

.versions__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.versions__meta,
.versions__document {
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}
</style>
