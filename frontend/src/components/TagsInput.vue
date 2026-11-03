<script setup lang="ts">
import { ref } from 'vue'
import { cleanList } from '../composables/useCatalogue'

const props = withDefaults(
  defineProps<{
    label: string
    placeholder?: string
    /** Offered in the browser's list; picking one adds it at once. */
    suggestions?: string[]
    maxLength?: number
    /** When reached, nothing more can be added. */
    maxItems?: number
    /** « tampon » and « Tampon » are the same tag. */
    ignoreCase?: boolean
    /** A taller field where the tags wrap onto several lines, to stand level with a two-line text area. */
    multiline?: boolean
  }>(),
  { placeholder: '', suggestions: () => [], maxLength: 30, maxItems: Infinity, ignoreCase: false, multiline: false },
)
/** The tags. */
const tags = defineModel<string[]>({ required: true })

const draft = ref('')
const listId = `tags-${Math.random().toString(36).slice(2, 8)}`
const input = ref<HTMLInputElement>()

const full = () => tags.value.length >= props.maxItems

function add(value = draft.value) {
  if (!full()) {
    const next = cleanList([...tags.value, value.slice(0, props.maxLength)], props.ignoreCase)
    if (next.length > tags.value.length) tags.value = next
  }
  draft.value = ''
}

function remove(tag: string) {
  tags.value = tags.value.filter((t) => t !== tag)
  input.value?.focus()
}

// Picking a suggestion in the browser's list is not typing: browsers report it as a replacement of the text (or as a
// plain event with no input type), and it adds the tag at once. Typing a name, even a whole one, waits for Enter.
function onInput(event: Event) {
  const { inputType } = event as InputEvent
  const matches = props.suggestions.some((s) => s.toLowerCase() === draft.value.trim().toLowerCase())
  if (inputType === 'insertReplacementText' || (inputType === undefined && matches)) add()
}

// Backspace in an empty field takes back the last tag, as in any tag field.
function onBackspace() {
  if (!draft.value && tags.value.length) tags.value = tags.value.slice(0, -1)
}
</script>

<template>
  <div class="tags-input">
    <label class="fr-label" :for="`${listId}-input`">{{ label }}</label>
    <!-- Tags and text field in one line, so the field has the height of any other and the form does not grow. -->
    <div class="tags-input__box" :class="{ 'tags-input__box--multiline': multiline }" @click="input?.focus()">
      <ul v-if="tags.length" class="tags-input__tags" :aria-label="`${label} : valeurs choisies`">
        <li v-for="tag in tags" :key="tag">
          <button type="button" class="fr-tag fr-tag--sm fr-tag--dismiss" :aria-label="`Retirer ${tag}`" @click.stop="remove(tag)">
            {{ tag }}
          </button>
        </li>
      </ul>
      <input
        :id="`${listId}-input`"
        ref="input"
        v-model="draft"
        class="tags-input__input"
        type="text"
        :list="suggestions.length ? listId : undefined"
        :maxlength="maxLength"
        :disabled="full()"
        autocomplete="off"
        :placeholder="full() ? `${maxItems} au plus` : tags.length ? '' : placeholder"
        title="Saisissez ou choisissez une valeur, puis Entrée"
        @input="onInput"
        @keydown.enter.prevent="add()"
        @keydown.backspace="onBackspace"
        @blur="add()"
      />
      <datalist v-if="suggestions.length" :id="listId">
        <option v-for="suggestion in suggestions.filter((s) => !tags.includes(s))" :key="suggestion" :value="suggestion" />
      </datalist>
    </div>
  </div>
</template>

<style scoped>
/* Looks like the other fields of the form. */
.tags-input__box {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  min-height: 2.5rem;
  margin-top: 0.5rem;
  padding: 0 0.5rem;
  border-radius: 0.25rem 0.25rem 0 0;
  background-color: var(--background-contrast-grey);
  box-shadow: inset 0 -2px 0 0 var(--border-plain-grey);
  cursor: text;
}

.tags-input__box:focus-within {
  outline: 2px solid #0a76f6;
  outline-offset: 2px;
}

/* Same height as a text area of two lines (4 rem): the two stand level, top and bottom. The tags wrap, and past that
   the field scrolls. */
.tags-input__box--multiline {
  flex-wrap: wrap;
  align-content: flex-start;
  align-items: flex-start;
  height: 4rem;
  padding-block: 0.375rem;
  overflow-y: auto;
}

.tags-input__box--multiline .tags-input__tags {
  flex-wrap: wrap;
  max-width: 100%;
  overflow: visible;
}

.tags-input__box--multiline .tags-input__input {
  padding-block: 0.25rem;
}

/* Many tags scroll sideways rather than push the field taller; the text field keeps room to type. */
.tags-input__tags {
  display: flex;
  flex: 0 1 auto;
  gap: 0.25rem;
  min-width: 0;
  max-width: 70%;
  margin: 0;
  padding: 0;
  overflow-x: auto;
  list-style: none;
}

.tags-input__tags li {
  flex: none;
}

.tags-input__input {
  flex: 1;
  min-width: 4.5rem;
  padding: 0.5rem 0;
  border: 0;
  background: transparent;
  color: var(--text-default-grey);
  font: inherit;
  outline: none;
}
</style>
