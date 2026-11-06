import {computed, ref} from 'vue'
import {rzApi} from './api'
import type {Category} from './types'

/**
 * Gemeinsamer Zustand der Kategorien (einmal laden, überall nutzen: Startseite, Rezept, Import, Kategorien-Seite).
 */
const list = ref<Category[]>([])
const loaded = ref(false)
let pending: Promise<Category[]> | null = null

export function useCategories() {
    function reload() {
        pending = rzApi.categories().then(c => {
            list.value = c
            loaded.value = true
            return c
        }).finally(() => pending = null)
        return pending
    }

    function ensure() {
        if (loaded.value) return Promise.resolve(list.value)
        return pending ?? reload()
    }

    async function create(name: string) {
        const c = await rzApi.createCategory(name)
        await reload()
        return c
    }

    const ids = computed(() => new Set(list.value.map(c => c.id)))

    return {categories: list, loaded, ids, ensure, reload, create}
}
