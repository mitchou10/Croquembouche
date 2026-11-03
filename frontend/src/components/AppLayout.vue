<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    <main id="contenu" class="app-layout__content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.app-layout__content {
  flex: 1;
  min-width: 0;
  padding: 1.5rem;
}

@media (max-width: 47.98em) {
  .app-layout {
    flex-direction: column;
  }
}
</style>
