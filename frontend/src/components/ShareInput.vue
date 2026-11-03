<script setup lang="ts">
import { ref } from 'vue'
import { MAX_SHARES, parseShare, sameShare } from '../composables/shares'
import type { Group, Share } from '../data/mock'

const props = defineProps<{
  /** The groups that exist: offered in the browser's list, and the only ones that can be named. */
  groups: Group[]
  /** When off the table (the analysis is public): nothing to add or take away, what was chosen is kept. */
  disabled?: boolean
}>()
/** The recipients. */
const shares = defineModel<Share[]>({ required: true })

const draft = ref('')
const error = ref('')
const input = ref<HTMLInputElement>()
const listId = `shares-${Math.random().toString(36).slice(2, 8)}`

/** Takes what is typed as a recipient. False when it is something else, which then stays in the field with the reason. */
function commit(value = draft.value): boolean {
  const text = value.trim()
  if (!text) {
    error.value = ''
    return true
  }
  const share = parseShare(text, props.groups)
  if (!share) {
    error.value = `« ${text} » n’est ni une adresse e-mail ni un groupe connu.`
    return false
  }
  if (!shares.value.some((s) => sameShare(s, share))) {
    if (shares.value.length >= MAX_SHARES) {
      error.value = `${MAX_SHARES} destinataires au plus.`
      return false
    }
    shares.value = [...shares.value, share]
  }
  draft.value = ''
  error.value = ''
  return true
}

function remove(share: Share) {
  shares.value = shares.value.filter((s) => !sameShare(s, share))
  input.value?.focus()
}

// Picking a group in the browser's list is not typing: it adds it at once. An address, even a whole one, waits for Enter.
function onInput(event: Event) {
  error.value = ''
  const { inputType } = event as InputEvent
  const matches = props.groups.some((g) => g.name.toLowerCase() === draft.value.trim().toLowerCase())
  if (inputType === 'insertReplacementText' || (inputType === undefined && matches)) commit()
}

// Backspace in an empty field takes back the last recipient, as in any tag field.
function onBackspace() {
  if (!draft.value && shares.value.length) shares.value = shares.value.slice(0, -1)
}

defineExpose({ commit, draft })
</script>

<template>
  <div class="share">
    <label class="fr-label" :for="`${listId}-input`">Partager avec</label>
    <!-- Recipients and text field in one line, like any other field of the form. -->
    <div class="share__box" :class="{ 'share__box--disabled': disabled }" @click="input?.focus()">
      <ul v-if="shares.length" class="share__tags" aria-label="Destinataires">
        <li v-for="share in shares" :key="`${share.kind}:${share.value}`">
          <button
            type="button"
            class="fr-tag fr-tag--sm fr-tag--dismiss share__tag"
            :class="{ 'share__tag--group': share.kind === 'group' }"
            :disabled="disabled"
            :aria-label="`Retirer ${share.kind === 'group' ? 'le groupe' : 'l’adresse'} ${share.value}`"
            :title="share.kind === 'group' ? `Groupe ${share.value}` : share.value"
            @click.stop="remove(share)"
          >
            {{ share.value }}
          </button>
        </li>
      </ul>
      <input
        :id="`${listId}-input`"
        ref="input"
        v-model="draft"
        class="share__input"
        type="text"
        inputmode="email"
        :list="groups.length ? listId : undefined"
        :disabled="disabled"
        autocomplete="off"
        :placeholder="disabled ? 'Visible par tous' : shares.length ? '' : 'E-mail ou groupe…'"
        :aria-invalid="!!error"
        :aria-describedby="error ? `${listId}-error` : undefined"
        title="Saisissez une adresse e-mail, ou choisissez un groupe, puis Entrée"
        @input="onInput"
        @keydown.enter.prevent="commit()"
        @keydown.backspace="onBackspace"
        @blur="commit()"
      />
      <datalist v-if="groups.length" :id="listId">
        <option
          v-for="group in groups.filter((g) => !shares.some((s) => s.kind === 'group' && s.value === g.name))"
          :key="group.id"
          :value="group.name"
          :label="`Groupe · ${group.name}`"
        />
      </datalist>
    </div>
    <p v-if="error" :id="`${listId}-error`" class="share__error fr-error-text fr-mb-0" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
/* Looks like the other fields of the form. */
.share__box {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.375rem;
  min-height: 2.5rem;
  /* An address is long: the recipients go onto several lines, up to this height, then the field scrolls. */
  max-height: 6rem;
  margin-top: 0.5rem;
  padding: 0.25rem 0.5rem;
  overflow-y: auto;
  border-radius: 0.25rem 0.25rem 0 0;
  background-color: var(--background-contrast-grey);
  box-shadow: inset 0 -2px 0 0 var(--border-plain-grey);
  cursor: text;
}

.share__box:focus-within {
  outline: 2px solid #0a76f6;
  outline-offset: 2px;
}

.share__box--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.share__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  min-width: 0;
  max-width: 100%;
  margin: 0;
  padding: 0;
  list-style: none;
}

.share__tags li {
  flex: none;
}

/* A group looks different from a person. */
.share__tag--group {
  background-color: var(--background-contrast-info);
  color: var(--text-action-high-blue-france);
}

.share__input {
  flex: 1 1 6rem;
  min-width: 6rem;
  padding: 0.25rem 0;
  border: 0;
  background: transparent;
  color: var(--text-default-grey);
  font: inherit;
  outline: none;
}

.share__error {
  margin-top: 0.25rem;
  font-size: 0.8125rem;
}
</style>
