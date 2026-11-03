<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { Template } from '../data/mock'
import DocumentViewer from './DocumentViewer.vue'
import EntitiesPane from './EntitiesPane.vue'

/**
 * The detail of a model, in a window over the page: to look at one without leaving what one is doing. Open while there
 * is a `template`; it closes with Escape, a click outside, or its button, and says so.
 */
const props = defineProps<{ template: Template | null }>()
const emit = defineEmits<{ close: [] }>()

const dialog = ref<HTMLDialogElement>()
const entityIndex = ref(0)

// The browser's own dialog: it keeps the focus inside, closes on Escape and dims the page. Where it cannot (no such
// method), it is only shown.
watch(
  () => props.template,
  async (template) => {
    entityIndex.value = 0
    await nextTick()
    const el = dialog.value
    if (!el) return
    if (template && !el.open) {
      if (typeof el.showModal === 'function') el.showModal()
      else el.setAttribute('open', '')
    } else if (!template && el.open) {
      if (typeof el.close === 'function') el.close()
      else el.removeAttribute('open')
    }
  },
  { immediate: true, flush: 'post' },
)

// A click on the dimmed area is on the dialog itself, not on what is inside it.
function onClick(event: MouseEvent) {
  if (event.target === dialog.value) emit('close')
}
</script>

<template>
  <dialog ref="dialog" class="preview" aria-labelledby="preview-title" @close="emit('close')" @click="onClick">
    <div v-if="template" class="preview__content" data-testid="preview">
      <header class="preview__header">
        <div class="preview__title">
          <h2 id="preview-title" class="fr-h4 fr-mb-0">{{ template.name }}</h2>
          <p class="fr-mb-0">
            Par <strong>{{ template.ownerName }}</strong>
            <DsfrTag v-for="category in template.categories" :key="category" :label="category" small />
          </p>
        </div>
        <button type="button" class="fr-btn fr-btn--tertiary fr-btn--sm" data-testid="preview-close" @click="emit('close')">Fermer</button>
      </header>

      <div class="preview__body" :class="{ 'preview__body--with-document': template.document }">
        <div v-if="template.document" class="preview__document">
          <DocumentViewer
            :document="template.document"
            :entities="template.entities"
            :highlight-id="template.entities[entityIndex]?.id"
            fit
          />
        </div>
        <div class="preview__details">
          <p class="preview__description fr-mb-0" data-testid="preview-description">{{ template.description }}</p>
          <EntitiesPane v-model:index="entityIndex" :template="template" />
        </div>
      </div>

      <footer class="preview__footer">
        <RouterLink class="fr-link fr-icon-arrow-right-line fr-link--icon-right" :to="{ name: 'catalogue-detail', params: { id: template.id } }">
          Ouvrir la page du modèle
        </RouterLink>
      </footer>
    </div>
  </dialog>
</template>

<style scoped>
.preview {
  width: min(62rem, 94vw);
  max-height: 92dvh;
  padding: 0;
  border: 0;
  background: var(--background-default-grey);
  box-shadow: 0 8px 32px rgb(0 0 18 / 32%);
}

.preview::backdrop {
  background: rgb(22 22 22 / 64%);
}

.preview__content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
}

.preview__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.preview__title p {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
  margin-top: 0.25rem;
}

.preview__body {
  display: grid;
  gap: 1rem;
}

.preview__document {
  /* A fixed height for the image to fit into, whole. */
  height: 20rem;
  min-width: 0;
}

.preview__details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}

.preview__description {
  max-height: 5rem;
  overflow-y: auto;
}

.preview__footer {
  display: flex;
  justify-content: flex-end;
}

@media (min-width: 48em) {
  .preview__body--with-document {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}
</style>
