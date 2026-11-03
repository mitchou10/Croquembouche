<script setup lang="ts">
const features = [
  { title: 'Un catalogue de modèles', description: 'Rassemblez les logos, tampons et signatures à retrouver dans vos documents.' },
  { title: 'Des analyses en lot', description: 'Lancez la recherche sur des centaines d’images et suivez son avancement.' },
  { title: 'Des résultats exploitables', description: 'Consultez le nombre de correspondances trouvées pour chaque analyse.' },
]
</script>

<template>
  <div class="landing">
    <DsfrHeader
      service-title="Croquembouche"
      service-description="Recherche de motifs dans vos documents"
      :logo-text="['République', 'Française']"
      :quick-links="[{ label: 'Se connecter', to: { name: 'login' }, icon: { name: 'fr-icon-lock-line', ssr: true } }]"
    />

    <main id="contenu" class="landing__main">
      <section class="fr-container landing__hero">
        <h1 class="fr-h2 fr-mb-2w">Retrouvez un motif dans toutes vos images</h1>
        <p class="fr-text--lead fr-mb-3w">
          Croquembouche détecte automatiquement un modèle (logo, tampon, signature…) dans vos documents numérisés.
        </p>
        <RouterLink class="fr-btn fr-btn--lg" :to="{ name: 'login' }">Se connecter</RouterLink>
      </section>

      <section class="landing__features fr-background-alt--grey" aria-label="Ce que vous pouvez faire">
        <div class="fr-container">
          <div class="fr-grid-row fr-grid-row--gutters">
            <div v-for="feature in features" :key="feature.title" class="fr-col-12 fr-col-md-4">
              <DsfrCard :title="feature.title" :description="feature.description" no-arrow />
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- A slim footer, with what the law asks for: the big DSFR one is taller than the rest of the page. -->
    <footer class="fr-footer landing__footer" role="contentinfo">
      <div class="fr-container">
        <ul class="fr-footer__bottom-list">
          <li class="fr-footer__bottom-item"><span class="fr-footer__bottom-link">Accessibilité : non conforme</span></li>
          <li class="fr-footer__bottom-item"><span class="fr-footer__bottom-link">Mentions légales</span></li>
          <li class="fr-footer__bottom-item"><span class="fr-footer__bottom-link">Données personnelles</span></li>
          <li class="fr-footer__bottom-item"><span class="fr-footer__bottom-link">Gestion des cookies</span></li>
        </ul>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
}

.landing__main {
  display: flex;
  flex: 1;
  flex-direction: column;
}

/* The hero takes the room there is, with the features at the bottom of it. */
.landing__hero {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-block: 1.5rem;
  text-align: center;
}

.landing__features {
  padding-block: 1.5rem;
}

.landing__footer {
  padding-block: 0.75rem;
}

.landing__footer .fr-footer__bottom-list {
  margin: 0;
}
</style>
