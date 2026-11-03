<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)
</script>

<template>
  <main>
    <h1>Croquembouche</h1>
    <button type="button" @click="count++">Clics : {{ count }}</button>
  </main>
</template>
