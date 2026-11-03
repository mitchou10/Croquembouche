import { onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * True on a screen at least `minEm` wide. 64 em by default: wide enough for the two-halves layout of a model's page, as
 * in TemplateLayout's CSS. The catalogue fixes its page from 48 em, where the sidebar stops stacking above the content.
 */
export function useWideScreen(minEm = 64) {
  const wide = ref(false)
  let query: MediaQueryList | undefined
  const sync = () => (wide.value = !!query?.matches)

  onMounted(() => {
    query = window.matchMedia?.(`(min-width: ${minEm}em)`)
    sync()
    query?.addEventListener('change', sync)
  })
  onBeforeUnmount(() => query?.removeEventListener('change', sync))

  return wide
}
