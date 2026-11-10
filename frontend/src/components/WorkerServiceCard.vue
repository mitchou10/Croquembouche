<script setup lang="ts">
import { ago, type ServiceStatus, type WorkerService } from '../composables/useWorkers'

/** One worker: how it is doing, in which version, its instances and the heartbeat of each, and the tasks it has. */
defineProps<{ service: WorkerService; now: number }>()

const status: Record<ServiceStatus, { label: string; type: 'success' | 'warning' | 'error' }> = {
  online: { label: 'En ligne', type: 'success' },
  partial: { label: 'Partiellement en ligne', type: 'warning' },
  offline: { label: 'Hors ligne', type: 'error' },
}

const pretty = (schema: unknown) => JSON.stringify(schema, null, 2)
const date = (iso: string) => new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'medium' })
const online = (service: WorkerService) => service.instances.filter((i) => i.online).length
</script>

<template>
  <section class="service" :aria-labelledby="`service-${service.name}`" data-testid="service">
    <header class="service__head">
      <h2 :id="`service-${service.name}`" class="service__name fr-h5 fr-mb-0" data-testid="service-name">{{ service.name }}</h2>
      <DsfrBadge :label="status[service.status].label" :type="status[service.status].type" data-testid="service-status" />
      <span class="service__versions" data-testid="service-versions">
        <DsfrTag v-for="version in service.versions" :key="version" :label="`v${version}`" small />
      </span>
      <span class="service__count" data-testid="service-count">
        {{ online(service) }} / {{ service.instances.length }} instance{{ service.instances.length > 1 ? 's' : '' }} en ligne
      </span>
    </header>

    <div class="service__table fr-table fr-table--no-caption fr-mb-0">
      <table>
        <caption>Instances de {{ service.name }}</caption>
        <thead>
          <tr>
            <th scope="col">Instance</th>
            <th scope="col">Hôte</th>
            <th scope="col">Version</th>
            <th scope="col">Démarrée</th>
            <th scope="col">Dernier signe de vie</th>
            <th scope="col">État</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="instance in service.instances" :key="instance.id" data-testid="instance">
            <td class="service__id" data-testid="instance-id">{{ instance.id }}</td>
            <td>{{ instance.hostname ?? '—' }}</td>
            <td data-testid="instance-version">{{ instance.versions.map((v) => `v${v}`).join(', ') }}</td>
            <td>
              <time :datetime="instance.startedAt" :title="date(instance.startedAt)">{{ ago(instance.startedAt, now) }}</time>
            </td>
            <td>
              <time :datetime="instance.lastSeenAt" :title="date(instance.lastSeenAt)" data-testid="instance-heartbeat">{{ ago(instance.lastSeenAt, now) }}</time>
            </td>
            <td>
              <DsfrBadge :label="instance.online ? 'En ligne' : 'Hors ligne'" :type="instance.online ? 'success' : 'error'" small data-testid="instance-status" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3 class="fr-h6 fr-mb-0">Tâches</h3>
    <ul class="service__tasks">
      <li v-for="task in service.tasks" :key="`${task.name}@${task.version}`" data-testid="task">
        <details class="task">
          <summary class="task__summary">
            <span class="task__name" data-testid="task-name">{{ task.name }}</span>
            <DsfrTag :label="`v${task.version}`" small />
            <span class="task__description">{{ task.description }}</span>
          </summary>
          <p class="task__author fr-mb-0">Auteur : {{ task.author || '—' }} · déclarée le {{ date(task.createdAt) }}</p>
          <div class="task__schemas">
            <div>
              <h4 class="task__title">Entrée</h4>
              <pre data-testid="task-input">{{ pretty(task.inputSchema) }}</pre>
            </div>
            <div>
              <h4 class="task__title">Réglages</h4>
              <pre data-testid="task-parameters">{{ pretty(task.parameters) }}</pre>
            </div>
            <div>
              <h4 class="task__title">Sortie</h4>
              <pre data-testid="task-output">{{ pretty(task.outputSchema) }}</pre>
            </div>
          </div>
        </details>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.service {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
}

.service__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
}

.service__name {
  font-family: monospace;
}

.service__versions {
  display: flex;
  gap: 0.25rem;
}

.service__count {
  margin-left: auto;
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}

.service__table {
  overflow-x: auto;
}

.service__id {
  font-family: monospace;
  font-size: 0.8125rem;
}

.service__tasks {
  display: grid;
  gap: 0.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.task {
  border: 1px solid var(--border-default-grey);
  padding: 0.5rem 0.75rem;
}

.task__summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.75rem;
  cursor: pointer;
}

.task__name {
  font-family: monospace;
  font-weight: 700;
}

.task__description {
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}

.task__author {
  margin-top: 0.5rem;
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}

.task__schemas {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.task__title {
  margin: 0 0 0.25rem;
  font-size: 0.875rem;
}

.task pre {
  max-height: 16rem;
  margin: 0;
  padding: 0.5rem;
  overflow: auto;
  background: var(--background-contrast-grey);
  font-size: 0.75rem;
}

@media (min-width: 64em) {
  .task__schemas {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
