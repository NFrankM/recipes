<template>
    <div class="rz-home">
        <header class="rz-home__head">
            <h1 class="rz-home__title">Rezepte</h1>
            <div class="rz-home__actions">
                <v-menu location="bottom end">
                    <template #activator="{props: p}">
                        <button type="button" class="rz-icon-btn" aria-label="Mehr" v-bind="p"><rz-icon name="more"/></button>
                    </template>
                    <v-list density="comfortable" min-width="230">
                        <v-list-item :to="{name: 'MealPlanPage'}" title="Essensplan"/>
                        <v-list-item :to="{name: 'BooksPage'}" title="Kochbücher"/>
                        <v-list-item :to="{name: 'ShoppingListPage'}" title="Einkaufsliste (Tandoor)"/>
                        <v-list-item :to="{name: 'StartPageTandoor'}" title="Klassische Startseite"/>
                        <v-list-item :to="{name: 'SettingsPage'}" title="Einstellungen"/>
                        <v-list-item :href="logoutUrl" title="Abmelden"/>
                    </v-list>
                </v-menu>
                <v-menu location="bottom end">
                    <template #activator="{props: p}">
                        <button type="button" class="rz-icon-btn rz-icon-btn--accent" aria-label="Rezept hinzufügen" v-bind="p">
                            <rz-icon name="plus"/>
                        </button>
                    </template>
                    <v-list density="comfortable" min-width="230">
                        <v-list-item :to="{name: 'RzImportPage'}" title="Aus dem Internet importieren"/>
                        <v-list-item :to="{name: 'ModelEditPage', params: {model: 'recipe'}}" title="Selbst anlegen"/>
                    </v-list>
                </v-menu>
            </div>
        </header>

        <label class="rz-search">
            <rz-icon name="search" :size="20"/>
            <input v-model="query" type="search" placeholder="Rezepte durchsuchen" enterkeyhint="search" aria-label="Rezepte durchsuchen"/>
            <button v-if="query" type="button" class="rz-search__clear" aria-label="Suche leeren" @click="query = ''"><rz-icon name="x" :size="18"/></button>
        </label>

        <div class="rz-chips" role="tablist">
            <button v-for="c in chips" :key="c.key" type="button" class="rz-chip" :class="{'rz-chip--active': filter === c.key}"
                    role="tab" :aria-selected="filter === c.key" @click="filter = c.key">{{ c.label }}</button>
        </div>

        <div class="rz-grid">
            <router-link v-for="r in recipes" :key="r.id" :to="{name: 'RecipeViewPage', params: {id: r.id}}" class="rz-card">
                <div class="rz-card__img" :style="r.image ? {backgroundImage: `url(${r.image})`} : {}">
                    <span v-if="variantIds.has(r.id)" class="rz-card__badge">Unsere Version</span>
                </div>
                <div class="rz-card__name">{{ r.name }}</div>
                <div class="rz-card__meta">
                    <span v-if="r.time"><rz-icon name="clock" :size="14"/> {{ r.time }} Min.</span>
                    <span v-if="ratings[r.id]?.average"><rz-stars :model-value="ratings[r.id]?.average ?? 0" :size="12"/></span>
                </div>
            </router-link>
        </div>

        <div v-if="loading" class="rz-grid">
            <div v-for="n in 4" :key="n" class="rz-card rz-card--skeleton">
                <div class="rz-card__img"></div>
                <div class="rz-skel-line"></div>
            </div>
        </div>
        <p v-if="!loading && recipes.length === 0" class="rz-empty">
            {{ query || filter !== 'all' ? 'Keine passenden Rezepte gefunden.' : 'Noch keine Rezepte – tippe oben auf + zum Importieren.' }}
        </p>
        <div ref="sentinel" class="rz-sentinel"></div>
    </div>
</template>

<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {ApiApi, ApiRecipeListRequest, Keyword} from '@/openapi'
import {useDjangoUrls} from '@/composables/useDjangoUrls'
import RzIcon from '../components/RzIcon.vue'
import RzStars from '../components/RzStars.vue'
import {rzApi} from '../services/api'
import type {RatingSummary} from '../services/types'

type Card = { id: number, name: string, image: string | null, time: number }

const route = useRoute()
const router = useRouter()
const logoutUrl = useDjangoUrls().getDjangoUrl('accounts/logout')

const query = ref(String(route.query.q ?? ''))
const filter = ref(String(route.query.filter ?? 'all'))
const keywords = ref<Keyword[]>([])
const recipes = ref<Card[]>([])
const ratings = ref<Record<number, RatingSummary>>({})
const variantIds = ref(new Set<number>())
const loading = ref(false)
const page = ref(1)
const hasMore = ref(true)
const sentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null
let requestNo = 0

const chips = computed(() => [
    {key: 'all', label: 'Alle'},
    {key: 'ours', label: 'Unsere Versionen'},
    {key: 'top', label: 'Gut bewertet'},
    {key: 'new', label: 'Neu'},
    ...keywords.value.map(k => ({key: `kw${k.id}`, label: k.label || k.name})),
])

onMounted(() => {
    document.documentElement.classList.add('rz-immersive')
    new ApiApi().apiKeywordList({pageSize: 12}).then(r => keywords.value = r.results ?? []).catch(() => undefined)
    rzApi.allVariants().then(v => variantIds.value = new Set(v.map(x => x.recipe))).catch(() => undefined)
    observer = new IntersectionObserver(entries => {
        if (entries.some(e => e.isIntersecting) && hasMore.value && !loading.value) loadPage()
    }, {rootMargin: '400px'})
    if (sentinel.value) observer.observe(sentinel.value)
    reset()
})
onBeforeUnmount(() => {
    document.documentElement.classList.remove('rz-immersive')
    observer?.disconnect()
})

