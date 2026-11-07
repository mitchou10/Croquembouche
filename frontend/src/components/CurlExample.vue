<script setup lang="ts">
import { computed, ref } from 'vue'
import { curlExamples } from '../composables/curlExample'

/**
 * A button that shows how to try the analysis from a terminal: the `curl` commands to send a document and to read what
 * was found, ready to copy, for this analysis and as the page is set (the capture kept or not).
 */
const props = defineProps<{ analysisId: string; keepScreenshot: boolean }>()

const open = ref(false)
const examples = computed(() => curlExamples({ origin: window.location.origin, analysisId: props.analysisId, keepScreenshot: props.keepScreenshot }))

// Which command was just copied, or failed to be: said for a moment, beside its button.
const copied = ref<{ index: number; ok: boolean } | null>(null)
let timer: ReturnType<typeof setTimeout> | undefined
async function copy(index: number) {
  let ok = true
  try {
    await navigator.clipboard.writeText(examples.value[index].command)
  } catch {
    ok = false
  }
  copied.value = { index, ok }
  clearTimeout(timer)
  timer = setTimeout(() => (copied.value = null), 2000)
}
</script>

<template>
  <div class="curl">
    <button
      type="button"
      class="fr-btn fr-btn--sm fr-btn--tertiary fr-icon-terminal-box-line fr-btn--icon-left"
      :aria-expanded="open"
      aria-controls="curl-example"
      data-testid="curl-button"
      @click="open = !open"
    >
      Tester avec curl
    </button>

    <section v-if="open" id="curl-example" class="curl__panel" aria-label="Exemple pour tester l’analyse avec curl" data-testid="curl-panel">
      <p class="fr-text--sm fr-mb-0">
        Envoyez un document à cette analyse depuis un terminal, puis lisez ce qu’elle a trouvé. L’analyse est rendue tout de suite avec un
        <code>id</code> : le résultat se précise ensuite (<code>status</code> : <code>running</code>, puis <code>done</code> ou <code>failed</code>).
      </p>

      <div v-for="(example, index) in examples" :key="example.title" class="curl__example" data-testid="curl-example">
        <div class="curl__head">
          <strong class="fr-text--sm">{{ example.title }}</strong>
          <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary fr-icon-clipboard-line fr-btn--icon-left" data-testid="curl-copy" @click="copy(index)">
            Copier
          </button>
          <span class="fr-hint-text" role="status" data-testid="curl-copied">{{ copied?.index === index ? (copied.ok ? 'Copié' : 'Copie impossible') : '' }}</span>
        </div>
        <pre class="curl__code" data-testid="curl-command"><code>{{ example.command }}</code></pre>
      </div>

      <ul class="fr-text--sm fr-mb-0 curl__notes">
        <li><code>$TOKEN</code> : le jeton d’accès Keycloak de votre compte. Ce que l’analyse trouve n’est visible que par la personne qui l’a lancée.</li>
        <li><code>mon-document.pdf</code> : une image (PNG, JPEG, WebP, GIF) ou un PDF, 20 Mo au plus.</li>
        <li><code>keepScreenshot</code> : <code>true</code> pour garder une capture du document (comme la case « Enregistrer une capture »), <code>false</code> sinon.</li>
        <li><code>jq</code> sert à lire le JSON ; sans lui, l’<code>id</code> est dans la réponse.</li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.curl {
  display: grid;
  gap: 0.5rem;
  min-width: 0;
}

.curl > button {
  justify-self: start;
}

/* As wide as the column and no more: a long command scrolls in its box instead of running under what is beside. */
.curl__panel {
  display: grid;
  gap: 0.75rem;
  min-width: 0;
  max-width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--border-default-grey);
  background: var(--background-alt-grey);
}

.curl__example {
  min-width: 0;
}

.curl__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.curl__code {
  margin: 0.25rem 0 0;
  padding: 0.5rem 0.75rem;
  overflow-x: auto;
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  font-size: 0.8125rem;
  line-height: 1.5;
}

.curl__notes {
  padding-left: 1.25rem;
}
</style>
