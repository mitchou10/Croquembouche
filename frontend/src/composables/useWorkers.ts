import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ApiError, fetchTasks } from '../data/api'
import type { Task } from '../data/tasks'

/** One instance of a worker, with what it has. */
export interface WorkerInstance {
  id: string
  hostname: string | null
  startedAt: string
  lastSeenAt: string
  online: boolean
  /** The versions of the tasks it has: one, unless it was made of several. */
  versions: string[]
  /** The names of the tasks it has. */
  tasks: string[]
}

/** How a worker is doing: every instance is alive, some are, or none. */
export type ServiceStatus = 'online' | 'partial' | 'offline'

/** A worker (`template_matching`...), with its instances and its tasks. */
export interface WorkerService {
  name: string
  status: ServiceStatus
  /** The versions its tasks are in, the newest last. */
  versions: string[]
  instances: WorkerInstance[]
  /** Its tasks, by name then version. */
  tasks: Task[]
}

const numeric = (version: string) => version.split(/[.-]/).map((part) => (/^\d+$/.test(part) ? Number(part) : -1))

/** Versions in order, the newest last: numbers as numbers. */
export function compareVersions(a: string, b: string): number {
  const [x, y] = [numeric(a), numeric(b)]
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    const diff = (x[i] ?? 0) - (y[i] ?? 0)
    if (diff) return diff
  }
  return 0
}

/**
 * The tasks of the backend, as workers: a task belongs to every worker whose instances have it. The workers by name; their
 * instances by when they started.
 */
export function groupServices(tasks: Task[]): WorkerService[] {
  const services = new Map<string, { tasks: Task[]; instances: Map<string, WorkerInstance> }>()
  for (const task of tasks) {
    for (const instance of task.instances) {
      const service = services.get(instance.service) ?? { tasks: [] as Task[], instances: new Map<string, WorkerInstance>() }
      services.set(instance.service, service)
      if (!service.tasks.includes(task)) service.tasks.push(task)
      const known = service.instances.get(instance.instanceId) ?? {
        id: instance.instanceId,
        hostname: instance.hostname,
        startedAt: instance.startedAt,
        lastSeenAt: instance.lastSeenAt,
        online: instance.online,
        versions: [],
        tasks: [],
      }
      service.instances.set(instance.instanceId, known)
      if (!known.versions.includes(task.version)) known.versions.push(task.version)
      known.tasks.push(task.name)
    }
  }
  return [...services]
    .map(([name, { tasks: own, instances }]): WorkerService => {
      const list = [...instances.values()].sort((a, b) => a.startedAt.localeCompare(b.startedAt))
      for (const instance of list) instance.versions.sort(compareVersions)
      const alive = list.filter((i) => i.online).length
      return {
        name,
        status: alive === list.length ? 'online' : alive ? 'partial' : 'offline',
        versions: [...new Set(own.map((t) => t.version))].sort(compareVersions),
        instances: list,
        tasks: own.sort((a, b) => a.name.localeCompare(b.name) || compareVersions(a.version, b.version)),
      }
    })
    .sort((a, b) => a.name.localeCompare(b.name))
}

/** « il y a 12 s », « il y a 3 min », « il y a 2 h », « il y a 5 j ». */
export function ago(iso: string, now: number): string {
  const seconds = Math.max(0, Math.round((now - Date.parse(iso)) / 1000))
  if (seconds < 5) return 'à l’instant'
  if (seconds < 60) return `il y a ${seconds} s`
  if (seconds < 3600) return `il y a ${Math.floor(seconds / 60)} min`
  if (seconds < 86_400) return `il y a ${Math.floor(seconds / 3600)} h`
  return `il y a ${Math.floor(seconds / 86_400)} j`
}

/** How often the page asks again, in milliseconds: a heartbeat is every 30 seconds, a worker is down after 90. */
export const REFRESH_MS = 10_000

/**
 * The workers and their tasks, kept up to date while the page that uses it is shown. `now` follows the clock every second,
 * so that « il y a 12 s » counts.
 */
export function useWorkers() {
  const tasks = ref<Task[]>([])
  const loaded = ref(false)
  const failed = ref('')
  const loading = ref(false)
  const now = ref(Date.now())
  const loadedAt = ref<number | null>(null)

  async function refresh() {
    loading.value = true
    try {
      tasks.value = await fetchTasks()
      failed.value = ''
      loadedAt.value = Date.now()
    } catch (error) {
      failed.value = error instanceof ApiError ? error.message : 'Le serveur est injoignable.'
    } finally {
      loaded.value = true
      loading.value = false
    }
  }

  let timer: ReturnType<typeof setInterval> | undefined
  let ticks = 0
  onMounted(() => {
    void refresh()
    timer = setInterval(() => {
      now.value = Date.now()
      if (++ticks % (REFRESH_MS / 1000) === 0) void refresh()
    }, 1000)
  })
  onBeforeUnmount(() => clearInterval(timer))

  const services = computed(() => groupServices(tasks.value))
  return { tasks, services, loaded, loading, failed, now, loadedAt, refresh }
}