let timer: ReturnType<typeof setTimeout> | undefined
watch(query, () => {
    clearTimeout(timer)
    timer = setTimeout(reset, 300)
})
watch(filter, reset)

function reset() {
    router.replace({query: {...(query.value ? {q: query.value} : {}), ...(filter.value !== 'all' ? {filter: filter.value} : {})}})
    recipes.value = []
    page.value = 1
    hasMore.value = true
    requestNo++
    loadPage()
}

async function loadPage() {
    const myRequest = requestNo
    loading.value = true
    try {
        let cards: Card[] = []
        if (filter.value === 'ours') {
            // Rezepte mit eigener Version (Haushalt: wenige) einzeln laden
            const variants = await rzApi.allVariants()
            const ids = [...new Set(variants.map(v => v.recipe))].slice(0, 60)
            const api = new ApiApi()
            const list = await Promise.all(ids.map(id => api.apiRecipeRetrieve({id}).catch(() => null)))
            cards = list.filter(r => r && (!query.value || r.name.toLowerCase().includes(query.value.toLowerCase())))
                .map(r => ({id: r!.id!, name: r!.name, image: r!.image, time: (r!.workingTime ?? 0) + (r!.waitingTime ?? 0)}))
            hasMore.value = false
        } else {
            const params: ApiRecipeListRequest = {page: page.value, pageSize: 20}
            if (query.value) params.query = query.value
            if (filter.value === 'top') params.ratingGte = 4
            if (filter.value === 'new') params.sortOrder = '-created_at'
            if (filter.value.startsWith('kw')) params.keywords = [Number(filter.value.slice(2))]
            const r = await new ApiApi().apiRecipeList(params)
            cards = (r.results ?? []).map(x => ({id: x.id!, name: x.name, image: x.image, time: (x.workingTime ?? 0) + (x.waitingTime ?? 0)}))
            hasMore.value = !!r.next
            page.value++
        }
        if (myRequest !== requestNo) return
        recipes.value = recipes.value.concat(cards)
        if (cards.length) {
            rzApi.ratings(cards.map(c => c.id)).then(list => {
                const map = {...ratings.value}
                list.forEach(x => map[x.recipe] = x)
                ratings.value = map
            }).catch(() => undefined)
        }
    } catch {
        hasMore.value = false
    } finally {
        if (myRequest === requestNo) loading.value = false
    }
}
</script>

<style scoped>
.rz-home {
    max-width: 960px;
    margin: 0 auto;
    padding: calc(16px + env(safe-area-inset-top)) 20px 24px;
    background: var(--rz-bg);
}

.rz-home__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.rz-home__title {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--rz-ink);
    margin: 0;
}

.rz-home__actions {
    display: flex;
    gap: 8px;
}

.rz-icon-btn--accent {
    background: var(--rz-accent);
    border-color: var(--rz-accent);
    color: #fff;
}

.rz-search {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 16px;
    height: 48px;
    padding: 0 14px;
    border-radius: var(--rz-radius-field);
    background: var(--rz-surface);
    color: var(--rz-muted);
}

.rz-search input {
    flex: 1;
    min-width: 0;
    border: 0;
    outline: none;
    background: transparent;
    font: inherit;
    font-size: 1rem;
    color: var(--rz-ink);
}

.rz-search input::placeholder {
    color: var(--rz-muted);
}

.rz-search__clear {
    border: 0;
    background: none;
    color: var(--rz-muted);
    width: 36px;
    height: 36px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.rz-chips {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    margin: 14px -20px 0;
    padding: 0 20px 4px;
    scrollbar-width: none;
}

.rz-chips::-webkit-scrollbar {
    display: none;
}

.rz-chip {
    flex-shrink: 0;
    height: 38px;
    padding: 0 16px;
    border-radius: 999px;
    border: 0;
    background: var(--rz-surface);
    color: var(--rz-ink-2);
    font: inherit;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
}

.rz-chip--active {
    background: var(--rz-accent);
    color: #fff;
}

.rz-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 20px 14px;
    margin-top: 20px;
}

@media (min-width: 720px) {
    .rz-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (min-width: 1100px) {
    .rz-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }
}

.rz-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    color: var(--rz-ink);
    text-decoration: none;
    min-width: 0;
}

.rz-card__img {
    position: relative;
    aspect-ratio: 4 / 5;
    border-radius: var(--rz-radius-card);
    background: var(--rz-surface) center / cover no-repeat;
}

.rz-card__badge {
    position: absolute;
    left: 8px;
    bottom: 8px;
    padding: 3px 9px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.92);
    color: var(--rz-accent);
    font-size: 0.6875rem;
    font-weight: 700;
}

.rz-card__name {
    font-weight: 700;
    font-size: 0.9375rem;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.rz-card__meta {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: -4px;
    color: var(--rz-muted);
    font-size: 0.8125rem;
}

.rz-card__meta span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.rz-card--skeleton .rz-card__img {
    animation: rz-pulse 1.2s ease-in-out infinite;
}

.rz-skel-line {
    height: 14px;
    width: 70%;
    border-radius: 7px;
    background: var(--rz-surface);
}

@keyframes rz-pulse {
    50% {
        opacity: .5;
    }
}

.rz-empty {
    text-align: center;
    color: var(--rz-muted);
    padding: 40px 0;
}

.rz-sentinel {
    height: 1px;
}
</style>
