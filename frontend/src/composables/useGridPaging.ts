import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'

/** How many cards fit in an area: whole rows only, since a card cut by the bottom of the page would need scrolling. */
export function gridCapacity(opts: { columns: number; areaHeight: number; rowHeight: number; gap: number }): number {
  const { columns, areaHeight, rowHeight, gap } = opts
  if (columns < 1 || rowHeight <= 0 || areaHeight <= 0) return 0
  const rows = Math.floor((areaHeight + gap) / (rowHeight + gap))
  return Math.max(1, rows) * columns
}

const px = (value: string) => Number.parseFloat(value) || 0

/**
 * The number of cards per page so that a page fills `area` without scrolling, kept up to date as it is resized. The
 * grid inside it sets the sizes in CSS (its columns, its row height, its gap): they are read from there, so the two
 * cannot drift apart. Until there is something to measure (and when `enabled` is false: a narrow screen, where the
 * page scrolls as usual), it is `fallback`.
 */
export function useGridPaging(
  area: Ref<HTMLElement | undefined>,
  grid: Ref<HTMLElement | undefined>,
  options: { enabled: Ref<boolean>; fallback?: number },
) {
  const fallback = options.fallback ?? 6
  const pageSize = ref(fallback)
  let observer: ResizeObserver | undefined

  function measure() {
    if (!options.enabled.value || !area.value || !grid.value) {
      pageSize.value = fallback
      return
    }
    const style = getComputedStyle(grid.value)
    const columns = style.gridTemplateColumns.split(' ').filter((c) => px(c) > 0).length
    const size = gridCapacity({
      columns,
      areaHeight: area.value.clientHeight,
      rowHeight: px(style.gridAutoRows),
      gap: px(style.rowGap),
    })
    pageSize.value = size || fallback
  }

  onMounted(() => {
    measure()
    if (typeof ResizeObserver === 'undefined' || !area.value) return
    observer = new ResizeObserver(measure)
    observer.observe(area.value)
  })
  // The grid is not there while the list is empty: it is measured once it appears.
  watch([grid, options.enabled], measure, { flush: 'post' })
  onBeforeUnmount(() => observer?.disconnect())

  return { pageSize, measure }
}
