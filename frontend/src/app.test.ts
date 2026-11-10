import VueDsfr from '@gouvminint/vue-dsfr'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createMemoryHistory, createRouter } from 'vue-router'
import App from './App.vue'
import { loadAnalyses, resetAnalyses, useAnalyses } from './composables/useAnalyses'
import { restoreVersion, uploadDocument } from './data/api'
import { simulatePage, simulateTest } from './test/simulate'
import { newEntity, resetCatalogue, useCatalogue } from './composables/useCatalogue'
import { loadGroups, resetGroups } from './composables/useGroups'
import { useSession } from './composables/useSession'
import { requireAuth, routes } from './router'
import { backendAnalysis, fakeFetch, droppedOldCount, reindexCount, setWorkerTasks, uploaded, workerTask } from './test/fakeBackend'

// Routes load their view on demand, which takes real time rather than just a few microtasks.
const landsOn = (router: ReturnType<typeof createRouter>, name: string) =>
  vi.waitFor(() => expect(router.currentRoute.value.name).toBe(name))

async function mountAt(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.beforeEach(requireAuth)
  await router.push(path)
  const wrapper = mount(App, { global: { plugins: [VueDsfr, router] } })
  await flushPromises()
  return { wrapper, router }
}

const { analyses } = useAnalyses()

describe('app', () => {
  beforeEach(() => {
    let blobs = 0
    URL.createObjectURL = vi.fn(() => `blob:test-${++blobs}`)
    URL.revokeObjectURL = vi.fn()
    localStorage.clear()
    resetCatalogue()
    resetAnalyses()
    resetGroups()
    useSession().setUser(null)
  })

  afterEach(() => vi.unstubAllGlobals())

  it('shows the landing page to visitors', async () => {
    const { wrapper } = await mountAt('/')
    expect(wrapper.text()).toContain('Retrouvez un motif dans toutes vos images')
  })

  it('redirects a visitor from the app to the login page', async () => {
    const { router } = await mountAt('/analyses')
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('sends the visitor to the backend to sign in, back to where they were going', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { assign })
    const { wrapper } = await mountAt('/connexion?redirect=/analyses')
    await wrapper.findAll('button').find((b) => b.text() === 'Se connecter')!.trigger('click')
    expect(assign).toHaveBeenCalledWith('/api/auth/login?redirect=%2Fanalyses')
  })

  it('does not follow an external redirect after login', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { assign })
    const { wrapper } = await mountAt('/connexion?redirect=//evil.example')
    await wrapper.findAll('button').find((b) => b.text() === 'Se connecter')!.trigger('click')
    expect(assign).toHaveBeenCalledWith('/api/auth/login?redirect=%2Fcatalogue')
  })

  it('shows the sidebar with the name of the user signed in', async () => {
    useSession().setUser('alice')
    const { wrapper } = await mountAt('/catalogue')
    const nav = wrapper.get('nav[aria-label="Navigation principale"]')
    expect(nav.text()).toContain('Catalogue')
    expect(nav.text()).toContain('Analyses')
    expect(wrapper.get('.app-sidebar__user').text()).toBe('alice')
  })

  it('opens the menu of the account from the user id: the profile, and signing out from there', async () => {
    useSession().setUser('alice')
    const { wrapper, router } = await mountAt('/catalogue')
    await wrapper.get('.app-sidebar__user').trigger('click')
    await wrapper.get('[data-testid="menu-profile"]').trigger('click')
    await landsOn(router, 'settings')
    expect(wrapper.find('[data-testid="account-menu"]').exists()).toBe(false) // it closes on the way

    const assign = vi.fn()
    vi.stubGlobal('location', { assign })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ redirectUrl: 'http://keycloak/logout' }) }))
    await wrapper.get('.app-sidebar__user').trigger('click')
    await wrapper.get('[data-testid="menu-logout"]').trigger('click')
    await vi.waitFor(() => expect(assign).toHaveBeenCalledWith('http://keycloak/logout'))
    expect(useSession().isAuthenticated.value).toBe(false)
  })

  it('has no choice of language in the profile', async () => {
    useSession().setUser('alice')
    const { wrapper } = await mountAt('/parametres')
    expect(wrapper.get('h1').text()).toBe('Mon profil')
    expect(wrapper.text()).not.toContain('Langue')
    expect(wrapper.find('select').exists()).toBe(false)
  })

  it('filters the catalogue', async () => {
    useSession().setUser('alice')
    const { wrapper } = await mountAt('/catalogue')
    await wrapper.get('input[type="search"]').setValue('QR')
    expect(wrapper.text()).toContain('Code QR de suivi')
    expect(wrapper.text()).not.toContain('Logo Marianne')
  })

  it('creates a template that the creator owns and can then pick in a new analysis', async () => {
    useSession().setUser('dana')
    const { wrapper, router } = await mountAt('/catalogue/nouveau')
    await field(wrapper, 'Nom').setValue('Tampon préfecture')
    await field(wrapper, 'Description').setValue('Tampon rectangulaire bleu')
    await wrapper.get('form').trigger('submit')
    await landsOn(router, 'catalogue-detail')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Tampon préfecture'))
    expect(wrapper.get('[data-testid="template-owner"]').text()).toBe('dana')
    expect(wrapper.get('[data-testid="template-version"]').text()).toBe('v1.0.0') // a new model starts at 1.0.0
    expect(wrapper.text()).toContain('Modifier')

    await router.push('/analyses/nouvelle')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Tampon préfecture'))
  })

  it('says who can use a model, and keeps it when the model is changed', async () => {
    useSession().setUser('dana')
    const { wrapper, router } = await mountAt('/catalogue/nouveau')
    await field(wrapper, 'Nom').setValue('Modèle de service')
    await field(wrapper, 'Description').setValue('Pour mon équipe')
    expect(wrapper.find('[data-testid="visibility"]').exists()).toBe(true)
    await wrapper.get('[data-testid="visibility"]').setValue('shared')
    const input = wrapper.get('input[title^="Saisissez une adresse"]')
    await input.setValue('julie@example.org')
    await input.trigger('keydown.enter')
    await wrapper.get('form').trigger('submit')
    await landsOn(router, 'catalogue-detail')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Modèle de service'))

    await router.push({ name: 'catalogue-edit', params: { id: String(router.currentRoute.value.params.id) } })
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Modifier le modèle'))
    expect((wrapper.get('[data-testid="visibility"]').element as HTMLSelectElement).value).toBe('shared')
    expect(wrapper.text()).toContain('julie@example.org')
  })

  it('adds a sub-model to a model: listed under it, found by search, with its own version', async () => {
    useSession().setUser('alice.martin')
    const { wrapper, router } = await mountAt('/catalogue/t1')
    expect(wrapper.find('[data-testid="parent-link"]').exists()).toBe(false)
    await wrapper.get('[data-testid="add-sub-model"]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('catalogue-new'))
    expect(wrapper.get('h1').text()).toBe('Nouveau sous-modèle')
    expect(wrapper.get('[data-testid="parent-model"]').text()).toContain('Logo Marianne')

    await field(wrapper, 'Nom').setValue('Logo Marianne, version noir et blanc')
    await field(wrapper, 'Description').setValue('Le même logo en noir et blanc')
    await wrapper.get('form').trigger('submit')
    await landsOn(router, 'catalogue-detail')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Logo Marianne, version noir et blanc'))
    expect(wrapper.get('[data-testid="parent-link"]').text()).toContain('Sous-modèle de Logo Marianne')
    expect(wrapper.find('[data-testid="add-sub-model"]').exists()).toBe(false) // one level only
    expect(wrapper.get('[data-testid="template-version"]').text()).toBe('v1.0.0')

    // The model lists it; the catalogue shows the models, and the sub-model when it is searched for.
    await router.push('/catalogue/t1')
    await vi.waitFor(() => expect(wrapper.get('[data-testid="sub-model-link"]').text()).toContain('noir et blanc'))
    await router.push('/catalogue')
    await vi.waitFor(() => expect(wrapper.get('[data-testid="children-tag"]').text()).toBe('1 sous-modèle'))
    expect(wrapper.text()).not.toContain('noir et blanc')
    await wrapper.get('input[type="search"]').setValue('noir et blanc')
    expect(wrapper.get('[data-testid="sub-model-tag"]').text()).toBe('Sous-modèle de Logo Marianne')
  })

  it('does not delete a model with sub-models before one of them is chosen to take its place', async () => {
    useSession().setUser('dana')
    const { wrapper, router } = await mountAt('/catalogue/nouveau')
    await field(wrapper, 'Nom').setValue('Racine')
    await field(wrapper, 'Description').setValue('Le modèle racine')
    await wrapper.get('form').trigger('submit')
    await landsOn(router, 'catalogue-detail')
    const rootId = String(router.currentRoute.value.params.id)
    for (const name of ['Annexe A', 'Annexe B']) {
      await router.push({ name: 'catalogue-new', query: { parent: rootId } })
      await field(wrapper, 'Nom').setValue(name)
      await field(wrapper, 'Description').setValue(`${name} du formulaire`)
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'catalogue-detail')
    }
    await router.push(`/catalogue/${rootId}`)
    await vi.waitFor(() => expect(wrapper.findAll('[data-testid="sub-model-link"]')).toHaveLength(2))

    await wrapper.get('[data-testid="delete"]').trigger('click')
    // It asks which one: every sub-model is offered, and nothing goes before one is chosen.
    const options = wrapper.findAll('[data-testid="promote-select"] option')
    expect(options.map((o) => o.text())).toEqual(['Annexe A', 'Annexe B'])
    await wrapper.get('[data-testid="promote-select"]').setValue(options[1].element.value)
    await wrapper.get('[data-testid="promote-confirm"]').trigger('click')

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('catalogue'))
    await vi.waitFor(() => expect(useCatalogue().find(rootId)).toBeUndefined())
    const [first, second] = useCatalogue()
      .templates.value.filter((t) => t.name.startsWith('Annexe'))
      .sort((x, y) => x.name.localeCompare(y.name))
    expect(second.parentId).toBeNull() // « Annexe B » took its place
    expect(first.parentId).toBe(second.id) // and « Annexe A » is under it
    expect(second.children.map((c) => c.name)).toEqual(['Annexe A'])
  })

  it('promotes a sub-model to a model of its own, which its model stops listing', async () => {
    useSession().setUser('alice.martin')
    const { wrapper, router } = await mountAt('/catalogue/nouveau')
    await field(wrapper, 'Nom').setValue('Racine P')
    await field(wrapper, 'Description').setValue('Le modèle racine')
    await wrapper.get('form').trigger('submit')
    await landsOn(router, 'catalogue-detail')
    const rootId = String(router.currentRoute.value.params.id)
    expect(wrapper.find('[data-testid="parent-link"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Promouvoir en modèle') // a root has nothing to be promoted from

    await router.push({ name: 'catalogue-new', query: { parent: rootId } })
    await field(wrapper, 'Nom').setValue('Annexe P')
    await field(wrapper, 'Description').setValue('Une annexe')
    await wrapper.get('form').trigger('submit')
    await landsOn(router, 'catalogue-detail')
    await vi.waitFor(() => expect(wrapper.get('[data-testid="parent-link"]').text()).toContain('Racine P'))

    await wrapper.get('[data-testid="delete"]').trigger('click') // « Promouvoir en modèle » (the first of the two buttons)
    await wrapper.get('[data-testid="confirm-yes"]').trigger('click')

    await vi.waitFor(() => expect(wrapper.find('[data-testid="parent-link"]').exists()).toBe(false))
    expect(useCatalogue().find(rootId)?.children).toEqual([])
    expect(wrapper.find('[data-testid="add-sub-model"]').exists()).toBe(true) // a root again: it can have sub-models
  })

  it('does not offer a sub-model to someone who does not own the model', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/t1')
    expect(wrapper.find('[data-testid="add-sub-model"]').exists()).toBe(false)
  })

  it('validates the template form', async () => {
    useSession().setUser('dana')
    const { wrapper, router } = await mountAt('/catalogue/nouveau')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('catalogue-new')
    expect(wrapper.text()).toContain('Donnez un nom au modèle.')
    expect(wrapper.text()).toContain('Ajoutez une description.')
    expect(wrapper.get('[data-testid="missing"]').text()).toBe('À compléter : le nom, la description.')
  })

  it('stars and unstars a template from its page', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/t3')
    const star = wrapper.get('[data-testid="star"]')
    expect(star.text()).toContain('Ajouter aux favoris (0)')
    await star.trigger('click')
    await flushPromises()
    expect(star.text()).toContain('Retirer des favoris (1)')
    expect(star.attributes('aria-pressed')).toBe('true')
    await star.trigger('click')
    await flushPromises()
    expect(star.text()).toContain('Ajouter aux favoris (0)')
  })

  it('lets the owner edit directly', async () => {
    useSession().setUser('bob.durand')
    const { wrapper, router } = await mountAt('/catalogue/t5/modifier')
    expect(wrapper.get('h1').text()).toBe('Modifier le modèle')
    await wrapper.findAll('input:not([type="file"])')[0].setValue('Case cochée v2')
    await wrapper.get('form').trigger('submit')
    await landsOn(router, 'catalogue-detail')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Case cochée v2'))
  })

  it('turns a non-owner edit into a suggestion that the owner accepts', async () => {
    useSession().setUser('dana')
    const first = await mountAt('/catalogue/t2')
    expect(first.wrapper.text()).toContain('Suggérer une modification')
    await first.router.push('/catalogue/t2/modifier')
    await vi.waitFor(() => expect(first.wrapper.get('h1').text()).toBe('Suggérer une modification'))
    await field(first.wrapper, 'Nom').setValue('Tampon « Reçu » v2')
    await first.wrapper.get('form').trigger('submit')
    await landsOn(first.router, 'catalogue-detail')
    // A suggestion is sent to be seen: the page opens on the suggestions.
    expect(first.router.currentRoute.value.query.onglet).toBe('suggestions')
    await vi.waitFor(() => expect(first.wrapper.text()).toContain('En attente'))
    expect(first.wrapper.get('h1').text()).toBe('Tampon « Reçu »') // unchanged until accepted
    expect(first.wrapper.text()).not.toContain('Accepter')

    useSession().setUser('bob.durand')
    const second = await mountAt('/catalogue/t2?onglet=suggestions')
    await second.wrapper.findAll('button').find((b) => b.text() === 'Accepter')!.trigger('click')
    await vi.waitFor(() => expect(second.wrapper.get('h1').text()).toBe('Tampon « Reçu » v2'))
    expect(second.wrapper.text()).toContain('Acceptée')
  })

  it('refuses a suggestion that changes nothing', async () => {
    useSession().setUser('dana')
    const { wrapper, router } = await mountAt('/catalogue/t4/modifier')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('catalogue-edit')
    expect(wrapper.text()).toContain('Modifiez au moins un champ')
  })

  describe('the administrator', () => {
    it('is named in the sidebar, and only the administrator', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const admin = await mountAt('/catalogue')
      expect(admin.wrapper.get('[data-testid="admin-badge"]').text()).toBe('Admin')
      useSession().setUser('dana')
      const other = await mountAt('/catalogue')
      expect(other.wrapper.find('[data-testid="admin-badge"]').exists()).toBe(false)
    })

    describe('the page of the services', () => {
      it('is in the sidebar of the administrator only, and anyone else is sent to the analyses', async () => {
        useSession().setUser('admin', { isAdmin: true })
        const admin = await mountAt('/catalogue')
        expect(admin.wrapper.get('a[href="/services"]').text()).toBe('Services')
        useSession().setUser('dana')
        const other = await mountAt('/catalogue')
        expect(other.wrapper.find('a[href="/services"]').exists()).toBe(false)
        const sent = await mountAt('/services')
        expect(sent.router.currentRoute.value.name).toBe('analyses')
      })

      it('shows each worker with its status, its versions and the heartbeat of its instances', async () => {
        useSession().setUser('admin', { isAdmin: true })
        const { wrapper } = await mountAt('/services')
        await vi.waitFor(() => expect(wrapper.findAll('[data-testid="service"]')).toHaveLength(2))

        const [ocr, matching] = wrapper.findAll('[data-testid="service"]')
        expect(ocr!.get('[data-testid="service-name"]').text()).toBe('ocr')
        expect(ocr!.get('[data-testid="service-status"]').text()).toBe('En ligne')
        expect(ocr!.get('[data-testid="service-versions"]').text()).toBe('v1.25.0')
        expect(matching!.get('[data-testid="service-name"]').text()).toBe('template_matching')
        expect(matching!.get('[data-testid="service-status"]').text()).toBe('Partiellement en ligne')
        // Two versions are known side by side, the newest last: one instance is up, the other two are down.
        expect(matching!.get('[data-testid="service-versions"]').text()).toBe('v1.24.0v1.25.0')
        expect(matching!.get('[data-testid="service-count"]').text()).toBe('1 / 3 instances en ligne')

        const rows = matching!.findAll('[data-testid="instance"]')
        expect(rows.map((r) => r.get('[data-testid="instance-status"]').text())).toEqual(['En ligne', 'Hors ligne', 'Hors ligne'])
        expect(rows[0]!.get('[data-testid="instance-heartbeat"]').text()).toMatch(/il y a \d+ s|à l’instant/)
        expect(rows[1]!.get('[data-testid="instance-heartbeat"]').text()).toBe('il y a 10 min')
        expect(rows.map((r) => r.get('[data-testid="instance-version"]').text())).toEqual(['v1.25.0', 'v1.25.0', 'v1.24.0'])
      })

      it('counts the services, the instances that are alive and the tasks', async () => {
        useSession().setUser('admin', { isAdmin: true })
        const { wrapper } = await mountAt('/services')
        await vi.waitFor(() => expect(wrapper.findAll('[data-testid="service"]')).toHaveLength(2))

        expect(wrapper.findAll('[data-testid="stat"]').map((s) => `${s.get('[data-testid="stat-value"]').text()} ${s.get('[data-testid="stat-label"]').text()}`)).toEqual([
          '2 Services',
          '2 Instances en ligne',
          '2 Instances hors ligne',
          '4 Tâches (nom et version)',
        ])
      })

      it('shows what a task takes, what can be set and what it gives', async () => {
        useSession().setUser('admin', { isAdmin: true })
        const { wrapper } = await mountAt('/services')
        await vi.waitFor(() => expect(wrapper.findAll('[data-testid="task"]').length).toBeGreaterThan(0))

        const task = wrapper.findAll('[data-testid="task"]').find((t) => t.get('[data-testid="task-name"]').text() === 'ocr.read_document')!
        expect(JSON.parse(task.get('[data-testid="task-input"]').text())).toMatchObject({ required: ['message'] })
        expect(JSON.parse(task.get('[data-testid="task-parameters"]').text()).properties.threshold.default).toBe(0.8)
        expect(JSON.parse(task.get('[data-testid="task-output"]').text()).properties.status).toEqual({ type: 'string' })
      })

      it('asks again when told to, and says so when no worker has declared itself', async () => {
        useSession().setUser('admin', { isAdmin: true })
        setWorkerTasks([])
        const { wrapper } = await mountAt('/services')
        await vi.waitFor(() => expect(wrapper.find('[data-testid="no-workers"]').exists()).toBe(true))

        setWorkerTasks([workerTask('ocr.ping', '1.26.0', [['ocr-new', true]])])
        await wrapper.get('[data-testid="refresh"]').trigger('click')
        await vi.waitFor(() => expect(wrapper.find('[data-testid="no-workers"]').exists()).toBe(false))
        expect(wrapper.get('[data-testid="service-versions"]').text()).toBe('v1.26.0')
        expect(wrapper.get('[data-testid="updated"]').text()).toMatch(/Mis à jour/)
      })
    })

    it('can accept a suggestion on a model it does not own', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/catalogue/t1?onglet=suggestions')
      expect(wrapper.get('[role="tablist"]').text()).toContain('1 en attente')
      // Not the owner: the page offers to suggest, not to edit.
      expect(wrapper.get('a[href$="/catalogue/t1/modifier"]').text()).toBe('Suggérer une modification')
      await wrapper.findAll('button').find((b) => b.text() === 'Accepter')!.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Acceptée')
      expect(wrapper.get('[data-testid="description"]').text()).toContain('version couleur')
    })

    it('can refuse one too', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/catalogue/t1?onglet=suggestions')
      await wrapper.findAll('button').find((b) => b.text() === 'Refuser')!.trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Refusée')
      expect(wrapper.get('[data-testid="description"]').text()).not.toContain('version couleur')
    })

    it('is told on the catalogue which models have suggestions waiting, as is their owner and not anyone else', async () => {
      const waiting = async (who: string) => {
        useSession().setUser(who, { isAdmin: who === 'admin' })
        const { wrapper } = await mountAt('/catalogue')
        return wrapper.text().includes('1 suggestion')
      }
      expect(await waiting('admin')).toBe(true)
      expect(await waiting('alice.martin')).toBe(true)
      expect(await waiting('dana')).toBe(false)
    })
  })

  describe('the catalogue, all or only one\'s own', () => {
    const tileTitles = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('.tile__title').map((t) => t.text())

    it('shows everything at first, and says which view is on', async () => {
      useSession().setUser('alice.martin')
      const { wrapper } = await mountAt('/catalogue')
      expect(button(wrapper, 'Tous').attributes('aria-pressed')).toBe('true')
      expect(button(wrapper, 'Mes modèles').attributes('aria-pressed')).toBe('false')
      expect(wrapper.get('[data-testid="list-total"]').text()).toBe('11 modèles')
    })

    it('keeps only one\'s own models, then everything again', async () => {
      useSession().setUser('alice.martin')
      const { wrapper } = await mountAt('/catalogue')
      await button(wrapper, 'Mes modèles').trigger('click')
      expect(button(wrapper, 'Mes modèles').attributes('aria-pressed')).toBe('true')
      expect(tileTitles(wrapper)).toEqual(['Logo Marianne', 'Signature type', 'Cachet de la poste', 'Logo CAF'])
      expect(wrapper.get('[data-testid="list-total"]').text()).toBe('4 modèles')
      await button(wrapper, 'Tous').trigger('click')
      expect(wrapper.get('[data-testid="list-total"]').text()).toBe('11 modèles')
    })

    it('goes with the search', async () => {
      useSession().setUser('alice.martin')
      const { wrapper } = await mountAt('/catalogue')
      await button(wrapper, 'Mes modèles').trigger('click')
      await wrapper.get('input[type="search"]').setValue('logo')
      expect(tileTitles(wrapper)).toEqual(['Logo Marianne', 'Logo CAF'])
      await wrapper.get('input[type="search"]').setValue('zzz')
      expect(wrapper.text()).toContain('Aucun modèle ne correspond à « zzz ».')
    })

    it('invites whoever has no model yet to make one', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue')
      await button(wrapper, 'Mes modèles').trigger('click')
      expect(wrapper.text()).toContain('Vous n’avez pas encore de modèle.')
      expect(wrapper.get('[data-testid="list-total"]').text()).toBe('0 modèle')
    })

    it('includes a model one has just made', async () => {
      useSession().setUser('dana')
      const { wrapper, router } = await mountAt('/catalogue/nouveau')
      await field(wrapper, 'Nom').setValue('Mon tampon')
      await field(wrapper, 'Description').setValue('Fait par moi')
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'catalogue-detail')
      await router.push('/catalogue')
      await vi.waitFor(() => expect(button(wrapper, 'Mes modèles')).toBeDefined())
      await button(wrapper, 'Mes modèles').trigger('click')
      expect(tileTitles(wrapper)).toEqual(['Mon tampon'])
    })
  })

  describe('the cards', () => {
    it('show the description of each model, the whole card being the link', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue')
      const first = wrapper.get('.tile')
      expect(first.get('.tile__description').text()).toBe('Bloc-marque de la République française.')
      expect(first.findAll('a')).toHaveLength(1)
      expect(first.get('a').attributes('href')).toBe('/catalogue/t1')
    })

    it('say what an analysis is for, or else which models it looks for', async () => {
      useSession().setUser('admin', { isAdmin: true }) // opens everything
      const { wrapper } = await mountAt('/analyses')
      const description = (title: string) =>
        wrapper.findAll('.tile').find((t) => t.get('.tile__title').text() === title)!.get('.tile__description').text()
      expect(description('Accusés de réception T3')).toBe('Tampons des accusés du troisième trimestre, à recouper avec le registre.')
      expect(description('Courriers octobre')).toBe('Logo Marianne, Filigrane « Copie »') // no description: the models
    })

    it('say whether an analysis is public, shared, or neither', async () => {
      useSession().setUser('admin', { isAdmin: true }) // opens everything
      const { wrapper } = await mountAt('/analyses')
      const sharing = (title: string) =>
        wrapper.findAll('.tile').find((t) => t.get('.tile__title').text() === title)!.find('[data-testid="sharing"]')
      expect(sharing('Courriers octobre').exists()).toBe(false) // private, and shared with no one
      expect(sharing('Accusés de réception T3').text()).toBe('Partagée · 1')
      expect(sharing('Contrats signés').text()).toBe('Partagée · 2')
      expect(sharing('Contrats signés').attributes('title')).toContain('marie.dupont@example.org, Service contentieux')
      expect(sharing('Attestations CAF').text()).toBe('Publique')
      expect(sharing('Attestations CAF').attributes('title')).toBe('Visible par tous les utilisateurs')
    })

    it('show the models and the details of each analysis', async () => {
      useSession().setUser('admin', { isAdmin: true }) // opens everything
      const { wrapper } = await mountAt('/analyses')
      const first = wrapper.get('.tile')
      expect(first.get('.tile__title').text()).toBe('Courriers octobre')
      expect(first.get('.tile__description').text()).toBe('Logo Marianne, Filigrane « Copie »')
      expect(first.text()).toContain('Terminée')
      expect(first.text()).toContain('2026-10-30 · 128 correspondances')
      expect(first.get('a').attributes('href')).toBe('/analyses/a1') // its dashboard
    })
  })

  describe('the analyses one can open', () => {
    const tile = (wrapper: ReturnType<typeof mount>, title: string) =>
      wrapper.findAll('.tile').find((t) => t.get('.tile__title').text() === title)!

    it('are links to their dashboard, and the others are named without one', async () => {
      useSession().setUser('alice.martin')
      const { wrapper } = await mountAt('/analyses')
      await vi.waitFor(() => expect(tile(wrapper, 'Accusés de réception T3').find('a').exists()).toBe(true)) // by her group, once loaded
      expect(tile(wrapper, 'Courriers octobre').get('a').attributes('href')).toBe('/analyses/a1') // hers
      expect(tile(wrapper, 'Attestations CAF').get('a').attributes('href')).toBe('/analyses/a5') // public
      const closed = tile(wrapper, 'Formulaires CERFA') // someone else's, and private
      expect(closed.find('a').exists()).toBe(false)
      expect(closed.get('[data-testid="restricted"]').text()).toBe('Accès restreint')
      expect(closed.get('.tile__description').text()).toBe('Vous n’avez pas accès à cette analyse.')
      expect(closed.text()).not.toContain('correspondance') // nothing of what is inside
    })

    it('are all of them for the administrator', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/analyses')
      expect(wrapper.findAll('.tile a').length).toBe(wrapper.findAll('.tile').length)
      expect(wrapper.findAll('[data-testid="restricted"]')).toHaveLength(0)
    })

    it('include what is shared with one\'s address or one\'s group', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/analyses')
      await vi.waitFor(() => expect(tile(wrapper, 'Courriers de la poste').find('a').exists()).toBe(true)) // group « Préfecture de Paris »
      expect(tile(wrapper, 'Courriers octobre').find('a').exists()).toBe(false)
      await wrapper.get('button[title="Page suivante"]').trigger('click') // the seventh analysis is on the second page
      expect(tile(wrapper, 'Contrats paraphés').find('a').exists()).toBe(true) // dana@example.org
    })

    it('opens the dashboard when one is clicked', async () => {
      useSession().setUser('alice.martin')
      const { wrapper, router } = await mountAt('/analyses')
      await tile(wrapper, 'Courriers octobre').get('a').trigger('click')
      await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('analysis-detail'))
      expect(router.currentRoute.value.params.id).toBe('a1')
    })
  })

  describe('the dashboard of an analysis', () => {
    const figures = (wrapper: ReturnType<typeof mount>) =>
      Object.fromEntries(wrapper.findAll('[data-testid="stat"]').map((s) => [s.get('[data-testid="stat-label"]').text(), s.get('[data-testid="stat-value"]').text()]))
    const open = async (id: string, who = 'alice.martin') => {
      // What the backend tells depends on who asks: the pages ask again for each person.
      resetAnalyses()
      resetCatalogue()
      await loadGroups()
      useSession().setUser(who, { isAdmin: who === 'admin' })
      const page = await mountAt(`/analyses/${id}`)
      await vi.waitFor(() => expect(page.wrapper.find('.fixed-page, [data-testid="no-access"]').exists()).toBe(true))
      return page
    }

    it('is deleted by its owner alone, after a confirmation, with its uses', async () => {
      const owner = await open('a1') // alice.martin's
      await owner.wrapper.get('[data-testid="delete"]').trigger('click')
      expect(owner.wrapper.get('[data-testid="confirm"]').text()).toContain('Supprimer cette analyse et ses résultats ?')
      await owner.wrapper.get('[data-testid="confirm-yes"]').trigger('click')
      await landsOn(owner.router, 'analyses')
      expect(useAnalyses().find('a1')).toBeUndefined()
      expect(backendAnalysis('a1')).toBeUndefined()
      // Someone who can open it, an administrator included, is not offered to.
      for (const who of ['dana', 'admin']) {
        expect((await open('a5', who)).wrapper.find('[data-testid="delete"]').exists()).toBe(false)
      }
    })

    it('shows the name, its state, who made it and what it looks for', async () => {
      const { wrapper } = await open('a1')
      expect(wrapper.get('h1').text()).toBe('Courriers octobre')
      expect(wrapper.find('.fr-badge').text()).toBe('Terminée')
      expect(wrapper.get('[data-testid="meta"]').text()).toContain('alice.martin')
      expect(wrapper.get('[data-testid="meta"]').text()).toContain('Logo Marianne, Filigrane « Copie »')
      expect(wrapper.get('[data-testid="sharing"]').text()).toBe('Privée')
    })

    it('shows how often it was seen and used, and how its uses went', async () => {
      const { wrapper } = await open('a1')
      // 42 views, and this one: the page is counted when it opens.
      expect(figures(wrapper)).toEqual({ Vues: '43', Utilisations: '4', Terminées: '3', 'En cours': '0', 'En erreur': '1' })
    })

    it('counts a view each time the page is opened, for whoever can', async () => {
      await open('a1')
      const second = await open('a1')
      expect(figures(second.wrapper).Vues).toBe('44')
      const { analyses } = useAnalyses()
      expect(analyses.value.find((a) => a.id === 'a1')!.views).toBe(44)
    })

    const showRuns = async (wrapper: ReturnType<typeof mount>) => {
      await wrapper.findAll('[role="tab"]').find((t) => t.text().startsWith('Utilisations'))!.trigger('click')
    }
    const showElements = async (wrapper: ReturnType<typeof mount>) => {
      await wrapper.findAll('[role="tab"]').find((t) => t.text().startsWith('Éléments'))!.trigger('click')
    }
    const showPage = async (wrapper: ReturnType<typeof mount>) => {
      await wrapper.findAll('[role="tab"]').find((t) => t.text() === 'Page')!.trigger('click')
    }

    it('names the uses on a tab, with how many there are', async () => {
      const { wrapper } = await open('a5')
      expect(wrapper.findAll('[role="tab"]').map((t) => t.text())).toEqual(['Résultat', 'Utilisations (5)'])
      expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toBe('Résultat') // the test comes first
      expect(wrapper.find('[data-testid="run"]').exists()).toBe(false)
    })

    it('lists the last uses, a page at a time', async () => {
      const { wrapper } = await open('a5') // five uses
      await showRuns(wrapper)
      expect(wrapper.findAll('[data-testid="run"]')).toHaveLength(4)
      expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('1 / 2')
      expect(wrapper.findAll('[data-testid="run"]')[0].text()).toContain('2026-10-12')
      expect(wrapper.findAll('[data-testid="run"]')[0].text()).toContain('alice.martin')
      expect(wrapper.findAll('[data-testid="run"]')[0].text()).toContain('214 correspondances')
      await wrapper.get('button[title="Page suivante"]').trigger('click')
      expect(wrapper.findAll('[data-testid="run"]')).toHaveLength(1)
      expect(wrapper.findAll('[data-testid="run"]')[0].text()).toContain('En échec')
    })

    it('has no pager when the uses fit on one page', async () => {
      const { wrapper } = await open('a1')
      await showRuns(wrapper)
      expect(wrapper.findAll('[data-testid="run"]')).toHaveLength(4)
      expect(wrapper.find('[data-testid="pager-count"]').exists()).toBe(false)
    })

    describe('the cards at the top, which filter the uses', () => {
      const tile = (wrapper: ReturnType<typeof mount>, label: string) =>
        wrapper.findAll('[data-testid="stat"]').find((t) => t.get('[data-testid="stat-label"]').text() === label)!
      const listed = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-testid="run"]').map((r) => r.text())

      it('lists only the uses that ended in error, on the tab of the uses, and says which filter is on', async () => {
        const { wrapper } = await open('a5') // five uses, one failed
        expect(wrapper.find('[data-testid="runs"]').exists()).toBe(false)
        await tile(wrapper, 'En erreur').trigger('click')
        expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toMatch(/^Utilisations/)
        expect(listed(wrapper)).toHaveLength(Number(figures(wrapper)['En erreur']))
        for (const row of listed(wrapper)) expect(row).toContain('En échec')
        expect(tile(wrapper, 'En erreur').attributes('aria-pressed')).toBe('true')
        expect(tile(wrapper, 'En cours').attributes('aria-pressed')).toBe('false')
        expect(wrapper.get('[data-testid="runs-filter"]').text()).toContain('En échec')
      })

      it('takes the filter off with the same card, with « Utilisations » or with the link', async () => {
        const { wrapper } = await open('a5')
        await tile(wrapper, 'Terminées').trigger('click')
        expect(listed(wrapper).length).toBeLessThan(Number(figures(wrapper).Utilisations))
        await tile(wrapper, 'Terminées').trigger('click') // again
        expect(listed(wrapper)).toHaveLength(4) // the first page of all five
        await tile(wrapper, 'En erreur').trigger('click')
        await tile(wrapper, 'Utilisations').trigger('click')
        expect(wrapper.find('[data-testid="runs-filter"]').exists()).toBe(false)
        await tile(wrapper, 'En erreur').trigger('click')
        await wrapper.get('[data-testid="runs-filter-clear"]').trigger('click')
        expect(wrapper.find('[data-testid="runs-filter"]').exists()).toBe(false)
        expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('1 / 2')
      })

      it('says so when no use has that state', async () => {
        const { wrapper } = await open('a1') // none is running
        await tile(wrapper, 'En cours').trigger('click')
        expect(wrapper.get('[data-testid="runs-empty"]').text()).toBe('Aucune utilisation « En cours ».')
      })

      it('does not make a button of the figure of the views', async () => {
        const { wrapper } = await open('a1')
        expect(tile(wrapper, 'Vues').element.tagName).toBe('DIV')
      })
    })

    it('says whether the analysis is public or shared', async () => {
      expect((await open('a5')).wrapper.get('[data-testid="sharing"]').text()).toBe('Publique')
      expect((await open('a4')).wrapper.get('[data-testid="sharing"]').text()).toBe('Partagée · 2')
    })

    it('is for everyone who can open the analysis: by a group, by an address, because it is public', async () => {
      expect((await open('a2', 'bob.durand')).wrapper.get('h1').text()).toBe('Accusés de réception T3') // owner
      expect((await open('a2', 'alice.martin')).wrapper.get('h1').text()).toBe('Accusés de réception T3') // her group
      expect((await open('a7', 'dana')).wrapper.get('h1').text()).toBe('Contrats paraphés') // her address
      expect((await open('a5', 'dana')).wrapper.get('h1').text()).toBe('Attestations CAF') // public
      const group = await open('a6', 'dana') // « Préfecture de Paris »
      expect(figures(group.wrapper).Utilisations).toBe('2')
    })

    it('is for the administrator whatever the analysis', async () => {
      const { wrapper } = await open('a3', 'admin')
      expect(wrapper.get('h1').text()).toBe('Formulaires CERFA')
      expect(figures(wrapper)['En erreur']).toBe('2')
    })

    it('says so, and counts nothing, when one cannot open it', async () => {
      const { wrapper } = await open('a3', 'dana')
      expect(wrapper.get('[data-testid="no-access"]').text()).toContain('Vous n’avez pas accès à cette analyse.')
      expect(wrapper.find('h1').exists()).toBe(false)
      expect(backendAnalysis('a3').views).toBe(9) // not counted: it was not opened
    })

    it('says so for an analysis that does not exist', async () => {
      useSession().setUser('alice.martin')
      await loadGroups()
      const { wrapper } = await mountAt('/analyses/nope')
      await vi.waitFor(() => expect(wrapper.text()).toContain('Cette analyse n’existe pas.'))
    })

    it('shows a new analysis as one use, running, and no view yet but its own', async () => {
      useSession().setUser('dana')
      await loadGroups()
      const created = await useAnalyses().createAnalysis({ name: 'À moi', description: 'Pour voir.', templateIds: ['t1'], isPublic: false, shares: [] })
      const { wrapper } = await mountAt(`/analyses/${created.id}`)
      await vi.waitFor(() => expect(wrapper.find('h1').exists()).toBe(true))
      expect(figures(wrapper)).toEqual({ Vues: '1', Utilisations: '1', Terminées: '0', 'En cours': '1', 'En erreur': '0' })
      expect(wrapper.get('[data-testid="meta"]').text()).toContain('Pour voir.')
    })

    describe('trying the analysis from a terminal', () => {
  it('has a button that shows the curl commands for this analysis, with the capture as the page is set', async () => {
    useSession().setUser('alice.martin')
    const { wrapper } = await mountAt('/analyses/a1')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="curl-button"]').exists()).toBe(true))

    await wrapper.get('[data-testid="curl-button"]').trigger('click')
    expect(wrapper.get('[data-testid="curl-command"]').text()).toContain('/api/analyses/a1/runs')
    expect(wrapper.get('[data-testid="curl-command"]').text()).toContain('keepScreenshot=true') // the box is checked by default

    await wrapper.get('[data-testid="save-screenshot"]').setValue(false)
    expect(wrapper.get('[data-testid="curl-command"]').text()).toContain('keepScreenshot=false')
  })
})

