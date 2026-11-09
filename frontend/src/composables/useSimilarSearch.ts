import { computed, onBeforeUnmount, ref } from 'vue'
import { DEFAULT_NEIGHBOURS, findNeighbours, MAX_NEIGHBOURS, MIN_NEIGHBOURS, sheetImage, type Neighbourhood } from '../data/similar'

/**
 * The search for the documents that look like one that is sent: the file, how many are wanted (`k`) and what was found.
 * Changing `k` searches again for the same file; a search that was overtaken by a newer one is forgotten.
 */
export function useSimilarSearch() {
  const file = ref<File | null>(null)
  const k = ref(DEFAULT_NEIGHBOURS)
  const found = ref<Neighbourhood | null>(null)
  const loading = ref(false)
  const error = ref('')
  // A picture of the file, to draw it in the graph: an image shows itself, anything else (a PDF) a sheet.
  const previewUrl = ref('')
  let latest = 0

  const preview = (target: File) => {
    if (previewUrl.value.startsWith('blob:')) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = target.type.startsWith('image/') ? URL.createObjectURL(target) : sheetImage(215, target.size)
  }

  async function run() {
    if (!file.value) return
    const mine = ++latest
    loading.value = true
    error.value = ''
    try {
      const answer = await findNeighbours(file.value, k.value)
      if (mine === latest) found.value = answer
    } catch {
      if (mine === latest) error.value = 'La recherche a échoué. Réessayez dans un instant.'
    } finally {
      if (mine === latest) loading.value = false
    }
  }

  async function search(target: File) {
    file.value = target
    preview(target)
    found.value = null
    await run()
  }

  /** How many are wanted, kept between the limits; searches again when there is a file. */
  async function setK(value: number) {
    const next = Number.isFinite(value) ? Math.max(MIN_NEIGHBOURS, Math.min(MAX_NEIGHBOURS, Math.round(value))) : DEFAULT_NEIGHBOURS
    if (next === k.value) return
    k.value = next
    await run()
  }

  function reset() {
    latest++
    file.value = null
    found.value = null
    loading.value = false
    error.value = ''
    if (previewUrl.value.startsWith('blob:')) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }

  onBeforeUnmount(reset)

  return { file, k, found, loading, error, previewUrl, hasResult: computed(() => !!found.value), search, setK, reset }
}
