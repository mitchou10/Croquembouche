<script setup lang="ts">
import { computed } from 'vue'
import StatTile from '../components/StatTile.vue'
import WorkerServiceCard from '../components/WorkerServiceCard.vue'
import { ago, useWorkers } from '../composables/useWorkers'

// The administrator's view of the workers: which are there, in which version, and whether their instances are alive. Each
// instance tells the backend which tasks it can be given when it starts, then that it is alive every 30 seconds; it is down
// when it has not for 90.
const { services, loaded, loading, failed, now, loadedAt, refresh } = useWorkers()

const instances = computed(() => services.value.flatMap((s) => s.instances))
const online = computed(() => instances.value.filter((i) => i.online).length)
const tasks = computed(() => new Set(services.value.flatMap((s) => s.tasks.map((t) => `${t.name}@${t.version}`))).size)
</script>

<template>
  <div class="workers">
    <header class="workers__head">
      <h1 class="workers__title fr-h3 fr-mb-0">Services</h1>
      <DsfrBadge label="Administrateur" type="info" small />
      <span v-if="loadedAt" class="workers__updated" data-testid="updated">Mis à jour {{ ago(new Date(loadedAt).toISOString(), now) }}</span>
      <button type="button" class="fr-btn fr-btn--secondary fr-btn--sm" :disabled="loading" data-testid="refresh" @click="refresh">
        {{ loading ? 'Actualisation…' : 'Actualiser' }}
      </button>
    </header>

    <p v-if="failed" class="fr-error-text" role="alert" data-testid="workers-fault">{{ failed }}</p>

    <section class="workers__stats" aria-label="Chiffres des services">
      <StatTile :value="services.length" label="Services" />
      <StatTile :value="online" label="Instances en ligne" tone="success" />
      <StatTile :value="instances.length - online" label="Instances hors ligne" :tone="instances.length - online ? 'error' : undefined" />
      <StatTile :value="tasks" label="Tâches (nom et version)" />
    </section>

    <p v-if="loaded && !services.length && !failed" role="status" data-testid="no-workers">
      Aucun worker ne s’est déclaré. Un worker déclare ses tâches au backend quand il démarre ; s’il tourne, vérifiez qu’il joint le backend (<code>BACKEND_URL</code>,
      <code>INTERNAL_API_KEY</code>).
    </p>

    <WorkerServiceCard v-for="service in services" :key="service.name" :service="service" :now="now" />
  </div>
</template>

<style scoped>
.workers {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.workers__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
}

.workers__title {
  margin-right: auto;
}

.workers__updated {
  color: var(--text-mention-grey);
  font-size: 0.875rem;
}

.workers__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem;
}
</style>