describe('testing the analysis', () => {
      const send = async (wrapper: ReturnType<typeof mount>, file: File) => {
        const input = wrapper.get('input[type="file"]')
        Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
        await input.trigger('change')
        await flushPromises()
      }
      const detections = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-testid="detection"]')
      /** Sends the document and goes to the elements, where what the analysis found is listed. */
      const sendShow = async (wrapper: ReturnType<typeof mount>, file: File) => {
        await send(wrapper, file)
        await showElements(wrapper)
      }
      const summary = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="test-summary"]').text()
      const models = ['t1', 't6']
      /** A name of file in which the made-up analysis finds at least `atLeast` elements, or none at all (`atLeast` 0). */
      const nameWith = (templateIds: string[], atLeast: number) =>
        Array.from({ length: 300 }, (_, i) => `essai-${i}.png`).find((name) => {
          const n = simulateTest({ templateIds }, { name, size: 1 }).length
          return atLeast === 0 ? n === 0 : n >= atLeast
        })!
      const image = (name: string) => new File(['x'], name, { type: 'image/png' })

      it('starts with the way it works, a place to drop a document, and the choice of keeping a capture', async () => {
        const { wrapper } = await open('a1')
        expect(wrapper.get('h2#tester-title').text()).toBe('Tester l’analyse')
        expect(wrapper.get('[data-testid="dropzone"]').text()).toContain('Déposez un document ici')
        expect(wrapper.get('[data-testid="dropzone"]').text()).toContain('image ou PDF, 20 Mo au plus')
        const steps = wrapper.get('[data-testid="steps"]').text()
        expect(steps).toContain('Logo Marianne, Filigrane « Copie »') // what it looks for
        expect(steps).toContain('Un test est une utilisation')
        expect(steps).toContain('Validez ou invalidez chaque prédiction')
        expect(steps).toContain('visible que par vous, même pour un administrateur')
        expect(wrapper.get('[data-testid="save-screenshot"]').element.checked).toBe(true) // kept unless said otherwise
        expect(wrapper.find('[data-testid="detection"]').exists()).toBe(false)
        expect(wrapper.find('.doc-viewer').exists()).toBe(false)
      })

      describe('page by page', () => {
        const pdfFile = (name: string) => new File(['x'], name, { type: 'application/pdf' })
        /** An analysis of « Formulaire X » (a PDF of three pages, the second named) and of « Logo Marianne », by dana. */
        const pdfAnalysis = async () => {
          useSession().setUser('dana')
          const { create } = useCatalogue()
          const document = await uploadDocument(pdfFile('modele.pdf'))
          const form = await create(
            { name: 'Formulaire X', description: 'Un formulaire', categories: [], entities: [], pages: [{ page: 2, name: 'Pièces', description: '' }] },
            document,
          )
          const analysis = await useAnalyses().createAnalysis({ name: 'Dossiers', description: '', templateIds: [form.id, 't1'], isPublic: false, shares: [] })
          const page = await mountAt(`/analyses/${analysis.id}`)
          await vi.waitFor(() => expect(page.wrapper.find('h1').exists()).toBe(true))
          return { ...page, form }
        }
        const classNames = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-testid="classification"] .classes__name').map((n) => n.text())

        it('classifies each page of a PDF, with the page of the model it looks like, and a pager to go through them', async () => {
          const { wrapper } = await pdfAnalysis()
          await send(wrapper, pdfFile('dossier.pdf'))
          expect(wrapper.get('[data-testid="page-card"] h3').text()).toBe('Classification de la page 1')
          expect(wrapper.get('[data-testid="page-pager"] [data-testid="pager-count"]').text()).toBe('1 / 3')
          expect(classNames(wrapper)).toHaveLength(4) // the likeliest four of five classes
          for (const name of classNames(wrapper)) expect(name).toMatch(/^(Formulaire X · page [13]|Formulaire X · Pièces|Logo Marianne|Autre, non reconnu)$/)

          await wrapper.get('[data-testid="page-pager"] button[title="Page suivante"]').trigger('click')
          expect(wrapper.get('[data-testid="page-card"] h3').text()).toBe('Classification de la page 2')
          expect(wrapper.get('[data-testid="page-number"]').text()).toBe('Page 2 / 3') // the document follows
        })

        it('follows the page of the document: going to a page there shows its classification', async () => {
          const { wrapper } = await pdfAnalysis()
          await send(wrapper, pdfFile('dossier.pdf'))
          await wrapper.get('.doc-viewer button[title="Page suivante"]').trigger('click')
          await wrapper.get('.doc-viewer button[title="Page suivante"]').trigger('click')
          expect(wrapper.get('[data-testid="page-card"] h3').text()).toBe('Classification de la page 3')
          expect(wrapper.get('[data-testid="page-pager"] [data-testid="pager-count"]').text()).toBe('3 / 3')
        })

        it('is decided page by page, and annotated with a page of a model, named as the model names it', async () => {
          const { wrapper, router } = await pdfAnalysis()
          await send(wrapper, pdfFile('dossier.pdf'))
          await wrapper.get('[data-testid="page-pager"] button[title="Page suivante"]').trigger('click')
          const options = wrapper.findAll('[data-testid="page-card"] [data-testid="review-annotate"] option').map((o) => o.text())
          expect(options).toEqual(['Annoter avec…', 'Formulaire X · page 1', 'Formulaire X · Pièces', 'Formulaire X · page 3', 'Logo Marianne'])

          await wrapper.get('[data-testid="page-card"] [data-testid="review-annotate"]').setValue(wrapper.findAll('[data-testid="page-card"] option')[3].element.getAttribute('value'))
          expect(wrapper.get('[data-testid="page-card"] [data-testid="review-state"]').text()).toBe('Annotée : Formulaire X · page 3')

          // Only the page 2 was decided: the other pages are still to be looked at.
          await wrapper.get('[data-testid="page-pager"] button[title="Page précédente"]').trigger('click')
          expect(wrapper.get('[data-testid="page-card"] [data-testid="review-state"]').text()).toBe('À vérifier')
          expect(wrapper.get('[data-testid="progress"]').text()).toMatch(/^1 \/ \d+ vérifiée$/)
          expect(router.currentRoute.value.name).toBe('analysis-detail')
        })

        it('is one classification for an image, with no pager', async () => {
          const { wrapper } = await pdfAnalysis()
          await send(wrapper, image('une-page.png'))
          expect(wrapper.get('[data-testid="page-card"] h3').text()).toBe('Classification de la page')
          expect(wrapper.find('[data-testid="page-pager"]').exists()).toBe(false)
        })
      })

      it('takes an image or a PDF', async () => {
        const { wrapper } = await open('a1')
        expect(wrapper.get('input[type="file"]').attributes('accept')).toBe('image/png,image/jpeg,image/webp,image/gif,application/pdf')
      })

      it('tries the analysis as soon as a document is chosen, which is a use of it', async () => {
        const { wrapper } = await open('a1')
        await sendShow(wrapper, image(nameWith(models, 1)))
        expect(wrapper.find('[data-testid="steps"]').exists()).toBe(false)
        expect(wrapper.find('[data-testid="dropzone"]').exists()).toBe(false)
        expect(detections(wrapper)).toHaveLength(1)
        expect(figures(wrapper)).toMatchObject({ Utilisations: '5', Terminées: '4' }) // 4 and 3 before
        expect(useAnalyses().analyses.value.find((a) => a.id === 'a1')!.runs).toHaveLength(5)
      })

      it('says what the use consumed, on the result and on the list of uses, with the total of the analysis', async () => {
        const { wrapper } = await open('a1')
        await sendShow(wrapper, image(nameWith(models, 1)))
        const own = wrapper.get('[data-testid="run-consumption"]').text().replace(/[\u202f\u00a0]/g, ' ')
        expect(own).toContain('Cette analyse a consommé')
        expect(own).toContain('2,4 Wh')
        expect(own).toContain('0,12 g')
        expect(own).toContain('4,3 mL')
        await showRuns(wrapper)
        expect(wrapper.get('[data-testid="analysis-consumption"]').text()).toContain('2,4 Wh') // the only one measured
        expect(wrapper.get('[data-testid="run-consumption-line"]').text().replace(/[\u202f\u00a0]/g, ' ')).toBe('2,4 Wh · 0,12 g de CO₂')
      })

      it('says nothing of the consumption of a use that was not measured', async () => {
        const { wrapper } = await open('a1')
        await showRuns(wrapper)
        expect(wrapper.find('[data-testid="analysis-consumption"]').exists()).toBe(false)
        expect(wrapper.find('[data-testid="run-consumption-line"]').exists()).toBe(false)
      })

      it('says the analysis is running while the worker computes, then shows the result', async () => {
        vi.useFakeTimers()
        try {
          const { wrapper } = await open('a1')
          await send(wrapper, image('slow.png'))
          expect(wrapper.get('[data-testid="run-running"]').text()).toContain('Analyse en cours')
          expect(figures(wrapper)).toMatchObject({ 'En cours': '1', Terminées: '3' })
          await vi.advanceTimersByTimeAsync(4000)
          await flushPromises()
          expect(wrapper.find('[data-testid="run-running"]').exists()).toBe(false)
          expect(wrapper.find('[data-testid="test-summary"]').exists()).toBe(true)
          expect(figures(wrapper)).toMatchObject({ 'En cours': '0', Terminées: '4' })
        } finally {
          vi.useRealTimers()
        }
      })

      it('cancels a use that is running: it stops, and what the worker would answer is not waited for', async () => {
        vi.useFakeTimers()
        try {
          const { wrapper } = await open('a1')
          await send(wrapper, image('slow.png'))
          expect(figures(wrapper)).toMatchObject({ 'En cours': '1' })
          await wrapper.get('[data-testid="cancel-run"]').trigger('click')
          await flushPromises()
          expect(wrapper.find('[data-testid="run-running"]').exists()).toBe(false)
          expect(wrapper.get('[data-testid="run-cancelled"]').text()).toContain('annulée')
          expect(figures(wrapper)).toMatchObject({ 'En cours': '0' })
          expect(useAnalyses().analyses.value.find((a) => a.id === 'a1')!.runs[0].status).toBe('cancelled')
          // Nothing is asked for any more: the use stays cancelled.
          await vi.advanceTimersByTimeAsync(4000)
          await flushPromises()
          expect(wrapper.find('[data-testid="run-cancelled"]').exists()).toBe(true)
        } finally {
          vi.useRealTimers()
        }
      })

      it('brings the element of a zone up when it is clicked on the document, from any tab', async () => {
        const { wrapper, name } = await open('a1').then(async (page) => {
          const name = nameWith(models, 2)
          await send(page.wrapper, image(name))
          return { ...page, name }
        })
        const found = useAnalyses().find('a1')!.runs[0].detections!
        expect(found.length).toBeGreaterThanOrEqual(2)
        expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toBe('Page')
        const viewer = wrapper.findComponent({ name: 'DocumentViewer' })
        viewer.vm.$emit('select', found[1].id)
        await flushPromises()
        expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toMatch(/^Éléments/)
        expect(wrapper.get('[data-testid="pager-count"]').text()).toBe(`2 / ${found.length}`)
        expect(name).toBeTruthy()
      })

      it('says so when the worker fails, and lets the person try again', async () => {
        vi.useFakeTimers()
        try {
          const { wrapper } = await open('a1')
          await send(wrapper, image('broken.png'))
          await vi.advanceTimersByTimeAsync(4000)
          await flushPromises()
          expect(wrapper.get('[data-testid="run-failed"]').text()).toContain('a échoué')
          expect(figures(wrapper)).toMatchObject({ 'En erreur': '2' })
          await wrapper.get('[data-testid="another"]').trigger('click')
          expect(wrapper.find('[data-testid="dropzone"]').exists()).toBe(true)
        } finally {
          vi.useRealTimers()
        }
      })

      it('shows the document with the elements found outlined on it, each named and with how sure it is', async () => {
        const { wrapper } = await open('a1')
        const name = nameWith(models, 1)
        await send(wrapper, image(name))
        expect(wrapper.get('h2#tester-title').text()).toBe('Document testé')
        expect(wrapper.get('[data-testid="tested-name"]').text()).toBe(name)
        // Kept with the use by the backend, which serves the image of its page.
        expect(wrapper.find('.doc-viewer img').attributes('src')).toMatch(/^\/api\/documents\/[^/]+\/pages\/1$/)
        const found = simulateTest({ templateIds: models }, { name, size: 1 })
        expect(wrapper.findAll('[data-testid="entity-zone"]')).toHaveLength(found.length)
        const labels = wrapper.findAll('[data-testid="entity-label"]').map((l) => l.text())
        expect(labels).toHaveLength(found.length)
        for (const label of labels) expect(label).toMatch(/^Élément \d+ · \d+ %$/)
      })

      it('sums up what was found, and how many predictions have been looked at', async () => {
        const { wrapper } = await open('a1')
        await send(wrapper, image(nameWith(models, 1)))
        expect(summary(wrapper)).toMatch(/^\d+ éléments? · \d modèles? sur 2 · 0 \/ \d+ vérifiée$/)
      })

      it('shows each element in turn, with what it could be and how sure the analysis is of each', async () => {
        const { wrapper } = await open('a1')
        const name = nameWith(models, 2)
        await sendShow(wrapper, image(name))
        const found = simulateTest({ templateIds: models }, { name, size: 1 })
        expect(detections(wrapper)).toHaveLength(1) // one at a time
        expect(wrapper.get('[data-testid="pager-count"]').text()).toBe(`1 / ${found.length}`)
        const rows = wrapper.findAll('[data-testid="classification"]')
        expect(rows).toHaveLength(found[0].classifications.length)
        expect(rows[0].classes()).toContain('classes__row--best')
        const percents = rows.map((r) => Number(r.get('.classes__percent').text().replace(' %', '')))
        expect(percents.reduce((n, p) => n + p, 0)).toBe(100)
        expect([...percents].sort((a, b) => b - a)).toEqual(percents)
        expect(wrapper.get('[data-testid="detection-confidence"]').text()).toBe(`${percents[0]} %`)
        await wrapper.get('button[title="Élément suivant"]').trigger('click')
        expect(wrapper.get('h3').text()).toBe('Élément 2')
      })

      it('outlines in red, on the document, the element being shown', async () => {
        const { wrapper } = await open('a1')
        await sendShow(wrapper, image(nameWith(models, 2)))
        const highlighted = () => wrapper.findAll('[data-testid="entity-zone"]').map((z) => z.classes().includes('doc-viewer__polygon--highlight'))
        expect(highlighted().filter(Boolean)).toHaveLength(1)
        expect(highlighted()[0]).toBe(true)
        await wrapper.get('button[title="Élément suivant"]').trigger('click')
        expect(highlighted()[0]).toBe(false)
        expect(highlighted()[1]).toBe(true)
      })

      it('says so when nothing is found, which is still a use, with the document shown', async () => {
        const { wrapper } = await open('a1')
        await send(wrapper, image(nameWith(models, 0)))
        expect(wrapper.get('[data-testid="nothing-found"]').text()).toBe('Aucun élément trouvé dans ce document.')
        expect(wrapper.find('[data-testid="detection"]').exists()).toBe(false)
        expect(wrapper.findAll('[data-testid="entity-zone"]')).toHaveLength(0)
        expect(wrapper.find('.doc-viewer').exists()).toBe(true)
        expect(figures(wrapper).Utilisations).toBe('5')
      })

      it('refuses a document that is not an image or a PDF, makes no use of it, and keeps the place to drop one', async () => {
        const { wrapper } = await open('a1')
        await send(wrapper, new File(['x'], 'notes.txt', { type: 'text/plain' }))
        expect(wrapper.get('[role="alert"]').text()).toContain('image')
        expect(wrapper.find('[data-testid="dropzone"]').exists()).toBe(true)
        expect(figures(wrapper).Utilisations).toBe('4')
        await send(wrapper, png())
        expect(wrapper.find('[role="alert"]').exists()).toBe(false)
        expect(wrapper.find('[data-testid="dropzone"]').exists()).toBe(false)
      })

      it('takes a document dropped on the place for it', async () => {
        const { wrapper } = await open('a1')
        const file = image(nameWith(models, 1))
        const zone = wrapper.get('[data-testid="dropzone"]')
        await zone.trigger('dragover')
        expect(zone.classes()).toContain('dropzone--over')
        await zone.trigger('dragleave')
        expect(zone.classes()).not.toContain('dropzone--over')
        await zone.trigger('drop', { dataTransfer: { files: [file] } })
        await flushPromises()
        expect(wrapper.get('[data-testid="tested-name"]').text()).toBe(file.name)
        await showElements(wrapper)
        expect(detections(wrapper)).toHaveLength(1)
      })

      it('shows a PDF through the screenshots of its pages, with the elements found', async () => {
        const { wrapper } = await open('a1')
        await sendShow(wrapper, new File(['x'], nameWith(models, 1).replace('.png', '.pdf'), { type: 'application/pdf' }))
        expect(detections(wrapper)).toHaveLength(1)
        expect(wrapper.find('.doc-viewer').exists()).toBe(true)
        expect(wrapper.get('[data-testid="page-number"]').text()).toBe('Page 1 / 3')
      })

      it('answers the same for the same document', async () => {
        const { wrapper } = await open('a1')
        const file = image(nameWith(models, 1))
        await sendShow(wrapper, file)
        const first = wrapper.get('[data-testid="detection"]').text()
        await wrapper.get('[data-testid="another"]').trigger('click')
        await sendShow(wrapper, file)
        expect(wrapper.get('[data-testid="detection"]').text()).toBe(first)
      })

      it('goes back to the place to drop a document with « Nouveau test », and keeps the result among the uses', async () => {
        const { wrapper } = await open('a1')
        await send(wrapper, image(nameWith(models, 1)))
        await wrapper.get('[data-testid="another"]').trigger('click')
        expect(wrapper.find('[data-testid="dropzone"]').exists()).toBe(true)
        expect(wrapper.find('[data-testid="steps"]').exists()).toBe(true)
        expect(wrapper.get('[role="tab"]:not([aria-selected="true"])').text()).toBe('Utilisations (5)')
        expect(wrapper.findAll('[role="tab"]')[1].text()).toBe('Utilisations (5)')
      })

      it('lists every class of an analysis of many models, four at most, saying how many are left', async () => {
        useSession().setUser('admin', { isAdmin: true })
        await loadGroups()
        const ids = ['t1', 't2', 't3', 't4', 't5']
        const many = await useAnalyses().createAnalysis({ name: 'Beaucoup', description: '', templateIds: ids, isPublic: true, shares: [] })
        const { wrapper } = await mountAt(`/analyses/${many.id}`)
        await vi.waitFor(() => expect(wrapper.find('h1').exists()).toBe(true))
        await send(wrapper, image(nameWith(ids, 1)))
        expect(wrapper.findAll('[data-testid="classification"]')).toHaveLength(4)
        expect(wrapper.get('[data-testid="classifications-hidden"]').text()).toBe('+ 2 autres classes encore moins probables')
      })

      it('keeps the result when the tab of the uses is looked at, and comes back to it', async () => {
        const { wrapper } = await open('a1')
        await send(wrapper, image(nameWith(models, 1)))
        await showRuns(wrapper)
        expect(wrapper.find('[data-testid="runs"]').exists()).toBe(true)
        expect(wrapper.find('[data-testid="test-summary"]').exists()).toBe(false)
        await wrapper.findAll('[role="tab"]')[0].trigger('click')
        expect(wrapper.find('[data-testid="test-summary"]').exists()).toBe(true)
        expect(wrapper.find('.doc-viewer').exists()).toBe(true) // and the document never went away
      })

      it('forgets what was shown when another analysis is shown', async () => {
        const { wrapper, router } = await open('a1')
        await send(wrapper, image(nameWith(models, 1)))
        await router.push('/analyses/a4')
        await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Contrats signés'))
        expect(wrapper.find('[data-testid="test-summary"]').exists()).toBe(false)
        expect(wrapper.find('[data-testid="dropzone"]').exists()).toBe(true)
        expect(wrapper.get('[data-testid="steps"]').text()).toContain('Signature type')
      })

      describe('keeping a capture of the document, or not', () => {
        it('keeps one by default, and says so', async () => {
          const { wrapper } = await open('a1')
          await send(wrapper, image(nameWith(models, 1)))
          expect(wrapper.find('.doc-viewer img').exists()).toBe(true)
          expect(wrapper.get('[data-testid="file-state"]').text()).toContain('Capture enregistrée.')
          expect(useAnalyses().analyses.value.find((a) => a.id === 'a1')!.runs[0].screenshot).toMatchObject({ type: 'image/png' })
        })

        it('keeps none when the box is unticked: the elements are listed without the document', async () => {
          const { wrapper } = await open('a1')
          await wrapper.get('[data-testid="save-screenshot"]').setValue(false)
          await send(wrapper, image(nameWith(models, 1)))
          expect(wrapper.find('.doc-viewer').exists()).toBe(false)
          expect(wrapper.get('[data-testid="no-screenshot"]').text()).toContain('Aucune capture n’a été enregistrée pour ce test')
          expect(wrapper.get('[data-testid="file-state"]').text()).toBe('Capture non enregistrée.')
          expect(useAnalyses().analyses.value.find((a) => a.id === 'a1')!.runs[0].screenshot).toBeNull()
          await showElements(wrapper)
          expect(detections(wrapper)).toHaveLength(1) // the predictions can still be looked at
        })

        it('keeps the screenshots of the pages of a PDF too', async () => {
          const { wrapper } = await open('a1')
          await send(wrapper, new File(['x'], nameWith(models, 1).replace('.png', '.pdf'), { type: 'application/pdf' }))
          expect(wrapper.get('[data-testid="file-state"]').text()).toContain('Capture enregistrée.')
        })
      })

      describe('looking at the predictions', () => {
        const trial = async () => {
          const page = await open('a1')
          await send(page.wrapper, image(nameWith(models, 2)))
          await showElements(page.wrapper)
          return page
        }
        const state = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="review-state"]').text()
        const labels = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-testid="entity-label"]').map((l) => l.text())
        const progress = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="progress"]').text()

        it('starts with every prediction still to look at', async () => {
          const { wrapper } = await trial()
          expect(state(wrapper)).toBe('À vérifier')
          expect(progress(wrapper)).toMatch(/^0 \/ \d+ vérifiée$/)
        })

        it('confirms a prediction, which is then said on the document', async () => {
          const { wrapper } = await trial()
          const before = labels(wrapper)[0]
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          expect(state(wrapper)).toBe('Prédiction validée')
          expect(progress(wrapper)).toMatch(/^1 \/ \d+ vérifiée$/)
          expect(labels(wrapper)[0]).toBe(`✓ ${before.replace(/ · \d+ %$/, '')}`)
        })

        it('rejects a prediction, which is then said on the document', async () => {
          const { wrapper } = await trial()
          const before = labels(wrapper)[0]
          await wrapper.get('[data-testid="review-invalidate"]').trigger('click')
          expect(state(wrapper)).toBe('Prédiction invalidée')
          expect(labels(wrapper)[0]).toBe(`✗ ${before.replace(/ · \d+ %$/, '')} (invalidée)`)
        })

        it('annotates a prediction with a model of the analysis, and only with one of them', async () => {
          const { wrapper } = await trial()
          const options = wrapper.findAll('[data-testid="review-annotate"] option').filter((o) => o.attributes('disabled') === undefined)
          expect(options.map((o) => o.text())).toEqual(['Logo Marianne', 'Filigrane « Copie »']) // not « other », nor the others of the catalogue
          await wrapper.get('[data-testid="review-annotate"]').setValue('t6')
          expect(state(wrapper)).toBe('Annotée : Filigrane « Copie »')
          expect(labels(wrapper)[0]).toBe('✎ Élément 1')
        })

        it('takes a decision back, or changes it', async () => {
          const { wrapper } = await trial()
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          await wrapper.get('[data-testid="review-invalidate"]').trigger('click')
          expect(state(wrapper)).toBe('Prédiction invalidée')
          expect(progress(wrapper)).toMatch(/^1 \//)
          await wrapper.get('[data-testid="review-reset"]').trigger('click')
          expect(state(wrapper)).toBe('À vérifier')
          expect(progress(wrapper)).toMatch(/^0 \//)
        })

        it('has a decision for each element of its own', async () => {
          const { wrapper } = await trial()
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          await wrapper.get('button[title="Élément suivant"]').trigger('click')
          expect(state(wrapper)).toBe('À vérifier')
          await wrapper.get('[data-testid="review-invalidate"]').trigger('click')
          await wrapper.get('button[title="Élément précédent"]').trigger('click')
          expect(state(wrapper)).toBe('Prédiction validée')
        })

        it('is kept in the use: it is still there after looking at the other tab', async () => {
          const { wrapper } = await trial()
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          await showRuns(wrapper)
          await wrapper.get('[data-testid="run-open"]').trigger('click') // the use just made, first in the list
          await showElements(wrapper)
          expect(state(wrapper)).toBe('Prédiction validée')
        })
      })

      describe('the classification of the page', () => {
        const trial = async (n = 1) => {
          const page = await open('a1')
          const name = nameWith(models, n)
          await send(page.wrapper, image(name))
          return { ...page, name }
        }
        const state = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="review-state"]').text()
        const progress = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="progress"]').text()
        const tabsOf = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[role="tab"]').map((t) => t.text())

        it('has a tab of its own, which comes first, and one for the elements and one for the uses', async () => {
          const { wrapper, name } = await trial()
          const found = simulateTest({ templateIds: models }, { name, size: 1 }).length
          expect(tabsOf(wrapper)).toEqual(['Page', `Éléments (${found})`, 'Utilisations (5)'])
          expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toBe('Page')
        })

        it('says which model the page corresponds to, how sure the analysis is, and what else it could be', async () => {
          const { wrapper, name } = await trial()
          const expected = simulatePage({ templateIds: models }, { name, size: 1 })
          const card = wrapper.get('[data-testid="page-card"]')
          expect(card.get('h3').text()).toBe('Classification de la page')
          const best = expected[0].templateId === 't1' ? 'Logo Marianne' : 'Filigrane « Copie »'
          expect(card.get('[data-testid="detection-best"]').text()).toBe(best)
          expect(card.get('[data-testid="detection-confidence"]').text()).toBe(`${Math.round(expected[0].confidence * 100)} %`)
          expect(card.findAll('[data-testid="classification"]')).toHaveLength(expected.length)
          const percents = card.findAll('.classes__percent').map((p) => Number(p.text().replace(' %', '')))
          expect(percents.reduce((n, p) => n + p, 0)).toBe(100)
        })

        it('is not one of the elements, and is not drawn on the document', async () => {
          const { wrapper } = await trial()
          expect(wrapper.find('[data-testid="detection"]').exists()).toBe(false) // the card of an element
          expect(wrapper.find('[data-testid="pager-count"]').exists()).toBe(false)
          expect(wrapper.findAll('[data-testid="entity-label"]').length).toBe(simulateTest({ templateIds: models }, { name: nameWith(models, 1), size: 1 }).length)
        })

        it('is still to be looked at, and counted with the elements', async () => {
          const { wrapper, name } = await trial()
          const found = simulateTest({ templateIds: models }, { name, size: 1 }).length
          expect(state(wrapper)).toBe('À vérifier')
          expect(progress(wrapper)).toBe(`0 / ${found + 1} vérifiée`)
        })

        it('is confirmed with a button', async () => {
          const { wrapper } = await trial()
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          expect(state(wrapper)).toBe('Prédiction validée')
          expect(progress(wrapper)).toMatch(/^1 \/ \d+ vérifiée$/)
        })

        it('is rejected with a button', async () => {
          const { wrapper } = await trial()
          await wrapper.get('[data-testid="review-invalidate"]').trigger('click')
          expect(state(wrapper)).toBe('Prédiction invalidée')
        })

        it('is annotated with a model of the analysis, and with no other', async () => {
          const { wrapper } = await trial()
          const options = wrapper.findAll('[data-testid="review-annotate"] option').filter((o) => o.attributes('disabled') === undefined)
          expect(options.map((o) => o.text())).toEqual(['Logo Marianne', 'Filigrane « Copie »'])
          await wrapper.get('[data-testid="review-annotate"]').setValue('t6')
          expect(state(wrapper)).toBe('Annotée : Filigrane « Copie »')
        })

        it('has a decision taken back, or changed', async () => {
          const { wrapper } = await trial()
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          await wrapper.get('[data-testid="review-invalidate"]').trigger('click')
          expect(state(wrapper)).toBe('Prédiction invalidée')
          await wrapper.get('[data-testid="review-reset"]').trigger('click')
          expect(state(wrapper)).toBe('À vérifier')
        })

        it('keeps its decision when the other tabs are looked at', async () => {
          const { wrapper } = await trial()
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          await showElements(wrapper)
          await showRuns(wrapper)
          await showPage(wrapper)
          expect(state(wrapper)).toBe('Prédiction validée')
        })

        it('is its own decision, apart from the elements\'', async () => {
          const { wrapper } = await trial(2)
          await wrapper.get('[data-testid="review-validate"]').trigger('click') // the page
          await showElements(wrapper)
          expect(state(wrapper)).toBe('À vérifier') // the first element is another matter
        })

        it('is looked at from the list of the uses too', async () => {
          const { wrapper } = await open('a1')
          await showRuns(wrapper)
          await wrapper.findAll('[data-testid="run-open"]')[0].trigger('click') // the demo use
          expect(wrapper.get('[data-testid="page-card"]').exists()).toBe(true)
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          expect(state(wrapper)).toBe('Prédiction validée')
        })

        it('is what the question about the file waits for, as much as the elements', async () => {
          const { wrapper } = await trial(1)
          await showElements(wrapper)
          const total = Number(wrapper.get('[data-testid="pager-count"]').text().split(' / ')[1])
          for (let i = 0; i < total; i++) {
            await wrapper.get('[data-testid="review-validate"]').trigger('click')
            if (i < total - 1) await wrapper.get('button[title="Élément suivant"]').trigger('click')
          }
          expect(wrapper.find('[data-testid="file-question"]').exists()).toBe(false) // the page is not looked at yet
          await showPage(wrapper)
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          expect(wrapper.find('[data-testid="file-question"]').exists()).toBe(true)
        })
      })

      describe('adding an element by hand', () => {
        const trial = async (options: { capture?: boolean; file?: File } = {}) => {
          const page = await open('a1')
          if (options.capture === false) await page.wrapper.get('[data-testid="save-screenshot"]').setValue(false)
          await send(page.wrapper, options.file ?? image(nameWith(models, 1)))
          await showElements(page.wrapper)
          return page
        }
        const add = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="add-element"]')
        const elementsTab = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[role="tab"]')[1].text()
        const count = (wrapper: ReturnType<typeof mount>) => Number(elementsTab(wrapper).match(/\((\d+)\)/)![1])
        const zones = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-testid="entity-zone"]')
        /** Draws a triangle on the document, closed with Enter. */
        const draw = async (wrapper: ReturnType<typeof mount>) => {
          await click(wrapper, [20, 10])
          await click(wrapper, [120, 10])
          await click(wrapper, [120, 60])
          key('Enter')
          await flushPromises()
        }

        it('is offered with the elements, and not with the page', async () => {
          const { wrapper } = await trial()
          expect(add(wrapper).text()).toBe('Ajouter un élément')
          expect(add(wrapper).attributes('disabled')).toBeUndefined()
          await showPage(wrapper)
          expect(wrapper.find('[data-testid="add-element"]').exists()).toBe(false)
        })

        it('needs the capture of the document, to draw on', async () => {
          const { wrapper } = await trial({ capture: false })
          expect(add(wrapper).attributes('disabled')).toBeDefined()
          expect(add(wrapper).attributes('title')).toContain('Il faut une capture du document')
          expect(wrapper.get('[data-testid="cannot-draw"]').text()).toContain('gardez une capture du document')
        })

        it('cannot be done once the file is deleted', async () => {
          const { wrapper } = await trial()
          await wrapper.get('[data-testid="file-state"] [data-testid="file-delete"]').trigger('click')
          expect(add(wrapper).attributes('disabled')).toBeDefined()
        })

        it('asks which model it is, among those of the analysis only, and for a zone on the document', async () => {
          const { wrapper } = await trial()
          await add(wrapper).trigger('click')
          const panel = wrapper.get('[data-testid="adding"]')
          expect(panel.findAll('#new-element-model option').map((o) => o.text())).toEqual(['Logo Marianne', 'Filigrane « Copie »'])
          expect(panel.get('[data-testid="adding-hint"]').text()).toContain('Dessinez la zone sur le document')
          expect(wrapper.find('[data-testid="add-element"]').exists()).toBe(false) // the button gives way to the panel
          expect(wrapper.find('[data-testid="zoom-level"]').exists()).toBe(true)
          expect(wrapper.findAll('.doc-viewer button').map((b) => b.text())).toEqual(expect.arrayContaining(['Polygone', 'Rectangle'])) // the tools
        })

        it('is given up with Cancel, or Escape', async () => {
          const { wrapper } = await trial()
          await add(wrapper).trigger('click')
          await wrapper.get('[data-testid="add-cancel"]').trigger('click')
          expect(wrapper.find('[data-testid="adding"]').exists()).toBe(false)
          expect(wrapper.findAll('.doc-viewer button').map((b) => b.text())).not.toContain('Polygone')
          await add(wrapper).trigger('click')
          key('Escape')
          await flushPromises()
          expect(wrapper.find('[data-testid="adding"]').exists()).toBe(false)
        })

        it('adds an element when a polygon is drawn, annotated with the model chosen', async () => {
          const { wrapper } = await trial()
          const rect = stubStage()
          const before = count(wrapper)
          await add(wrapper).trigger('click')
          await draw(wrapper)
          expect(count(wrapper)).toBe(before + 1)
          expect(wrapper.find('[data-testid="adding"]').exists()).toBe(false)
          expect(wrapper.find('[data-testid="manual-element"]').exists()).toBe(true) // and it is the one shown
          expect(wrapper.get('[data-testid="manual-element"]').text()).toContain('Ajouté à la main')
          expect(wrapper.get('[data-testid="manual-model"]').text()).toBe('Logo Marianne')
          expect(zones(wrapper).at(-1)!.attributes('points')).toBe('10,10 60,10 60,60')
          expect(wrapper.findAll('[data-testid="entity-label"]').at(-1)!.text()).toBe('✎ Élément 4')
          rect.mockRestore()
        })

        it('asks which entity of the model it is, if the person knows, and keeps it', async () => {
          const { wrapper } = await trial()
          const rect = stubStage()
          await add(wrapper).trigger('click')
          const options = wrapper.findAll('[data-testid="new-element-entity"] option').map((o) => o.text())
          expect(options[0]).toBe('Je ne sais pas')
          expect(options.length).toBeGreaterThan(1)
          const entity = useCatalogue().find('t1')!.entities[0]
          await wrapper.get('[data-testid="new-element-entity"]').setValue(entity.id)
          await draw(wrapper)
          const detection = useAnalyses().findRun('a1', useAnalyses().find('a1')!.runs[0].id)!.detections!.at(-1)!
          expect(detection.entityId).toBe(entity.id)
          rect.mockRestore()
        })

        it('annotates with the model picked in the list', async () => {
          const { wrapper } = await trial()
          const rect = stubStage()
          await add(wrapper).trigger('click')
          await wrapper.get('[data-testid="new-element-model"]').setValue('t6')
          await draw(wrapper)
          expect(wrapper.get('[data-testid="manual-model"]').text()).toBe('Filigrane « Copie »')
          expect(wrapper.findAll('[data-testid="entity-label"]').at(-1)!.text()).toBe('✎ Élément 4')
          rect.mockRestore()
        })

        it('takes a rectangle as well as a polygon', async () => {
          const { wrapper } = await trial()
          const rect = stubStage()
          await add(wrapper).trigger('click')
          await wrapper.findAll('.doc-viewer button').find((b) => b.text() === 'Rectangle')!.trigger('click')
          await drag(wrapper, [20, 10], [120, 60])
          expect(zones(wrapper).at(-1)!.attributes('points')).toBe('10,10 60,10 60,60 10,60')
          rect.mockRestore()
        })

        it('counts as looked at, as a decision already taken', async () => {
          const { wrapper } = await trial()
          const rect = stubStage()
          const before = wrapper.get('[data-testid="progress"]').text().match(/^(\d+) \/ (\d+)/)!
          await add(wrapper).trigger('click')
          await draw(wrapper)
          const after = wrapper.get('[data-testid="progress"]').text().match(/^(\d+) \/ (\d+)/)!
          expect([Number(after[1]), Number(after[2])]).toEqual([Number(before[1]) + 1, Number(before[2]) + 1])
          rect.mockRestore()
        })

        it('has neither prediction to look at nor confidence: it is the person\'s own annotation', async () => {
          const { wrapper } = await trial()
          const rect = stubStage()
          await add(wrapper).trigger('click')
          await draw(wrapper)
          expect(wrapper.find('[data-testid="review"]').exists()).toBe(false)
          expect(wrapper.find('[data-testid="detection-confidence"]').exists()).toBe(false)
          rect.mockRestore()
        })

        it('is taken away with its button, and nothing else is', async () => {
          const { wrapper } = await trial()
          const rect = stubStage()
          const before = count(wrapper)
          await add(wrapper).trigger('click')
          await draw(wrapper)
          await wrapper.get('[data-testid="manual-remove"]').trigger('click')
          expect(count(wrapper)).toBe(before)
          expect(wrapper.find('[data-testid="manual-element"]').exists()).toBe(false)
          expect(wrapper.find('[data-testid="detection"]').exists()).toBe(true) // what the analysis found is still there
          expect(wrapper.find('[data-testid="manual-remove"]').exists()).toBe(false) // and cannot be taken away
          rect.mockRestore()
        })

        it('can be added when nothing was found, which then is not « nothing » any more', async () => {
          const { wrapper } = await trial({ file: image(nameWith(models, 0)) })
          const rect = stubStage()
          expect(wrapper.get('[data-testid="nothing-found"]').exists()).toBe(true)
          await add(wrapper).trigger('click')
          await draw(wrapper)
          expect(wrapper.find('[data-testid="nothing-found"]').exists()).toBe(false)
          expect(count(wrapper)).toBe(1)
          expect(wrapper.get('[data-testid="test-summary"]').text()).toMatch(/^1 élément · 1 modèle sur 2/)
          rect.mockRestore()
        })

        it('stays with the use: it is there again when the use is opened from the list', async () => {
          const { wrapper } = await trial()
          const rect = stubStage()
          const before = count(wrapper)
          await add(wrapper).trigger('click')
          await draw(wrapper)
          await showRuns(wrapper)
          await wrapper.get('[data-testid="run-open"]').trigger('click') // the use just made, first in the list
          expect(count(wrapper)).toBe(before + 1)
          rect.mockRestore()
        })

        it('is for one\'s own results only: the administrator cannot add to someone else\'s', async () => {
          const { wrapper } = await open('a5', 'admin')
          await showRuns(wrapper)
          expect(wrapper.findAll('[data-testid="run-open"]')).toHaveLength(0) // none of alice\'s or dana\'s is theirs to open
          expect(wrapper.find('[data-testid="add-element"]').exists()).toBe(false)
        })
      })

      describe('the document, once the predictions are looked at', () => {
        const trial = async (saveScreenshot = true) => {
          const page = await open('a1')
          if (!saveScreenshot) await page.wrapper.get('[data-testid="save-screenshot"]').setValue(false)
          await send(page.wrapper, image(nameWith(models, 2)))
          return page
        }
        const validateAll = async (wrapper: ReturnType<typeof mount>) => {
          await wrapper.get('[data-testid="review-validate"]').trigger('click') // the page, which is also looked at
          await showElements(wrapper)
          const total = Number(wrapper.get('[data-testid="pager-count"]').text().split(' / ')[1])
          for (let i = 0; i < total; i++) {
            await wrapper.get('[data-testid="review-validate"]').trigger('click')
            if (i < total - 1) await wrapper.get('button[title="Élément suivant"]').trigger('click')
          }
        }

        it('is not asked about while some predictions are still to look at, but can be deleted at any time', async () => {
          const { wrapper } = await trial()
          expect(wrapper.find('[data-testid="file-question"]').exists()).toBe(false)
          expect(wrapper.get('[data-testid="file-state"] [data-testid="file-delete"]').text()).toBe('Supprimer le fichier')
        })

        it('asks what to do with it once everything is looked at', async () => {
          const { wrapper } = await trial()
          await validateAll(wrapper)
          const question = wrapper.get('[data-testid="file-question"]')
          expect(question.text()).toContain('Toutes les prédictions sont vérifiées.')
          expect(question.text()).toContain('Supprimer le fichier de test ?')
          expect(question.get('[data-testid="file-delete"]').text()).toBe('Supprimer le fichier')
          expect(question.get('[data-testid="file-keep"]').text()).toBe('Le conserver')
        })

        it('deletes the file when told to, keeping the results and the decisions', async () => {
          const { wrapper } = await trial()
          await validateAll(wrapper)
          await wrapper.get('[data-testid="file-question"] [data-testid="file-delete"]').trigger('click')
          expect(wrapper.find('[data-testid="file-question"]').exists()).toBe(false)
          expect(wrapper.find('.doc-viewer').exists()).toBe(false)
          expect(wrapper.get('[data-testid="no-screenshot"]').text()).toContain('La capture de ce document a été supprimée')
          expect(wrapper.get('[data-testid="file-state"]').text()).toBe('Fichier supprimé.')
          expect(wrapper.get('[data-testid="review-state"]').text()).toBe('Prédiction validée') // the decisions stay
          await showElements(wrapper)
          expect(detections(wrapper)).toHaveLength(1)
        })

        it('keeps the file when told to, and stops asking', async () => {
          const { wrapper } = await trial()
          await validateAll(wrapper)
          await wrapper.get('[data-testid="file-keep"]').trigger('click')
          expect(wrapper.find('[data-testid="file-question"]').exists()).toBe(false)
          expect(wrapper.find('.doc-viewer').exists()).toBe(true)
          expect(wrapper.get('[data-testid="file-state"]').text()).toContain('Capture enregistrée (conservée).')
          await showElements(wrapper)
          await wrapper.get('[data-testid="review-reset"]').trigger('click') // changing one's mind does not bring the question back
          await wrapper.get('[data-testid="review-validate"]').trigger('click')
          expect(wrapper.find('[data-testid="file-question"]').exists()).toBe(false)
        })

        it('deletes the file before everything is looked at, with the small button', async () => {
          const { wrapper } = await trial()
          await wrapper.get('[data-testid="file-state"] [data-testid="file-delete"]').trigger('click')
          expect(wrapper.find('.doc-viewer').exists()).toBe(false)
          expect(wrapper.get('[data-testid="file-state"]').text()).toBe('Fichier supprimé.')
        })

        it('does not ask when no capture was kept: there is nothing to delete', async () => {
          const { wrapper } = await trial(false)
          await validateAll(wrapper)
          expect(wrapper.find('[data-testid="file-question"]').exists()).toBe(false)
          expect(wrapper.get('[data-testid="file-state"]').text()).toBe('Capture non enregistrée.')
        })

        it('does not ask for a use that found nothing: there is nothing to look at', async () => {
          const { wrapper } = await open('a1')
          await send(wrapper, image(nameWith(models, 0)))
          expect(wrapper.find('[data-testid="file-question"]').exists()).toBe(false)
          expect(wrapper.get('[data-testid="file-state"] [data-testid="file-delete"]').exists()).toBe(true)
        })
      })
    })

    describe('the result of a use is private to the person who ran it', () => {
      const send = async (wrapper: ReturnType<typeof mount>, file: File) => {
        const input = wrapper.get('input[type="file"]')
        Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
        await input.trigger('change')
        await flushPromises()
      }
      const rows = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-testid="run"]')

      it('can be opened from the list of the uses, with its document and what was decided', async () => {
        const { wrapper } = await open('a1') // alice.martin ran r1, which has a result and a capture
        await showRuns(wrapper)
        expect(rows(wrapper)[0].get('[data-testid="run-open"]').exists()).toBe(true)
        await rows(wrapper)[0].get('[data-testid="run-open"]').trigger('click')
        expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toBe('Page')
        expect(wrapper.get('[data-testid="tested-name"]').text()).toBe('courrier-octobre-1.svg')
        expect(wrapper.find('.doc-viewer img').attributes('src')).toBe('/api/documents/seed-shot/pages/1')
        await showElements(wrapper)
        expect(wrapper.get('[data-testid="review-state"]').text()).toBe('Prédiction validée') // the demo's first element
      })

      it('has no button for a use that stored no result', async () => {
        const { wrapper } = await open('a1')
        await showRuns(wrapper)
        const third = rows(wrapper)[2] // r3: a use without a stored result
        expect(third.find('[data-testid="run-open"]').exists()).toBe(false)
        expect(third.find('[data-testid="run-private"]').exists()).toBe(false)
      })

      it('shows a use without a capture by listing its elements, without the document', async () => {
        const { wrapper } = await open('a1')
        await showRuns(wrapper)
        await rows(wrapper)[1].get('[data-testid="run-open"]').trigger('click') // r2: a result, no capture
        expect(wrapper.find('.doc-viewer').exists()).toBe(false)
        expect(wrapper.get('[data-testid="no-screenshot"]').exists()).toBe(true)
        await showElements(wrapper)
        expect(wrapper.find('[data-testid="detection"]').exists()).toBe(true)
      })

      it('is not offered for someone else\'s use, even to an administrator who can open the analysis', async () => {
        const { wrapper } = await open('a5', 'admin') // r12 is alice.martin\'s and r13 dana\'s
        await showRuns(wrapper)
        const withResult = rows(wrapper).filter((r) => r.find('[data-testid="run-private"], [data-testid="run-open"]').exists())
        expect(withResult).toHaveLength(2)
        for (const r of withResult) {
          expect(r.find('[data-testid="run-open"]').exists()).toBe(false)
          expect(r.get('[data-testid="run-private"]').text()).toBe('Résultat privé')
        }
      })

      it('shows the administrator the figures of every use, but the result of none but their own', async () => {
        const { wrapper } = await open('a5', 'admin')
        expect(figures(wrapper).Utilisations).toBe('5') // all of them are counted
        await showRuns(wrapper)
        expect(rows(wrapper)).toHaveLength(4)
        await wrapper.findAll('[role="tab"]')[0].trigger('click')
        await send(wrapper, png())
        await showRuns(wrapper)
        const mine = rows(wrapper)[0]
        expect(mine.text()).toContain('admin')
        expect(mine.get('[data-testid="run-open"]').exists()).toBe(true) // theirs
        expect(wrapper.findAll('[data-testid="run-open"]')).toHaveLength(1)
      })

      it('is shared by no one: each person opens only theirs on the same public analysis', async () => {
        const dana = await open('a5', 'dana')
        await showRuns(dana.wrapper)
        const danaRows = rows(dana.wrapper).filter((r) => r.find('[data-testid="run-open"], [data-testid="run-private"]').exists())
        expect(danaRows.filter((r) => r.find('[data-testid="run-open"]').exists()).map((r) => r.text())).toEqual([expect.stringContaining('dana')])
        expect(danaRows.filter((r) => r.find('[data-testid="run-private"]').exists()).map((r) => r.text())).toEqual([expect.stringContaining('alice.martin')])
        const alice = await open('a5', 'alice.martin')
        await showRuns(alice.wrapper)
        const aliceRows = rows(alice.wrapper).filter((r) => r.find('[data-testid="run-open"], [data-testid="run-private"]').exists())
        expect(aliceRows.filter((r) => r.find('[data-testid="run-open"]').exists()).map((r) => r.text())).toEqual([expect.stringContaining('alice.martin')])
      })

      it('does not show someone else\'s result even when asked for its identifier', async () => {
        const { wrapper } = await open('a5', 'admin')
        const { analyses } = useAnalyses()
        // The backend does not send it, and nothing in the page selects the use: its result is nowhere to be seen.
        expect(analyses.value.find((a) => a.id === 'a5')!.runs.find((r) => r.id === 'r12')!.detections).toBeUndefined()
        await showRuns(wrapper)
        expect(wrapper.findAll('[data-testid="run-open"]')).toHaveLength(0)
        expect(wrapper.find('[data-testid="detection"]').exists()).toBe(false)
      })
    })
  })

  describe('the evaluation', () => {
    /** alice.martin tries the analysis on a document in which t1 is found, and validates what was found. */
    async function decide() {
      useSession().setUser('alice.martin')
      const name = Array.from({ length: 300 }, (_, i) => `essai-${i}.png`).find((n) =>
        simulateTest({ templateIds: ['t1', 't6'] }, { name: n, size: 1 }).some((d) => d.classifications[0].templateId === 't1'),
      )!
      const { startRun, reviewDetection, findRun } = useAnalyses()
      const run = (await startRun('a1', new File(['x'], name, { type: 'image/png' }), { saveScreenshot: false }))!
      for (const d of findRun('a1', run.id)!.detections!) await reviewDetection('a1', run.id, d.id, { status: 'validated' })
    }
    const correct = (wrapper: ReturnType<typeof mount>) =>
      Number(wrapper.get('[data-testid="quality-elements"] [data-testid="counts"]').text().match(/^(\d+) juste/)![1])

    it('says what the person decided of their own tests, over every model and model by model', async () => {
      await decide()
      const { wrapper } = await mountAt('/evaluation')
      await flushPromises()
      expect(wrapper.get('h1').text()).toBe('Évaluation')
      expect(wrapper.find('[role="tab"]').exists()).toBe(false) // only theirs: nothing to choose
      expect(correct(wrapper)).toBeGreaterThan(0)
      expect(wrapper.get('[data-testid="quality-pages"] h3').text()).toBe('Classification des pages')
      const lines = wrapper.findAll('[data-testid="quality-model"]')
      expect(lines.length).toBeGreaterThan(0)
      expect(lines[0].get('a').attributes('href')).toMatch(/^\/catalogue\//)
    })

    it('starts empty for someone who decided nothing', async () => {
      useSession().setUser('nouveau.venu')
      const { wrapper } = await mountAt('/evaluation')
      await flushPromises()
      expect(wrapper.get('[data-testid="quality-empty"]').text()).toContain('Vous n’avez encore')
      expect(wrapper.find('[data-testid="quality-models"]').exists()).toBe(false)
    })

    it('gives the administrator everyone’s decisions as well, with how many people took part', async () => {
      await decide()
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/evaluation')
      await flushPromises()
      expect(wrapper.findAll('[role="tab"]').map((t) => t.text())).toEqual(['Mes décisions', 'Tous les utilisateurs'])
      expect(wrapper.get('[data-testid="quality-empty"]').text()).toContain('Vous n’avez encore') // the admin decided nothing
      await wrapper.findAll('[role="tab"]')[1].trigger('click')
      await flushPromises()
      expect(wrapper.get('[data-testid="reviewers"]').text()).toMatch(/\d+ personne/)
      expect(correct(wrapper)).toBeGreaterThan(0)
    })

    it('says when the figures cannot be loaded', async () => {
      useSession().setUser('dana')
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
      const { wrapper } = await mountAt('/evaluation')
      await flushPromises()
      expect(wrapper.get('[role="alert"]').text()).toContain('n’ont pas pu être chargés')
    })
  })

  describe('my consumption, from my profile', () => {
    const rows = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-testid="consumption-row"]')

    it('is a link of the settings page', async () => {
      useSession().setUser('alice.martin')
      const { wrapper, router } = await mountAt('/parametres')
      await wrapper.get('[data-testid="my-consumption-link"]').trigger('click')
      await landsOn(router, 'my-consumption')
    })

    it('tells what the uses of the person consumed, in all and by analysis', async () => {
      useSession().setUser('alice.martin')
      const { wrapper } = await mountAt('/parametres/consommation')
      await vi.waitFor(() => expect(wrapper.find('[data-testid="consumption-by-analysis"]').exists()).toBe(true))

      const mine = analyses.value.flatMap((a) => backendAnalysis(a.id).runs).filter((r) => r.userId === 'alice.martin' && r.fileName)
      expect(wrapper.get('[data-testid="consumption-uses"]').text()).toContain(`${mine.length} utilisations`)
      expect(rows(wrapper).length).toBeGreaterThan(0)
      // Each analysis links to its page.
      expect(wrapper.get('[data-testid="consumption-analysis"]').attributes('href')).toMatch(/^\/analyses\//)
    })

    it('counts a use that was measured, and lists one that was not for nothing', async () => {
      useSession().setUser('alice.martin')
      const run = backendAnalysis('a1').runs.find((r) => r.userId === 'alice.martin' && r.fileName)!
      run.consumption = { durationS: 5, energyWh: 7, co2G: 0.4, waterMl: 12.6 }
      const { wrapper } = await mountAt('/parametres/consommation')
      await vi.waitFor(() => expect(rows(wrapper).length).toBeGreaterThan(0))

      expect(wrapper.get('[data-testid="my-consumption-total"]').text()).toContain('Toutes mes utilisations')
      expect(wrapper.get('[data-testid="consumption-row-energy"]').text()).toMatch(/Wh/)
    })

    it('has nothing to say to someone who tested nothing', async () => {
      useSession().setUser('someone.new')
      const { wrapper } = await mountAt('/parametres/consommation')
      await vi.waitFor(() => expect(wrapper.find('[data-testid="consumption-none"]').exists()).toBe(true))
      expect(wrapper.find('[data-testid="consumption-by-analysis"]').exists()).toBe(false)
    })

    it('says so when it cannot be loaded', async () => {
      useSession().setUser('alice.martin')
      vi.stubGlobal('fetch', () => Promise.resolve(new Response('{}', { status: 500 })))
      const { wrapper } = await mountAt('/parametres/consommation')
      await vi.waitFor(() => expect(wrapper.find('[data-testid="consumption-failed"]').exists()).toBe(true))
    })
  })

  describe('the overview of the administrator', () => {
    const values = (wrapper: ReturnType<typeof mount>) =>
      Object.fromEntries(wrapper.findAll('[data-testid="stat"]').map((s) => [s.get('[data-testid="stat-label"]').text(), s.get('[data-testid="stat-value"]').text()]))

    it('is in the sidebar for the administrator only', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const admin = await mountAt('/catalogue')
      expect(admin.wrapper.findAll('.app-sidebar__link').map((l) => l.text())).toEqual(['Catalogue', 'Analyses', 'Recherche', 'Évaluation', 'Vue d’ensemble', 'Services'])
      useSession().setUser('dana')
      const other = await mountAt('/catalogue')
      expect(other.wrapper.findAll('.app-sidebar__link').map((l) => l.text())).toEqual(['Catalogue', 'Analyses', 'Recherche', 'Évaluation'])
    })

    it('is out of reach of anyone else, who is sent to the analyses', async () => {
      useSession().setUser('dana')
      const { router } = await mountAt('/vue-d-ensemble')
      expect(router.currentRoute.value.name).toBe('analyses')
    })

    it('shows the figures of every analysis', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/vue-d-ensemble')
      expect(wrapper.get('h1').text()).toBe('Vue d’ensemble')
      expect(values(wrapper)).toEqual({ Analyses: '8', Vues: '251', Utilisations: '20', Terminées: '12', 'En cours': '3', 'En erreur': '5' })
      expect(wrapper.get('[data-testid="visibility"]').text()).toBe('1 publique · 4 partagées · 3 privées')
    })

    it('says what the uses consumed all together, when some were measured', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const none = await mountAt('/vue-d-ensemble')
      expect(none.wrapper.find('[data-testid="overview-consumption"]').exists()).toBe(false)
      backendAnalysis('a1')!.runs[0].consumption = { durationS: 5, energyWh: 1500, co2G: 120, waterMl: 2700 }
      backendAnalysis('a5')!.runs[0].consumption = { durationS: 5, energyWh: 500, co2G: 80, waterMl: 900 }
      resetAnalyses()
      const { wrapper } = await mountAt('/vue-d-ensemble')
      const text = wrapper.get('[data-testid="overview-consumption"]').text().replace(/[\u202f\u00a0]/g, ' ')
      expect(text).toContain('2 kWh') // 2 000 Wh
      expect(text).toContain('200 g')
      expect(text).toContain('3,6 L')
      expect(text).toContain('8,3 ampoules LED allumées 1 jour') // 2 000 Wh
      expect(text).toContain('3,6 bouteilles d’1 L') // 3,6 L
    })

    it('has the catalogue indexed again, and says how much was sent', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/vue-d-ensemble')
      expect(wrapper.find('[data-testid="reindex-done"]').exists()).toBe(false)
      await wrapper.get('[data-testid="reindex"]').trigger('click')
      await vi.waitFor(() => expect(wrapper.find('[data-testid="reindex-done"]').exists()).toBe(true))
      expect(reindexCount()).toBe(1)
      expect(wrapper.get('[data-testid="reindex-done"]').text()).toMatch(/^Indexation demandée pour \d+ modèles?\.$/)
    })

    it('tells why the indexing could not be asked for', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/vue-d-ensemble')
      vi.stubGlobal('fetch', () => Promise.resolve(new Response('{"detail":"Le broker est injoignable."}', { status: 503 })))
      await wrapper.get('[data-testid="reindex"]').trigger('click')
      await vi.waitFor(() => expect(wrapper.find('[data-testid="reindex-fault"]').exists()).toBe(true))
      expect(wrapper.find('[data-testid="reindex-done"]').exists()).toBe(false)
    })

    it('deletes the old indexes only after a confirmation', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/vue-d-ensemble')
      await wrapper.get('[data-testid="drop-old"]').trigger('click')
      expect(wrapper.get('[data-testid="drop-old-warning"]').text()).toContain('pour de bon')
      await wrapper.get('[data-testid="drop-old-cancel"]').trigger('click')
      expect(droppedOldCount()).toBe(0)
      await wrapper.get('[data-testid="drop-old"]').trigger('click')
      await wrapper.get('[data-testid="drop-old-confirm"]').trigger('click')
      await vi.waitFor(() => expect(wrapper.find('[data-testid="drop-old-done"]').exists()).toBe(true))
      expect(droppedOldCount()).toBe(1)
    })

    it('spreads the uses over their three states', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/vue-d-ensemble')
      expect(wrapper.get('.bar').attributes('aria-label')).toBe('Terminées : 12, En cours : 3, En erreur : 5')
      const widths = wrapper.findAll('.bar__part').map((p) => p.attributes('style'))
      expect(widths).toEqual(['width: 60%;', 'width: 15%;', 'width: 25%;'])
    })

    it('lists the most used analyses, each a link to its dashboard', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/vue-d-ensemble')
      const rows = wrapper.findAll('[data-testid="most-used"]')
      expect(rows).toHaveLength(5)
      expect(rows[0].get('a').text()).toBe('Attestations CAF')
      expect(rows[0].get('a').attributes('href')).toBe('/analyses/a5')
      expect(rows[0].text()).toContain('5 utilisations · 120 vues')
      expect(rows[1].get('a').text()).toBe('Courriers octobre') // 4 uses
    })

    it('lists what needs a look: the failures first, then what is still running', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/vue-d-ensemble')
      const rows = wrapper.findAll('[data-testid="to-watch"]')
      expect(rows.map((r) => r.get('a').text())).toEqual(['Formulaires CERFA', 'Demandes refusées', 'Contrats paraphés', 'Accusés de réception T3'])
      expect(rows[0].text()).toContain('En échec')
      expect(rows[2].text()).toContain('En cours')
    })

    it('says so when nothing is wrong', async () => {
      useSession().setUser('admin', { isAdmin: true })
      const { wrapper } = await mountAt('/vue-d-ensemble')
      for (const a of useAnalyses().analyses.value) a.status = 'done'
      await flushPromises()
      expect(wrapper.text()).toContain('Rien à signaler')
    })

    it('does not count its own visit as a view of any analysis', async () => {
      useSession().setUser('admin', { isAdmin: true })
      await mountAt('/vue-d-ensemble')
      expect(useAnalyses().analyses.value.reduce((n, a) => n + a.views, 0)).toBe(251)
    })

    it('counts the analyses made meanwhile', async () => {
      useSession().setUser('admin', { isAdmin: true })
      useAnalyses().createAnalysis({ name: 'Neuve', description: '', templateIds: ['t1'], isPublic: false, shares: [] })
      const { wrapper } = await mountAt('/vue-d-ensemble')
      expect(values(wrapper)).toMatchObject({ Analyses: '9', Utilisations: '21', 'En cours': '4' })
    })
  })

  it('tells the owner how many suggestions wait on the catalogue', async () => {
    useSession().setUser('alice.martin')
    const { wrapper } = await mountAt('/catalogue')
    expect(wrapper.text()).toContain('1 suggestion')
    expect(wrapper.text()).toContain('Par alice.martin')
  })

  it('shows a message for an unknown template', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/nope')
    expect(wrapper.text()).toContain('Ce modèle n’existe pas.')
  })

  const upload = async (wrapper: ReturnType<typeof mount>, file: File) => {
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises() // the document is sent to the backend
  }
  const png = () => new File(['x'], 'scan.png', { type: 'image/png' })
  const button = (wrapper: ReturnType<typeof mount>, text: string) =>
    wrapper.findAll('button').find((b) => b.text() === text)!
  const byTitle = (wrapper: ReturnType<typeof mount>, title: string) => wrapper.get(`button[title="${title}"]`)
  // The nth field (input or textarea) whose label starts with `label`.
  const field = (wrapper: ReturnType<typeof mount>, label: string, n = 0) => {
    const target = wrapper.findAll('label').filter((l) => l.text().startsWith(label))[n]
    return wrapper.get(`#${target.attributes('for')}`)
  }
  const entityCount = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="pager-count"]').text()
  const addEntity = async (wrapper: ReturnType<typeof mount>, name = '', definition = '') => {
    await wrapper.get('.entities .fr-btn--icon-left').trigger('click') // « Ajouter », not the one of the categories
    if (name) await field(wrapper, 'Nom', 1).setValue(name)
    if (definition) await field(wrapper, 'Définition').setValue(definition)
  }

  // jsdom has no layout: give every element a size so that pointer positions turn into fractions of 200 x 100.
  const stubStage = () =>
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ left: 0, top: 0, width: 200, height: 100 } as DOMRect)
  const pointer = (wrapper: ReturnType<typeof mount>, type: string, [x, y]: [number, number]) =>
    wrapper.get('[data-testid="document-stage"]').element.dispatchEvent(new MouseEvent(type, { clientX: x, clientY: y, bubbles: true }))
  const click = async (wrapper: ReturnType<typeof mount>, at: [number, number]) => {
    pointer(wrapper, 'pointerdown', at)
    pointer(wrapper, 'pointerup', at)
    await flushPromises()
  }
  const drag = async (wrapper: ReturnType<typeof mount>, from: [number, number], to: [number, number]) => {
    pointer(wrapper, 'pointerdown', from)
    pointer(wrapper, 'pointermove', to)
    pointer(wrapper, 'pointerup', to)
    await flushPromises()
  }
  const key = (name: string) => window.dispatchEvent(new KeyboardEvent('keydown', { key: name, bubbles: true }))
  /** A form with an image and one entity set to a zone: the drawing is under way. */
  async function startDrawing() {
    useSession().setUser('dana')
    const rect = stubStage()
    const page = await mountAt('/catalogue/nouveau')
    await upload(page.wrapper, png())
    await addEntity(page.wrapper, 'Cachet', 'Le cachet')
    await page.wrapper.get('[data-testid="entity"] input[id$="-zone"]').setValue(true) // starts the drawing by itself
    return { ...page, rect }
  }
  const row = (wrapper: ReturnType<typeof mount>) => wrapper.get('.entity__zone')
  const zones = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[data-testid="entity-zone"]')

  it('creates a template without any document', async () => {
    useSession().setUser('dana')
    const { wrapper, router } = await mountAt('/catalogue/nouveau')
    await field(wrapper, 'Nom').setValue('Sans document')
    await field(wrapper, 'Description').setValue('Rien à joindre')
    await wrapper.get('form').trigger('submit')
    await landsOn(router, 'catalogue-detail')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Sans document'))
    expect(wrapper.find('[data-testid="document-name"]').exists()).toBe(false)
  })

  it('has no size field', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/nouveau')
    expect(wrapper.text()).not.toContain('Taille')
  })

  it('accepts an image or a PDF and refuses anything else', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/nouveau')
    expect(wrapper.get('input[type="file"]').attributes('accept')).toBe(
      'image/png,image/jpeg,image/webp,image/gif,application/pdf',
    )

    await upload(wrapper, new File(['x'], 'notes.txt', { type: 'text/plain' }))
    expect(wrapper.get('#document-error').text()).toContain('image')
    expect(wrapper.find('[data-testid="document-name"]').exists()).toBe(false)

    await upload(wrapper, png())
    expect(wrapper.find('#document-error').exists()).toBe(false)
    expect(wrapper.get('[data-testid="document-name"]').text()).toBe('scan.png')
    // Sent to the backend, which serves the image of its page.
    expect(wrapper.find('img').attributes('src')).toMatch(/^\/api\/documents\/[^/]+\/pages\/1$/)
    expect(uploaded()).toHaveLength(1)

    // A PDF is shown through the screenshots of its pages; the image it replaces is deleted from the backend.
    await upload(wrapper, new File(['x'], 'doc.pdf', { type: 'application/pdf' }))
    expect(wrapper.get('[data-testid="document-name"]').text()).toBe('doc.pdf')
    expect(uploaded().map((d) => d.name)).toEqual(['doc.pdf'])
    expect(wrapper.find('img').exists()).toBe(true)
    expect(wrapper.get('[data-testid="page-number"]').text()).toBe('Page 1 / 3')
  })

  it('says why the backend refused a document', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/nouveau')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ detail: 'Ce PDF est illisible.' }) }))
    await upload(wrapper, new File(['x'], 'doc.pdf', { type: 'application/pdf' }))
    expect(wrapper.get('#document-error').text()).toBe('Ce PDF est illisible.')
    expect(wrapper.find('[data-testid="document-name"]').exists()).toBe(false)

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    await upload(wrapper, png())
    expect(wrapper.get('#document-error').text()).toBe('Le document n’a pas pu être envoyé.')
  })

  describe('what a PDF suggests', () => {
    const pdf = () => new File(['x'], 'formulaire.pdf', { type: 'application/pdf' })

    it('offers the entities detected in a PDF, and adds them with their zones, to be improved', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      expect(wrapper.find('[data-testid="suggestions"]').exists()).toBe(false)
      await upload(wrapper, pdf())
      expect(wrapper.get('[data-testid="suggestions"]').text()).toContain('2 entités détectées dans ce PDF.')

      await wrapper.get('[data-testid="suggestions-add"]').trigger('click')

      expect(wrapper.find('[data-testid="suggestions"]').exists()).toBe(false) // offered once
      expect(entityCount(wrapper)).toBe('1 / 2')
      expect(field(wrapper, 'Nom', 2).element.value).toBe('Nom du demandeur') // after the form's name and the page's
      expect(field(wrapper, 'Définition').element.value).toBe('Le champ « Nom du demandeur » du document.')
      expect(wrapper.get('[data-testid="entity"] input[id$="-zone"]').element.checked).toBe(true) // found by its zone
      // Its zone is outlined on the page it is on.
      expect(wrapper.findAll('[data-testid="entity-zone"]')).toHaveLength(1)
    })

    it('adds them after the entities already there', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await addEntity(wrapper)
      await upload(wrapper, pdf())
      await wrapper.get('[data-testid="suggestions-add"]').trigger('click')
      expect(entityCount(wrapper)).toBe('1 / 3') // its own, then the two of the PDF
    })

    it('can be ignored', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await upload(wrapper, pdf())
      await wrapper.get('[data-testid="suggestions-ignore"]').trigger('click')
      expect(wrapper.find('[data-testid="suggestions"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="entity"]').exists()).toBe(false)
    })

    it('suggests nothing for an image, or when the backend cannot say, or once the document is taken off', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await upload(wrapper, png())
      expect(wrapper.find('[data-testid="suggestions"]').exists()).toBe(false)

      await upload(wrapper, pdf())
      expect(wrapper.find('[data-testid="suggestions"]').exists()).toBe(true)
      await button(wrapper, 'Retirer le document').trigger('click')
      expect(wrapper.find('[data-testid="suggestions"]').exists()).toBe(false)

      vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => (path.endsWith('/suggestions') ? Promise.reject(new Error('down')) : fakeFetch(path, init))))
      await upload(wrapper, pdf())
      expect(wrapper.find('[data-testid="suggestions"]').exists()).toBe(false)
      expect(wrapper.find('#document-error').exists()).toBe(false) // the document itself was taken
    })

    it('are those of the document of the form: a document chosen since leaves the old ones out', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await upload(wrapper, pdf())
      await upload(wrapper, png())
      expect(wrapper.find('[data-testid="suggestions"]').exists()).toBe(false)
    })
  })

  describe('the pages of a model', () => {
    const pdf = () => new File(['x'], 'formulaire.pdf', { type: 'application/pdf' })
    // The field of the model, not the ones of a page that start the same way.
    const exact = (wrapper: ReturnType<typeof mount>, label: string) =>
      wrapper.get(`#${wrapper.findAll('label').find((l) => l.text() === label)!.attributes('for')}`)

    it('can each be given a name and a description, with the model\'s name and the number as the default', async () => {
      useSession().setUser('dana')
      const { wrapper, router } = await mountAt('/catalogue/nouveau')
      expect(wrapper.find('[data-testid="page-fields"]').exists()).toBe(false) // no document, no page
      await upload(wrapper, png())
      expect(wrapper.find('[data-testid="page-fields"]').exists()).toBe(false) // an image is one page

      await upload(wrapper, pdf())
      await exact(wrapper, 'Nom').setValue('Formulaire X')
      expect(field(wrapper, 'Nom de la page 1').attributes('placeholder')).toBe('Formulaire X · page 1')

      await wrapper.get('.doc-viewer button[title="Page suivante"]').trigger('click')
      await field(wrapper, 'Nom de la page 2').setValue('Pièces justificatives')
      await field(wrapper, 'Description de la page 2').setValue('Les annexes à joindre')
      await wrapper.get('.doc-viewer button[title="Page suivante"]').trigger('click')
      expect(field(wrapper, 'Nom de la page 3').element.value).toBe('') // the other pages are the default
      await exact(wrapper, 'Description').setValue('Un formulaire')
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'catalogue-detail')
      await vi.waitFor(() => expect(wrapper.find('[data-testid="page-note"]').exists()).toBe(true))

      // The page of the model is shown with how it is called, and what is said of it.
      expect(wrapper.get('[data-testid="page-note"]').text()).toBe('Formulaire X · page 1')
      await wrapper.get('.doc-viewer button[title="Page suivante"]').trigger('click')
      expect(wrapper.get('[data-testid="page-note"]').text()).toBe('Formulaire X · Pièces justificatives — Les annexes à joindre')
    })

    it('goes back to the default when the name is taken away', async () => {
      useSession().setUser('dana')
      const { create } = useCatalogue()
      const document = await uploadDocument(pdf())
      const made = await create({ name: 'Formulaire X', description: 'Un formulaire', categories: [], entities: [], pages: [{ page: 1, name: 'Couverture', description: '' }] }, document)
      const { wrapper, router } = await mountAt(`/catalogue/${made.id}/modifier`)
      expect(field(wrapper, 'Nom de la page 1').element.value).toBe('Couverture')
      await field(wrapper, 'Nom de la page 1').setValue('')
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'catalogue-detail')
      await vi.waitFor(() => expect(wrapper.find('[data-testid="page-note"]').exists()).toBe(true))
      expect(wrapper.get('[data-testid="page-note"]').text()).toBe('Formulaire X · page 1')
    })

    it('has nothing said of a document the model has no more', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await upload(wrapper, pdf())
      await field(wrapper, 'Nom de la page 1').setValue('Couverture')
      await upload(wrapper, pdf()) // another document: what was said of the pages of the first means nothing
      expect(field(wrapper, 'Nom de la page 1').element.value).toBe('')
    })

    it('shows the page of an entity\'s zone when the document has several', async () => {
      useSession().setUser('dana')
      const { create } = useCatalogue()
      const document = await uploadDocument(pdf())
      const zone = { page: 3, points: [{ x: 0.1, y: 0.1 }, { x: 0.4, y: 0.1 }, { x: 0.4, y: 0.3 }] }
      const made = await create(
        { name: 'Formulaire X', description: 'Un formulaire', categories: [], pages: [], entities: [{ ...newEntity(), name: 'Signature', definition: 'En bas', zones: [zone] }] },
        document,
      )
      const { wrapper } = await mountAt(`/catalogue/${made.id}`)
      expect(wrapper.get('[data-testid="entity-kind"]').text()).toBe('Zone · page 3')
      // The viewer goes to the page of the entity that is on show.
      await vi.waitFor(() => expect(wrapper.get('[data-testid="page-number"]').text()).toBe('Page 3 / 3'))
    })
  })

  it('looks at the pages of a PDF one at a time', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/nouveau')
    await upload(wrapper, new File(['x'], 'doc.pdf', { type: 'application/pdf' }))
    const page = () => wrapper.get('[data-testid="page-number"]').text()
    expect(wrapper.get('button[title="Page précédente"]').attributes('disabled')).toBeDefined()
    await wrapper.get('button[title="Page suivante"]').trigger('click')
    expect(page()).toBe('Page 2 / 3')
    expect(wrapper.find('img').attributes('src')).toMatch(/\/pages\/2$/)
    await wrapper.get('button[title="Page suivante"]').trigger('click')
    expect(wrapper.get('button[title="Page suivante"]').attributes('disabled')).toBeDefined()
    await wrapper.get('button[title="Page précédente"]').trigger('click')
    expect(page()).toBe('Page 2 / 3')
  })

  it('replaces or removes the document', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/nouveau')
    await upload(wrapper, png())
    expect(button(wrapper, 'Remplacer')).toBeDefined()
    await button(wrapper, 'Retirer le document').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="document-name"]').exists()).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
    expect(uploaded()).toHaveLength(0) // taken off the backend too, as nothing keeps it
  })

  describe('categories', () => {
    const categories = (wrapper: ReturnType<typeof mount>) =>
      wrapper.findAll('.categories .tags-input__tags button').map((b) => b.text())
    const typeCategory = async (wrapper: ReturnType<typeof mount>, value: string) => {
      await wrapper.get('.categories input').setValue(value)
      await wrapper.get('.categories input').trigger('keydown.enter')
    }

    it('takes custom categories as tags, and refuses blanks and duplicates', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await typeCategory(wrapper, 'Sur mesure')
      await typeCategory(wrapper, '  ')
      await typeCategory(wrapper, 'sur mesure')
      expect(categories(wrapper)).toEqual(['Sur mesure'])
      expect(wrapper.get('.categories input').element.value).toBe('')
    })

    it('adds what was typed when leaving the field, and removes a tag from its button', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await wrapper.get('.categories input').setValue('Courrier')
      await wrapper.get('.categories input').trigger('blur')
      expect(categories(wrapper)).toEqual(['Courrier'])
      await wrapper.get('.categories .tags-input__tags button').trigger('click')
      expect(categories(wrapper)).toEqual([])
    })

    it('takes back the last tag with Backspace in an empty field, but not while there is text', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await typeCategory(wrapper, 'Un')
      await typeCategory(wrapper, 'Deux')
      await wrapper.get('.categories input').setValue('Tr')
      await wrapper.get('.categories input').trigger('keydown.backspace')
      expect(categories(wrapper)).toEqual(['Un', 'Deux'])
      await wrapper.get('.categories input').setValue('')
      await wrapper.get('.categories input').trigger('keydown.backspace')
      expect(categories(wrapper)).toEqual(['Un'])
    })

    it('offers the usual and the existing categories, and adds one picked in the list at once', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      const options = wrapper.findAll('datalist option').map((o) => o.attributes('value'))
      expect(options).toContain('Tampon')
      expect(options).toContain('Officiel') // made up on a demo model
      await wrapper.get('.categories input').setValue('Tampon') // exactly a suggestion: a pick, not typing
      expect(categories(wrapper)).toEqual(['Tampon'])
      expect(wrapper.findAll('datalist option').map((o) => o.attributes('value'))).not.toContain('Tampon')
    })

    it('keeps what is being typed until Enter or leaving the field', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await wrapper.get('.categories input').setValue('Sur mes')
      expect(categories(wrapper)).toEqual([])
      expect(wrapper.get('.categories input').element.value).toBe('Sur mes')
    })

    it('saves them on the model and shows them as tags', async () => {
      useSession().setUser('dana')
      const { wrapper, router } = await mountAt('/catalogue/nouveau')
      await field(wrapper, 'Nom').setValue('Avec catégories')
      await field(wrapper, 'Description').setValue('Deux tags')
      await wrapper.get('.categories input').setValue('Tampon')
      await typeCategory(wrapper, 'Sur mesure')
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'catalogue-detail')
      await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Avec catégories'))
      expect(wrapper.findAll('.template-view__meta .fr-tag').map((t) => t.text())).toEqual(['Tampon', 'Sur mesure'])
    })
  })

  describe('entities, one at a time', () => {
    it('describes an entity by name and definition, and requires both', async () => {
      useSession().setUser('dana')
      const { wrapper, router } = await mountAt('/catalogue/nouveau')
      await field(wrapper, 'Nom').setValue('Facture')
      await field(wrapper, 'Description').setValue('Une facture')
      expect(entityCount(wrapper)).toBe('0')
      expect(wrapper.text()).toContain('Aucune entité')
      await addEntity(wrapper)
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(router.currentRoute.value.name).toBe('catalogue-new')
      expect(wrapper.text()).toContain('Donnez un nom à l’entité.')
      expect(wrapper.text()).toContain('Ajoutez une définition.')

      expect(wrapper.get('[data-testid="missing"]').text()).toBe('À compléter : l’entité 1.')
      await field(wrapper, 'Nom', 1).setValue('Numéro de facture')
      await field(wrapper, 'Définition').setValue('Le numéro en haut à droite')
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'catalogue-detail')
      await vi.waitFor(() => expect(wrapper.get('[data-testid="entity"]').text()).toContain('Numéro de facture'))
      expect(wrapper.get('[data-testid="entity"]').text()).toContain('Définition')
    })

    it('shows one entity at a time and pages through them', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await addEntity(wrapper, 'A', 'La première')
      await addEntity(wrapper, 'B', 'La deuxième')
      await addEntity(wrapper, 'C', 'La troisième')
      expect(entityCount(wrapper)).toBe('3 / 3')
      expect(wrapper.findAll('[data-testid="entity"]')).toHaveLength(1)
      expect((field(wrapper, 'Nom', 1).element as HTMLInputElement).value).toBe('C')
      expect(byTitle(wrapper, 'Entité suivante').attributes('disabled')).toBeDefined()

      await byTitle(wrapper, 'Entité précédente').trigger('click')
      expect(entityCount(wrapper)).toBe('2 / 3')
      expect((field(wrapper, 'Nom', 1).element as HTMLInputElement).value).toBe('B')
      await byTitle(wrapper, 'Entité précédente').trigger('click')
      expect(byTitle(wrapper, 'Entité précédente').attributes('disabled')).toBeDefined()
      expect((field(wrapper, 'Nom', 1).element as HTMLInputElement).value).toBe('A')
    })

    it('removes the entity on show', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await addEntity(wrapper, 'A', 'La première')
      await addEntity(wrapper, 'B', 'La deuxième')
      await button(wrapper, 'Supprimer cette entité').trigger('click')
      expect(entityCount(wrapper)).toBe('1 / 1')
      expect((field(wrapper, 'Nom', 1).element as HTMLInputElement).value).toBe('A')
      await button(wrapper, 'Supprimer cette entité').trigger('click')
      expect(entityCount(wrapper)).toBe('0')
      expect(wrapper.text()).toContain('Aucune entité')
    })

    it('jumps to the first incomplete entity when saving', async () => {
      useSession().setUser('dana')
      const { wrapper, router } = await mountAt('/catalogue/nouveau')
      await field(wrapper, 'Nom').setValue('Facture')
      await field(wrapper, 'Description').setValue('Une facture')
      await addEntity(wrapper, 'A', 'Complète')
      await addEntity(wrapper, 'B') // no definition
      await addEntity(wrapper, 'C', 'Complète')
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(router.currentRoute.value.name).toBe('catalogue-new')
      expect(entityCount(wrapper)).toBe('2 / 3')
      expect(wrapper.text()).toContain('Ajoutez une définition.')
      expect(wrapper.get('[data-testid="missing"]').text()).toBe('À compléter : l’entité 2.')
    })
  })

  describe('type and examples of an entity', () => {
    const typeSelect = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="entity"] select')
    const examples = (wrapper: ReturnType<typeof mount>) =>
      wrapper.findAll('.entity__examples .tags-input__tags button').map((b) => b.text())
    const typeExample = async (wrapper: ReturnType<typeof mount>, value: string) => {
      const input = wrapper.get('.entity__examples input')
      await input.setValue(value)
      await input.trigger('keydown.enter')
    }

    it('offers the types, starting at text', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await addEntity(wrapper)
      // The select's own « Sélectionner une option » is disabled: it is not a type.
      const options = typeSelect(wrapper).findAll('option').filter((o) => o.attributes('disabled') === undefined)
      expect(options.map((o) => o.text())).toEqual([
        'Texte',
        'Date',
        'Entier',
        'Nombre décimal',
        'Montant',
        'Pourcentage',
        'Oui / non',
        'Image',
        'Tableau',
      ])
      expect((typeSelect(wrapper).element as HTMLSelectElement).value).toBe('text')
    })

    const info = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="entity"] .info-tip__button')

    it('has an « i » that gives the definition of the type, which follows the type chosen', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await addEntity(wrapper)
      expect(info(wrapper).attributes('aria-label')).toBe('Définition du type Texte')
      expect(wrapper.find('.info-tip__panel').exists()).toBe(false)
      await info(wrapper).trigger('click')
      expect(wrapper.get('.info-tip__panel').text()).toContain('Une suite de caractères libre')
      await typeSelect(wrapper).setValue('amount')
      expect(info(wrapper).attributes('aria-label')).toBe('Définition du type Montant')
      expect(wrapper.get('.info-tip__panel').text()).toContain('Montant')
      expect(wrapper.get('.info-tip__panel').text()).toContain('Une somme d’argent')
    })

    it('has an « i » on the page of a model too, with the definition of the type of the entity on show', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t2')
      expect(wrapper.get('[data-testid="entity-type"]').text()).toBe('Date')
      await info(wrapper).trigger('click')
      expect(wrapper.get('.info-tip__panel').text()).toContain('AAAA-MM-JJ')
    })

    it('takes examples as tags: added with Enter, kept distinct, at most five, taken back', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await addEntity(wrapper)
      await typeExample(wrapper, '12/03/2026')
      await typeExample(wrapper, '12/03/2026') // twice
      await typeExample(wrapper, '   ') // blank
      await typeExample(wrapper, 'a')
      await typeExample(wrapper, 'A') // another example: case counts here
      expect(examples(wrapper)).toEqual(['12/03/2026', 'a', 'A'])
      await typeExample(wrapper, 'd')
      await typeExample(wrapper, 'e')
      expect(examples(wrapper)).toHaveLength(5)
      expect(wrapper.get('.entity__examples input').attributes('disabled')).toBeDefined() // no sixth
      await wrapper.get('.entity__examples .tags-input__tags button').trigger('click')
      expect(examples(wrapper)).toEqual(['a', 'A', 'd', 'e'])
      expect(wrapper.get('.entity__examples input').attributes('disabled')).toBeUndefined()
    })

    it('takes optional tags, apart from the examples: added with Enter, one for « Verso » and « verso », taken back', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await addEntity(wrapper)
      const tags = () => wrapper.findAll('.entity__tags .tags-input__tags button').map((b) => b.text())
      expect(tags()).toEqual([]) // optional
      const input = wrapper.get('.entity__tags input')
      for (const value of ['Verso', 'verso', '  ', 'à la main']) {
        await input.setValue(value)
        await input.trigger('keydown.enter')
      }
      expect(tags()).toHaveLength(2)
      expect(examples(wrapper)).toEqual([]) // the examples are not the tags
      await wrapper.get('.entity__tags .tags-input__tags button').trigger('click')
      expect(tags()).toHaveLength(1)
    })

    it('has them of its own for each entity', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await addEntity(wrapper, 'A', 'Un')
      await typeExample(wrapper, 'un exemple')
      await typeSelect(wrapper).setValue('amount')
      await addEntity(wrapper, 'B', 'Deux')
      expect(examples(wrapper)).toEqual([])
      expect((typeSelect(wrapper).element as HTMLSelectElement).value).toBe('text')
      await byTitle(wrapper, 'Entité précédente').trigger('click')
      expect(examples(wrapper)).toEqual(['un exemple'])
      expect((typeSelect(wrapper).element as HTMLSelectElement).value).toBe('amount')
    })

    it('saves them on the model and shows them on its page', async () => {
      useSession().setUser('dana')
      const { wrapper, router } = await mountAt('/catalogue/nouveau')
      await field(wrapper, 'Nom').setValue('Facture')
      await field(wrapper, 'Description').setValue('Une facture')
      await addEntity(wrapper, 'Total TTC', 'Le montant à payer')
      await typeSelect(wrapper).setValue('amount')
      await typeExample(wrapper, '1 250,00 €')
      await typeExample(wrapper, '89,90 €')
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'catalogue-detail')
      await vi.waitFor(() => expect(wrapper.get('[data-testid="entity"]').text()).toContain('Total TTC'))
      expect(wrapper.get('[data-testid="entity-type"]').text()).toBe('Montant')
      expect(wrapper.get('[data-testid="entity-examples"]').text()).toContain('1 250,00 €')
      expect(wrapper.get('[data-testid="entity-examples"]').text()).toContain('89,90 €')
    })

    it('shows the type and the examples of the demo entities, and nothing for an entity without example', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t2')
      expect(wrapper.get('[data-testid="entity-type"]').text()).toBe('Date')
      expect(wrapper.get('[data-testid="entity-examples"]').text()).toContain('12/03/2026')
      const noExample = await mountAt('/catalogue/t1')
      await byTitle(noExample.wrapper, 'Entité suivante').trigger('click')
      expect(noExample.wrapper.get('[data-testid="entity-type"]').text()).toBe('Texte')
      expect(noExample.wrapper.get('[data-testid="entity-examples"]').text()).toContain('Liberté Égalité Fraternité')
    })

    it('brings the entity of a zone up when it is clicked on the document of a model', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t1')
      await byTitle(wrapper, 'Entité suivante').trigger('click')
      expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('2 / 2')
      wrapper.findComponent({ name: 'DocumentViewer' }).vm.$emit('select', 'e1')
      await flushPromises()
      expect(wrapper.get('[data-testid="pager-count"]').text()).toBe('1 / 2')
      expect(wrapper.get('.entity-card').text()).toContain('Emblème')
    })

    it('is filled in when editing an existing model, and changed in place', async () => {
      useSession().setUser('bob.durand') // owns t2
      const { wrapper, router } = await mountAt('/catalogue/t2/modifier')
      expect((typeSelect(wrapper).element as HTMLSelectElement).value).toBe('date')
      expect(examples(wrapper)).toEqual(['12/03/2026', '1 novembre 2026'])
      await typeSelect(wrapper).setValue('text')
      await wrapper.get('.entity__examples .tags-input__tags button').trigger('click')
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'catalogue-detail')
      await vi.waitFor(() => expect(wrapper.get('[data-testid="entity-type"]').text()).toBe('Texte'))
      expect(wrapper.get('[data-testid="entity-examples"]').text()).toContain('1 novembre 2026')
      expect(wrapper.get('[data-testid="entity-examples"]').text()).not.toContain('12/03/2026')
    })
  })

  it('offers the zone mode only once there is a document', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/nouveau')
    await addEntity(wrapper)
    const zone = () => wrapper.get('[data-testid="entity"] input[id$="-zone"]')
    expect(zone().attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Ajoutez un document d’exemple')
    await upload(wrapper, png())
    expect(zone().attributes('disabled')).toBeUndefined()
  })

  it('offers to draw a zone on a PDF, on the page that is shown', async () => {
    useSession().setUser('dana')
    const { wrapper } = await mountAt('/catalogue/nouveau')
    await upload(wrapper, new File(['x'], 'doc.pdf', { type: 'application/pdf' }))
    await addEntity(wrapper)
    expect(wrapper.get('[data-testid="entity"] input[id$="-zone"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).not.toContain('Pas encore disponible pour un PDF')
  })

  describe('drawing a zone on the document', () => {
    it('starts as soon as the zone is chosen, with a Cancel button next to the instruction', async () => {
      const { wrapper, rect } = await startDrawing()
      const row = wrapper.get('.entity__zone')
      expect(row.get('[data-testid="draw-hint"]').text()).toContain('Dessin en cours')
      expect(row.findAll('button').map((b) => b.text())).toEqual(['Annuler'])
      expect(wrapper.find('[data-testid="zoom-level"]').exists()).toBe(true) // the document is ready: toolbar with the tools
      expect(button(wrapper, 'Polygone').attributes('aria-pressed')).toBe('true')
      rect.mockRestore()
    })

    it('can be cancelled and started again', async () => {
      const { wrapper, rect } = await startDrawing()
      await row(wrapper).get('.fr-btn--tertiary').trigger('click')
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(false)
      expect(button(wrapper, 'Dessiner la zone')).toBeDefined()
      await button(wrapper, 'Dessiner la zone').trigger('click')
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(true)
      rect.mockRestore()
    })

    it('does not start for the definition mode, nor without an image', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await upload(wrapper, png())
      await addEntity(wrapper, 'A', 'B')
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(false)
      await wrapper.get('[data-testid="entity"] input[id$="-zone"]').setValue(true)
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(true)
      await wrapper.get('[data-testid="entity"] input[id$="-definition"]').setValue(true)
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(false)
    })

    it('requires the zone once the zone mode is chosen', async () => {
      const { wrapper, router, rect } = await startDrawing()
      await wrapper.get('.entity__zone .fr-btn--tertiary').trigger('click') // stop drawing without a zone
      await field(wrapper, 'Nom').setValue('Tampon rond')
      await field(wrapper, 'Description').setValue('Un tampon')
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(wrapper.text()).toContain('Dessinez la zone sur le document.')
      expect(router.currentRoute.value.name).toBe('catalogue-new')
      rect.mockRestore()
    })

    it('draws a polygon point by point, closed by clicking the first point', async () => {
      const { wrapper, router, rect } = await startDrawing()
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(true)
      await click(wrapper, [20, 10])
      await click(wrapper, [120, 10])
      await click(wrapper, [120, 60])
      expect(wrapper.findAll('[data-testid="draft-point"]')).toHaveLength(3)
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(true) // not closed yet
      await click(wrapper, [20, 60])
      await click(wrapper, [22, 12]) // within a few pixels of the first point: closes
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(false)
      expect(wrapper.findAll('[data-testid="draft-point"]')).toHaveLength(0)
      expect(button(wrapper, 'Redessiner')).toBeDefined() // there is a zone now
      expect(zones(wrapper)).toHaveLength(1)
      expect(zones(wrapper)[0].attributes('points')).toBe('10,10 60,10 60,60 10,60')

      await field(wrapper, 'Nom').setValue('Tampon rond')
      await field(wrapper, 'Description').setValue('Un tampon')
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'catalogue-detail')
      await vi.waitFor(() => expect(wrapper.get('[data-testid="entity"]').text()).toContain('Zone'))
      expect(zones(wrapper)).toHaveLength(1)
      rect.mockRestore()
    })

    it('closes with Enter, removes the last point with Backspace and gives up with Escape', async () => {
      const { wrapper, rect } = await startDrawing()
      await click(wrapper, [20, 10])
      await click(wrapper, [120, 10])
      key('Enter')
      await flushPromises()
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(true) // two points make no zone

      await click(wrapper, [120, 60])
      key('Backspace')
      await flushPromises()
      expect(wrapper.findAll('[data-testid="draft-point"]')).toHaveLength(2)

      await click(wrapper, [120, 60])
      key('Enter')
      await flushPromises()
      expect(zones(wrapper)).toHaveLength(1)
      expect(zones(wrapper)[0].attributes('points')).toBe('10,10 60,10 60,60')

      await button(wrapper, 'Redessiner').trigger('click')
      await click(wrapper, [50, 50])
      key('Escape')
      await flushPromises()
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(false)
      expect(wrapper.findAll('[data-testid="draft-point"]')).toHaveLength(0)
      expect(zones(wrapper)).toHaveLength(1) // the earlier zone is kept
      rect.mockRestore()
    })

    it('leaves the keys alone while typing in a field', async () => {
      const { wrapper, rect } = await startDrawing()
      await click(wrapper, [20, 10])
      const input = field(wrapper, 'Description').element
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Backspace', bubbles: true }))
      await flushPromises()
      expect(wrapper.findAll('[data-testid="draft-point"]')).toHaveLength(1)
      rect.mockRestore()
    })

    it('puts the name of the entity on its zone, as it is typed', async () => {
      const { wrapper, rect } = await startDrawing() // « Cachet »
      await click(wrapper, [20, 10])
      await click(wrapper, [120, 10])
      await click(wrapper, [120, 60])
      key('Enter')
      await flushPromises()
      const label = () => wrapper.get('[data-testid="entity-label"]')
      expect(label().text()).toBe('Cachet')
      await field(wrapper, 'Nom', 1).setValue('Cachet de la préfecture')
      expect(label().text()).toBe('Cachet de la préfecture')
      expect(label().attributes('title')).toBe('Cachet de la préfecture') // in full, when the label is cut
      await field(wrapper, 'Nom', 1).setValue('   ')
      expect(label().text()).toBe('Entité 1') // no name yet
      rect.mockRestore()
    })

    it('labels each zone with its own entity\'s name', async () => {
      const { wrapper, rect } = await startDrawing()
      await click(wrapper, [20, 10])
      await click(wrapper, [120, 10])
      await click(wrapper, [120, 60])
      key('Enter')
      await flushPromises()
      await addEntity(wrapper, 'Signature', 'La signature')
      await wrapper.get('[data-testid="entity"] input[id$="-zone"]').setValue(true)
      await click(wrapper, [30, 20])
      await click(wrapper, [90, 20])
      await click(wrapper, [90, 70])
      key('Enter')
      await flushPromises()
      expect(wrapper.findAll('[data-testid="entity-label"]').map((l) => l.text())).toEqual(['Cachet', 'Signature'])
      rect.mockRestore()
    })

    it('draws a rectangle by dragging, as four points', async () => {
      const { wrapper, rect } = await startDrawing()
      await button(wrapper, 'Rectangle').trigger('click')
      await drag(wrapper, [20, 10], [120, 60])
      expect(zones(wrapper)).toHaveLength(1)
      expect(zones(wrapper)[0].attributes('points')).toBe('10,10 60,10 60,60 10,60')
      rect.mockRestore()
    })

    it('ignores a stray click with the rectangle tool', async () => {
      const { wrapper, rect } = await startDrawing()
      await button(wrapper, 'Rectangle').trigger('click')
      await drag(wrapper, [50, 50], [51, 51])
      expect(zones(wrapper)).toHaveLength(0)
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(true) // still waiting for a real zone
      rect.mockRestore()
    })

    it('stops drawing when moving to another entity', async () => {
      const { wrapper, rect } = await startDrawing()
      await addEntity(wrapper, 'Autre', 'Une autre')
      expect(wrapper.find('[data-testid="draw-hint"]').exists()).toBe(false)
      rect.mockRestore()
    })
  })

  describe('zooming the document', () => {
    const level = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="zoom-level"]').text()

    it('zooms in and out with the buttons, and back to the whole image', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await upload(wrapper, png())
      expect(level(wrapper)).toBe('100 %')
      expect(byTitle(wrapper, 'Dézoomer').attributes('disabled')).toBeDefined() // never smaller than the whole image
      await byTitle(wrapper, 'Zoomer').trigger('click')
      await flushPromises()
      expect(level(wrapper)).toBe('125 %')
      await byTitle(wrapper, 'Zoomer').trigger('click')
      await flushPromises()
      expect(level(wrapper)).toBe('156 %')
      await byTitle(wrapper, 'Dézoomer').trigger('click')
      await flushPromises()
      expect(level(wrapper)).toBe('125 %')
      await wrapper.get('[data-testid="zoom-level"]').trigger('click')
      await flushPromises()
      expect(level(wrapper)).toBe('100 %')
    })

    it('stops at 800 %', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await upload(wrapper, png())
      for (let i = 0; i < 12; i++) {
        await byTitle(wrapper, 'Zoomer').trigger('click')
        await flushPromises()
      }
      expect(level(wrapper)).toBe('800 %')
      expect(byTitle(wrapper, 'Zoomer').attributes('disabled')).toBeDefined()
    })

    it('zooms with Ctrl + wheel, and leaves a plain wheel to scroll', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/nouveau')
      await upload(wrapper, png())
      const viewport = wrapper.get('[data-testid="document-viewport"]').element
      const wheel = (init: WheelEventInit) => {
        const event = new WheelEvent('wheel', { bubbles: true, cancelable: true, clientX: 100, clientY: 50, ...init })
        viewport.dispatchEvent(event)
        return event
      }
      expect(wheel({ deltaY: -100 }).defaultPrevented).toBe(false)
      await flushPromises()
      expect(level(wrapper)).toBe('100 %')
      expect(wheel({ deltaY: -100, ctrlKey: true }).defaultPrevented).toBe(true)
      await flushPromises()
      expect(level(wrapper)).toBe('120 %')
      wheel({ deltaY: 100, ctrlKey: true })
      await flushPromises()
      expect(level(wrapper)).toBe('100 %')
    })

    it('draws at the right place whatever the zoom', async () => {
      const { wrapper, rect } = await startDrawing()
      await byTitle(wrapper, 'Zoomer').trigger('click')
      await flushPromises()
      // The stage is still reported as 200 x 100: points are read from where the page says the image is.
      await click(wrapper, [100, 50])
      expect(wrapper.get('[data-testid="draft-point"]').attributes('style')).toContain('left: 50%')
      rect.mockRestore()
    })
  })

  it('drops the zones when the document is replaced', async () => {
    useSession().setUser('alice.martin')
    const { wrapper } = await mountAt('/catalogue/t1/modifier')
    expect(wrapper.text()).toContain('courrier-exemple.svg')
    expect(zones(wrapper)).toHaveLength(1)
    await upload(wrapper, new File(['x'], 'autre.png', { type: 'image/png' }))
    expect(wrapper.text()).toContain('Les zones dessinées ont été retirées')
    expect(zones(wrapper)).toHaveLength(0)
    expect(wrapper.get('[data-testid="document-name"]').text()).toBe('autre.png')
  })

  describe('the page of a model', () => {
    it('is deleted by its owner, after a confirmation, and the catalogue goes on without it', async () => {
      useSession().setUser('dana')
      const made = await useCatalogue().create({ name: 'À jeter', description: 'Pour voir.', categories: [], entities: [], pages: [] })
      const { wrapper, router } = await mountAt(`/catalogue/${made.id}`)
      await wrapper.get('[data-testid="delete"]').trigger('click')
      expect(wrapper.get('[data-testid="confirm"]').text()).toContain('Supprimer ce modèle ?')
      await wrapper.get('[data-testid="confirm-no"]').trigger('click') // not so sure after all
      expect(wrapper.find('[data-testid="confirm"]').exists()).toBe(false)
      expect(router.currentRoute.value.name).toBe('catalogue-detail')
      await wrapper.get('[data-testid="delete"]').trigger('click')
      await wrapper.get('[data-testid="confirm-yes"]').trigger('click')
      await landsOn(router, 'catalogue')
      expect(useCatalogue().find(made.id)).toBeUndefined()
      expect(wrapper.text()).not.toContain('À jeter')
    })

    it('is not offered for a model that is someone else\'s', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t1')
      expect(wrapper.find('[data-testid="delete"]').exists()).toBe(false)
    })

    it('says why it is not deleted when an analysis looks for it, and stays', async () => {
      useSession().setUser('alice.martin')
      const { wrapper, router } = await mountAt('/catalogue/t1')
      await wrapper.get('[data-testid="delete"]').trigger('click')
      await wrapper.get('[data-testid="confirm-yes"]').trigger('click')
      expect(wrapper.get('[data-testid="action-error"]').text()).toContain('utilisé par')
      expect(router.currentRoute.value.name).toBe('catalogue-detail')
      expect(useCatalogue().find('t1')).toBeDefined()
    })

    const tabs = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('[role="tab"]').map((t) => t.text())

    it('shows the version of the model and its history, and the owner goes back to one', async () => {
      useSession().setUser('alice.martin')
      const { wrapper } = await mountAt('/catalogue/t1')
      expect(wrapper.get('[data-testid="template-version"]').text()).toBe('v1.0.0')

      await wrapper.get('[data-testid="versions-tab"]').trigger('click')
      await vi.waitFor(() => expect(wrapper.findAll('[data-testid="version-number"]').map((v) => v.text())).toEqual(['v1.0.0']))
      expect(wrapper.find('[data-testid="versions"] [data-testid="confirm"]').exists()).toBe(false) // it is the current one
      expect(wrapper.get('[data-testid="versions"]').text()).toContain('Courante')
    })

    it('goes back to an old version, which makes a new one on top', async () => {
      useSession().setUser('alice.martin')
      await restoreVersion('t1', '1.0.0') // the model is at 1.1.0 now, with 1.0.0 in its history
      const { wrapper } = await mountAt('/catalogue/t1')
      await wrapper.get('[data-testid="versions-tab"]').trigger('click')
      await vi.waitFor(() => expect(wrapper.findAll('[data-testid="version-number"]').map((v) => v.text())).toEqual(['v1.1.0', 'v1.0.0']))

      await wrapper.get('[data-testid="versions"] [data-testid="delete"]').trigger('click')
      await wrapper.get('[data-testid="confirm-yes"]').trigger('click')

      await vi.waitFor(() => expect(wrapper.findAll('[data-testid="version-number"]').map((v) => v.text())).toEqual(['v1.2.0', 'v1.1.0', 'v1.0.0']))
      expect(wrapper.get('[data-testid="template-version"]').text()).toBe('v1.2.0')
    })

    it('does not offer to go back to someone who does not own the model', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t1')
      await wrapper.get('[data-testid="versions-tab"]').trigger('click')
      await vi.waitFor(() => expect(wrapper.findAll('[data-testid="version"]')).toHaveLength(1))
      expect(wrapper.text()).not.toContain('Revenir à cette version')
    })

    it('has the layout of the form, read-only, with the document and the entities', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t1')
      expect(wrapper.find('.template-page').exists()).toBe(true) // the same two halves as the form
      expect(wrapper.get('[data-testid="document-name"]').text()).toBe('courrier-exemple.svg')
      expect(zones(wrapper)).toHaveLength(1)
      expect(wrapper.get('[data-testid="template-owner"]').text()).toBe('alice.martin')
      expect(wrapper.findAll('.template-view__meta .fr-tag').map((t) => t.text())).toEqual(['Identité', 'Officiel'])
      expect(wrapper.get('[data-testid="description"]').text()).toContain('Bloc-marque')
      expect(wrapper.find('input[type="file"]').exists()).toBe(false) // nothing to fill in
      expect(wrapper.find('textarea').exists()).toBe(false)
    })

    it('offers the owner to edit, and anyone else to suggest', async () => {
      useSession().setUser('alice.martin')
      const owner = await mountAt('/catalogue/t1')
      const edit = owner.wrapper.get('a[href$="/catalogue/t1/modifier"]')
      expect(edit.text()).toBe('Modifier')

      useSession().setUser('dana')
      const other = await mountAt('/catalogue/t1')
      expect(other.wrapper.get('a[href$="/catalogue/t1/modifier"]').text()).toBe('Suggérer une modification')
    })

    it('shows the entities one at a time', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t1')
      expect(tabs(wrapper)).toEqual(['Entités (2)', 'Suggestions (1)', 'Qualité', 'Versions'])
      expect(entityCount(wrapper)).toBe('1 / 2')
      expect(wrapper.findAll('[data-testid="entity"]')).toHaveLength(1)
      expect(wrapper.get('[data-testid="entity"]').text()).toContain('Emblème')
      expect(wrapper.get('[data-testid="entity"]').text()).toContain('Zone')
      await byTitle(wrapper, 'Entité suivante').trigger('click')
      expect(entityCount(wrapper)).toBe('2 / 2')
      expect(wrapper.get('[data-testid="entity"]').text()).toContain('Devise')
      expect(wrapper.get('[data-testid="entity"]').text()).toContain('Définition')
    })

    describe('the quality tab', () => {
      const quality = async () => {
        useSession().setUser('dana')
        const page = await mountAt('/catalogue/t1')
        await page.wrapper.get('[data-testid="quality-tab"]').trigger('click')
        await flushPromises()
        return page.wrapper
      }

      it('says how right the analysis has been on the model: its pages, its elements and each entity', async () => {
        const wrapper = await quality()
        expect(wrapper.get('[data-testid="quality-pages"] h3').text()).toBe('Classification des pages')
        expect(wrapper.get('[data-testid="quality-elements"] h3').text()).toBe('Éléments trouvés')
        expect(wrapper.findAll('[data-testid="quality-entity"]').map((r) => r.find('th').text())).toEqual(['Emblème', 'Devise'])
        expect(wrapper.get('[data-testid="quality-pages"] [data-testid="exact"]').exists()).toBe(true)
      })

      it('learns from what people decide: a prediction validated is one more right', async () => {
        const correct = (wrapper: Awaited<ReturnType<typeof quality>>) =>
          Number(wrapper.get('[data-testid="quality-elements"] [data-testid="counts"]').text().match(/^(\d+) juste/)![1])
        const before = correct(await quality())
        // alice.martin tries the analysis on a document in which t1 is found, and validates what was found.
        useSession().setUser('alice.martin')
        const name = Array.from({ length: 300 }, (_, i) => `essai-${i}.png`).find(
          (n) => simulateTest({ templateIds: ['t1', 't6'] }, { name: n, size: 1 }).some((d) => d.classifications[0].templateId === 't1'),
        )!
        const { startRun, reviewDetection, findRun } = useAnalyses()
        const run = (await startRun('a1', new File(['x'], name, { type: 'image/png' }), { saveScreenshot: false }))!
        const found = findRun('a1', run.id)!.detections!.filter((d) => d.classifications[0].templateId === 't1')
        for (const d of found) await reviewDetection('a1', run.id, d.id, { status: 'validated' })
        expect(correct(await quality())).toBe(before + found.length)
      })

      it('says when the figures cannot be loaded', async () => {
        useSession().setUser('dana')
        const { wrapper } = await mountAt('/catalogue/t1')
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
        await wrapper.get('[data-testid="quality-tab"]').trigger('click')
        await flushPromises()
        expect(wrapper.get('[data-testid="quality"] [role="alert"]').text()).toContain('n’a pas pu être chargée')
      })
    })

    it('outlines the zone of the entity on show, and only that one', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t1')
      expect(wrapper.find('.doc-viewer__polygon--highlight').exists()).toBe(true) // « Emblème » has a zone
      await byTitle(wrapper, 'Entité suivante').trigger('click')
      expect(wrapper.find('.doc-viewer__polygon--highlight').exists()).toBe(false) // « Devise » has none
    })

    it('stars an entity, for the current user only, and takes it back', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t1')
      const star = () => wrapper.get('[data-testid="entity-star"]')
      expect(star().text()).toContain('2') // bob.durand and chloe.petit
      expect(star().attributes('aria-pressed')).toBe('false')
      await star().trigger('click')
      await flushPromises()
      expect(star().text()).toContain('3')
      expect(star().attributes('aria-pressed')).toBe('true')
      await byTitle(wrapper, 'Entité suivante').trigger('click') // the other entity is not starred
      expect(wrapper.get('[data-testid="entity-star"]').attributes('aria-pressed')).toBe('false')
      await byTitle(wrapper, 'Entité précédente').trigger('click')
      await star().trigger('click')
      await flushPromises()
      expect(star().text()).toContain('2')
    })

    it('opens on the suggestions with ?onglet=suggestions, and tells the owner how many wait', async () => {
      useSession().setUser('alice.martin')
      const { wrapper } = await mountAt('/catalogue/t1?onglet=suggestions')
      expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toContain('Suggestions (1)')
      expect(wrapper.get('[role="tablist"]').text()).toContain('1 en attente')
      expect(wrapper.get('[data-testid="suggestion"]').text()).toContain('bob.durand')
      expect(wrapper.get('[data-testid="suggestion"]').text()).toContain('version couleur')
    })

    it('stars a suggestion, for the current user only, and takes it back', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t1?onglet=suggestions')
      const star = () => wrapper.get('[data-testid="suggestion-star"]')
      expect(star().text()).toContain('1') // chloe.petit
      expect(star().attributes('aria-pressed')).toBe('false')
      await star().trigger('click')
      await flushPromises()
      expect(star().text()).toContain('2')
      expect(star().attributes('aria-pressed')).toBe('true')
      await star().trigger('click')
      await flushPromises()
      expect(star().text()).toContain('1')
      expect(star().attributes('aria-pressed')).toBe('false')
    })

    it('only lets the owner decide, but lets anyone comment', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t1?onglet=suggestions')
      expect(wrapper.text()).not.toContain('Accepter')
      expect(wrapper.get('[data-testid="comment"]').text()).toContain('alice.martin') // already one in the demo data
      const send = () => button(wrapper, 'Commenter')
      expect(send().attributes('disabled')).toBeDefined() // nothing to send yet
      await wrapper.get('[data-testid="suggestion"] input').setValue('  Je suis pour.  ')
      expect(send().attributes('disabled')).toBeUndefined()
      await wrapper.get('[data-testid="suggestion"] form').trigger('submit')
      await flushPromises()
      const comments = wrapper.findAll('[data-testid="comment"]')
      expect(comments).toHaveLength(2)
      expect(comments[1].text()).toContain('dana')
      expect(comments[1].text()).toContain('Je suis pour.')
      expect(wrapper.get('[data-testid="suggestion"] input').element.value).toBe('') // ready for the next one
      expect(wrapper.text()).toContain('Commentaires (2)')
    })

    it('says so when there is nothing to show', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/catalogue/t3')
      expect(wrapper.text()).toContain('Aucune entité définie pour ce modèle.')
      expect(wrapper.text()).toContain('Ce modèle n’a pas de document d’exemple.')
      await wrapper.findAll('[role="tab"]')[1].trigger('click')
      expect(wrapper.text()).toContain('Aucune suggestion pour ce modèle.')
    })
  })

  it('lists the analyses as cards, with their total', async () => {
    useSession().setUser('alice')
    const { wrapper } = await mountAt('/analyses')
    expect(wrapper.text()).toContain('Courriers octobre')
    expect(wrapper.text()).toContain('En échec')
    expect(wrapper.findAll('.tile')).toHaveLength(Math.min(analyses.value.length, 6)) // a page of six, with no layout to measure
    expect(wrapper.get('[data-testid="list-total"]').text()).toBe(`${analyses.value.length} analyses au total`)
  })

  it('creates an analysis from catalogue items and lists it first', async () => {
    useSession().setUser('alice')
    await loadAnalyses()
    const before = analyses.value.length
    const { wrapper, router } = await mountAt('/analyses/nouvelle')
    await field(wrapper, 'Nom de l’analyse').setValue('Courriers novembre')
    await wrapper.get('#template-t1').setValue(true)
    await wrapper.get('#template-t4').setValue(true)
    await wrapper.get('form').trigger('submit')
    await landsOn(router, 'analyses')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Courriers novembre'))
    expect(analyses.value).toHaveLength(before + 1)
    expect(analyses.value[0]).toMatchObject({ name: 'Courriers novembre', templateIds: ['t1', 't4'], status: 'running' })
    expect(wrapper.get('[data-testid="list-total"]').text()).toBe(`${before + 1} analyses au total`)
  })

  it('needs a name and at least one catalogue item', async () => {
    useSession().setUser('alice')
    await loadAnalyses()
    const before = analyses.value.length
    const { wrapper, router } = await mountAt('/analyses/nouvelle')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('analysis-new')
    expect(wrapper.text()).toContain('Donnez un nom à l’analyse.')
    expect(wrapper.get('[data-testid="missing"]').text()).toBe('À compléter : le nom, au moins un modèle.')
    expect(analyses.value).toHaveLength(before)
  })

  describe('choosing the models of an analysis', () => {
    const tile = (wrapper: ReturnType<typeof mount>, id: string) => wrapper.get(`#template-${id}`).element.closest('.tile') as HTMLElement
    const box = (wrapper: ReturnType<typeof mount>, id: string) => wrapper.get(`#template-${id}`)
    const picked = (wrapper: ReturnType<typeof mount>) =>
      wrapper.findAll('.tile--selected').map((t) => t.get('label').text())
    const total = (wrapper: ReturnType<typeof mount>) => wrapper.get('[data-testid="list-total"]').text()

    beforeEach(() => {
      // jsdom does not open a dialog: the browser's two methods, in their simplest form.
      HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
        this.setAttribute('open', '')
      }
      HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
        this.removeAttribute('open')
        this.dispatchEvent(new Event('close'))
      }
    })
    afterEach(() => {
      // @ts-expect-error: back to what jsdom has
      delete HTMLDialogElement.prototype.showModal
      // @ts-expect-error: ditto
      delete HTMLDialogElement.prototype.close
    })

    it('shows the models as cards, as the catalogue does, each with its box', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/analyses/nouvelle')
      expect(wrapper.findAll('.tile')).toHaveLength(6) // a page of six, with no layout to measure
      const first = wrapper.get('.tile')
      expect(first.get('label').text()).toBe('Logo Marianne')
      expect(first.get('.tile__description').text()).toBe('Bloc-marque de la République française.')
      expect(first.findAll('.fr-tag').map((t) => t.text())).toEqual(['Identité', 'Officiel'])
      expect(first.text()).toContain('Par alice.martin')
      expect(first.get('input[type="checkbox"]').exists()).toBe(true)
      expect(total(wrapper)).toBe('11 modèles · 0 sélectionné')
    })

    it('picks a model with its box, and lets it go', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/analyses/nouvelle')
      await box(wrapper, 't1').setValue(true)
      expect(tile(wrapper, 't1').classList).toContain('tile--selected')
      expect(total(wrapper)).toBe('11 modèles · 1 sélectionné')
      await box(wrapper, 't2').setValue(true)
      expect(total(wrapper)).toBe('11 modèles · 2 sélectionnés')
      await box(wrapper, 't1').setValue(false)
      expect(picked(wrapper)).toEqual(['Tampon « Reçu »'])
    })

    it('picks a model by clicking anywhere on its card, once, and lets it go the same way', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/analyses/nouvelle')
      await tile(wrapper, 't3').querySelector('.tile__description')!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      await flushPromises()
      expect(picked(wrapper)).toEqual(['Signature type'])
      await tile(wrapper, 't3').querySelector('.tile__description')!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      await flushPromises()
      expect(picked(wrapper)).toEqual([])
    })

    it('leaves the box, its label and the detail button to do their own job, so that a click is one choice and not two', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/analyses/nouvelle')
      // The page is not in a document here, so a click on a label ticks nothing by itself: what is seen is that the card's
      // own handler stays out of it. In a browser the label ticks the box, and the card must not tick it again.
      const click = (el: Element | null) => el!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      click(tile(wrapper, 't3').querySelector('label'))
      click(tile(wrapper, 't3').querySelector('input'))
      click(tile(wrapper, 't3').querySelector('.new-analysis__detail'))
      await flushPromises()
      expect(picked(wrapper)).toEqual([])
      click(tile(wrapper, 't3').querySelector('.tile__tags') ?? tile(wrapper, 't3').querySelector('.tile__description')) // the card itself
      await flushPromises()
      expect(picked(wrapper)).toEqual(['Signature type'])
    })

    it('keeps what is picked through a search, the « mine » filter and a change of page', async () => {
      useSession().setUser('alice.martin')
      const { wrapper } = await mountAt('/analyses/nouvelle')
      await box(wrapper, 't1').setValue(true) // on the first page
      await wrapper.get('input[type="search"]').setValue('tampon')
      expect(wrapper.findAll('.tile').map((t) => t.get('label').text())).toEqual(['Tampon « Reçu »', 'Filigrane « Copie »', 'Cachet de la poste'])
      await box(wrapper, 't7').setValue(true)
      await wrapper.get('input[type="search"]').setValue('')
      await wrapper.findAll('button').find((b) => b.text() === 'Mes modèles')!.trigger('click')
      expect(wrapper.findAll('.tile').map((t) => t.get('label').text())).toEqual(['Logo Marianne', 'Signature type', 'Cachet de la poste', 'Logo CAF'])
      expect(picked(wrapper)).toEqual(['Logo Marianne', 'Cachet de la poste'])
      expect(total(wrapper)).toBe('4 modèles · 2 sélectionnés') // the picks of models not shown are counted too
      await wrapper.findAll('button').find((b) => b.text() === 'Tous')!.trigger('click')
      expect(total(wrapper)).toBe('11 modèles · 2 sélectionnés')
    })

    it('says so when the search, or « mine », shows nothing', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/analyses/nouvelle')
      await wrapper.findAll('button').find((b) => b.text() === 'Mes modèles')!.trigger('click')
      expect(wrapper.text()).toContain('Vous n’avez pas encore de modèle.')
      await wrapper.findAll('button').find((b) => b.text() === 'Tous')!.trigger('click')
      await wrapper.get('input[type="search"]').setValue('zzz')
      expect(wrapper.text()).toContain('Aucun modèle ne correspond à « zzz ».')
    })

    it('creates the analysis with the picks of several searches, in the order of the catalogue', async () => {
      useSession().setUser('alice')
      await loadAnalyses()
      const before = analyses.value.length
      const { wrapper, router } = await mountAt('/analyses/nouvelle')
      await field(wrapper, 'Nom de l’analyse').setValue('Mélange')
      await wrapper.get('input[type="search"]').setValue('qr')
      await box(wrapper, 't4').setValue(true) // picked first, but later in the catalogue
      await wrapper.get('input[type="search"]').setValue('marianne')
      await box(wrapper, 't1').setValue(true)
      await wrapper.get('form').trigger('submit')
      await landsOn(router, 'analyses')
      expect(analyses.value).toHaveLength(before + 1)
      expect(analyses.value[0]).toMatchObject({ name: 'Mélange', templateIds: ['t1', 't4'] })
    })

    describe('describing and sharing the analysis', () => {
      const publicBox = (wrapper: ReturnType<typeof mount>) => wrapper.get('input.fr-toggle__input')
      const shareField = (wrapper: ReturnType<typeof mount>) => wrapper.get('.share input')
      const shareTags = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('.share__tags button').map((b) => b.text())
      const typeShare = async (wrapper: ReturnType<typeof mount>, text: string) => {
        await shareField(wrapper).setValue(text)
        await shareField(wrapper).trigger('keydown.enter')
      }
      /** A form with a name and one model, ready to be sent. */
      async function ready() {
        useSession().setUser('chloe.petit') // of the group « Service contentieux »
        const page = await mountAt('/analyses/nouvelle')
        await field(page.wrapper, 'Nom de l’analyse').setValue('Mon analyse')
        await box(page.wrapper, 't1').setValue(true)
        return page
      }

      it('has the form on one side and the models on the other', async () => {
        useSession().setUser('dana')
        const { wrapper } = await mountAt('/analyses/nouvelle')
        expect(wrapper.get('section[aria-label="Informations sur l’analyse"]').find('textarea').exists()).toBe(true)
        expect(wrapper.get('section[aria-label="Modèles à rechercher"]').findAll('.tile').length).toBeGreaterThan(0)
        expect(wrapper.find('section[aria-label="Informations sur l’analyse"] .tile').exists()).toBe(false)
      })

      it('takes a description, which is optional and kept as typed', async () => {
        const { wrapper, router } = await ready()
        expect(field(wrapper, 'Description').attributes('maxlength')).toBe('300')
        await field(wrapper, 'Description').setValue('  À quoi sert cette analyse.  ')
        await wrapper.get('form').trigger('submit')
        await landsOn(router, 'analyses')
        expect(analyses.value[0]).toMatchObject({ name: 'Mon analyse', description: 'À quoi sert cette analyse.' })
      })

      it('can be made with no description and no recipient', async () => {
        const { wrapper, router } = await ready()
        await wrapper.get('form').trigger('submit')
        await landsOn(router, 'analyses')
        expect(analyses.value[0]).toMatchObject({ description: '', isPublic: false, shares: [] })
      })

      it('is shared with people by e-mail address and with groups by name', async () => {
        const { wrapper, router } = await ready()
        await typeShare(wrapper, 'Marie.Dupont@example.org')
        await typeShare(wrapper, 'service contentieux')
        expect(shareTags(wrapper)).toEqual(['marie.dupont@example.org', 'Service contentieux'])
        await wrapper.get('form').trigger('submit')
        await landsOn(router, 'analyses')
        expect(analyses.value[0].isPublic).toBe(false)
        expect(analyses.value[0].shares).toEqual([
          { kind: 'email', value: 'marie.dupont@example.org' },
          { kind: 'group', value: 'Service contentieux' },
        ])
        await vi.waitFor(() => expect(wrapper.get('[data-testid="sharing"]').text()).toBe('Partagée · 2'))
        expect(wrapper.get('[data-testid="sharing"]').attributes('title')).toContain('1 personne et 1 groupe')
      })

      it('offers the groups of the person, which are the ones the backend gives', async () => {
        const { wrapper } = await ready()
        expect(wrapper.findAll('.share datalist option').map((o) => o.attributes('value'))).toEqual(['Service contentieux'])
      })

      it('takes what was typed in the field when the form is sent, without Enter', async () => {
        const { wrapper, router } = await ready()
        await shareField(wrapper).setValue('paul@example.org')
        await wrapper.get('form').trigger('submit')
        await landsOn(router, 'analyses')
        expect(analyses.value[0].shares).toEqual([{ kind: 'email', value: 'paul@example.org' }])
      })

      it('does not send the form while what was typed is not a recipient, and says so', async () => {
        const { wrapper, router } = await ready()
        const before = analyses.value.length
        await shareField(wrapper).setValue('pas-une-adresse')
        await wrapper.get('form').trigger('submit')
        await flushPromises()
        expect(router.currentRoute.value.name).toBe('analysis-new')
        expect(wrapper.get('[data-testid="missing"]').text()).toBe('À compléter : le destinataire à corriger.')
        expect(wrapper.get('.share [role="alert"]').text()).toContain('n’est ni une adresse e-mail ni un groupe connu')
        expect(analyses.value).toHaveLength(before)
        await shareField(wrapper).setValue('')
        await wrapper.get('form').trigger('submit')
        await landsOn(router, 'analyses')
        expect(analyses.value).toHaveLength(before + 1)
      })

      it('can be public, which leaves the recipients\' field off', async () => {
        const { wrapper } = await ready()
        expect(shareField(wrapper).attributes('disabled')).toBeUndefined()
        await publicBox(wrapper).setValue(true)
        expect(shareField(wrapper).attributes('disabled')).toBeDefined()
        expect(shareField(wrapper).attributes('placeholder')).toBe('Visible par tous')
        expect(wrapper.text()).toContain('Visible par tous les utilisateurs')
      })

      it('is saved as public, with no recipient, and says so in the list', async () => {
        const { wrapper, router } = await ready()
        await typeShare(wrapper, 'marie@example.org')
        await publicBox(wrapper).setValue(true)
        await wrapper.get('form').trigger('submit')
        await landsOn(router, 'analyses')
        expect(analyses.value[0]).toMatchObject({ isPublic: true, shares: [] })
        await vi.waitFor(() => expect(wrapper.get('.tile [data-testid="sharing"]').text()).toBe('Publique'))
      })

      it('keeps the recipients named while it is public, for when it is not after all', async () => {
        const { wrapper } = await ready()
        await typeShare(wrapper, 'marie@example.org')
        await publicBox(wrapper).setValue(true)
        expect(shareTags(wrapper)).toEqual(['marie@example.org'])
        await publicBox(wrapper).setValue(false)
        expect(shareField(wrapper).attributes('disabled')).toBeUndefined()
        expect(shareTags(wrapper)).toEqual(['marie@example.org'])
      })

      it('does not mind what is left in the recipients\' field once public', async () => {
        const { wrapper, router } = await ready()
        await shareField(wrapper).setValue('pas-une-adresse')
        await publicBox(wrapper).setValue(true)
        await wrapper.get('form').trigger('submit')
        await landsOn(router, 'analyses')
        expect(analyses.value[0].isPublic).toBe(true)
      })
    })

    it('says what is missing, one thing at a time', async () => {
      useSession().setUser('dana')
      const { wrapper } = await mountAt('/analyses/nouvelle')
      await box(wrapper, 't1').setValue(true)
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(wrapper.get('[data-testid="missing"]').text()).toBe('À compléter : le nom.')
      await field(wrapper, 'Nom de l’analyse').setValue('Ok')
      await box(wrapper, 't1').setValue(false)
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(wrapper.get('[data-testid="missing"]').text()).toBe('À compléter : au moins un modèle.')
    })

    describe('the detail of a model', () => {
      const detailButton = (wrapper: ReturnType<typeof mount>, id: string) =>
        tile(wrapper, id).querySelector('.new-analysis__detail') as HTMLElement
      const open = async (wrapper: ReturnType<typeof mount>, id: string) => {
        detailButton(wrapper, id).click()
        await flushPromises()
      }

      it('opens over the page, with the model\'s description, document and entities', async () => {
        useSession().setUser('dana')
        const { wrapper } = await mountAt('/analyses/nouvelle')
        expect((wrapper.get('dialog').element as HTMLDialogElement).open).toBe(false)
        await open(wrapper, 't1')
        expect((wrapper.get('dialog').element as HTMLDialogElement).open).toBe(true)
        const preview = wrapper.get('[data-testid="preview"]')
        expect(preview.get('h2').text()).toBe('Logo Marianne')
        expect(preview.get('[data-testid="preview-description"]').text()).toContain('Bloc-marque')
        expect(preview.find('.doc-viewer').exists()).toBe(true)
        expect(preview.get('[data-testid="entity"]').text()).toContain('Emblème')
      })

      it('does not pick the model, nor lose what was filled in, and closes', async () => {
        useSession().setUser('dana')
        const { wrapper } = await mountAt('/analyses/nouvelle')
        await field(wrapper, 'Nom de l’analyse').setValue('Mon analyse')
        await box(wrapper, 't2').setValue(true)
        await open(wrapper, 't1')
        expect(picked(wrapper)).toEqual(['Tampon « Reçu »']) // t1 was looked at, not picked
        await wrapper.get('[data-testid="preview-close"]').trigger('click')
        await flushPromises()
        expect((wrapper.get('dialog').element as HTMLDialogElement).open).toBe(false)
        expect(wrapper.find('[data-testid="preview"]').exists()).toBe(false)
        expect((field(wrapper, 'Nom de l’analyse').element as HTMLInputElement).value).toBe('Mon analyse')
        expect(picked(wrapper)).toEqual(['Tampon « Reçu »'])
      })

      it('shows the model asked for, one after the other', async () => {
        useSession().setUser('dana')
        const { wrapper } = await mountAt('/analyses/nouvelle')
        await open(wrapper, 't2')
        expect(wrapper.get('[data-testid="preview"] h2').text()).toBe('Tampon « Reçu »')
        await wrapper.get('[data-testid="preview-close"]').trigger('click')
        await flushPromises()
        await open(wrapper, 't3')
        expect(wrapper.get('[data-testid="preview"] h2').text()).toBe('Signature type')
      })

      it('shows a star as soon as it is given', async () => {
        useSession().setUser('dana')
        const { wrapper } = await mountAt('/analyses/nouvelle')
        await open(wrapper, 't1')
        const star = () => wrapper.get('[data-testid="preview"] [data-testid="entity-star"]')
        expect(star().text()).toContain('2')
        await star().trigger('click')
        await flushPromises()
        expect(star().text()).toContain('3') // the page follows the catalogue, which holds a new object for the model
      })

      it('is named for a screen reader by the model it is about', async () => {
        useSession().setUser('dana')
        const { wrapper } = await mountAt('/analyses/nouvelle')
        expect(detailButton(wrapper, 't1').textContent).toContain('Voir le détail')
        expect(detailButton(wrapper, 't1').textContent).toContain('de Logo Marianne')
      })
    })
  })
})
