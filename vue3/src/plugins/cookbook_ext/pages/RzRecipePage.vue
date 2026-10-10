<template>
    <div class="rz-recipe">
        <!-- Foto -->
        <div class="rz-hero" :style="recipe?.image ? {backgroundImage: `url(${recipe.image})`} : {}">
            <div class="rz-hero__bar">
                <button type="button" class="rz-icon-btn" aria-label="Zurück" @click="goBack()">
                    <rz-icon name="arrow-left"/>
                </button>
                <v-menu location="bottom end">
                    <template #activator="{props: p}">
                        <button type="button" class="rz-icon-btn" aria-label="Mehr" v-bind="p">
                            <rz-icon name="more"/>
                        </button>
                    </template>
                    <v-list density="comfortable" min-width="240">
                        <v-list-item v-if="canWrite" :to="{name: 'ModelEditPage', params: {model: 'recipe', id: id}}" title="Original bearbeiten"/>
                        <v-list-item :to="{name: 'RecipeViewPageTandoor', params: {id: id}}" title="Klassische Ansicht"/>
                        <v-list-item v-if="canWrite && currentVariant" title="„Unsere Version“ löschen" @click="confirmDelete = true"/>
                    </v-list>
                </v-menu>
            </div>
        </div>

        <!-- Sheet über dem Foto -->
        <main class="rz-sheet-main">
            <div v-if="loadError" class="rz-empty">
                <p>{{ loadError }}</p>
                <v-btn variant="outlined" @click="load()">Erneut versuchen</v-btn>
            </div>

            <template v-else-if="recipe">
                <h1 class="rz-title">{{ recipe.name }}</h1>

                <div class="rz-meta">
                    <span v-if="totalTime" class="rz-meta__item"><rz-icon name="clock" :size="18"/>{{ formatMinutes(totalTime) }}</span>
                    <a v-if="rating && rating.count" href="#rz-bewertungen" class="rz-meta__item rz-meta__rating">
                        <rz-stars :model-value="rating.average ?? 0" :size="16"/>
                        <span>{{ rating.count }} {{ rating.count === 1 ? 'Bewertung' : 'Bewertungen' }}</span>
                    </a>
                </div>

                <div v-if="recipe.keywords?.length" class="rz-tags">
                    <span v-for="k in recipe.keywords" :key="k.id" class="rz-tag">{{ k.label || k.name }}</span>
                </div>

                <p v-if="recipe.description" class="rz-desc">{{ recipe.description }}</p>

                <rz-segment v-model="mode" :options="modeOptions" class="rz-block"/>

                <!-- Noch keine eigene Version -->
                <div v-if="mode === 'ours' && !currentVariant" class="rz-callout rz-block">
                    <p class="rz-callout__title">Noch keine eigene Version</p>
                    <p class="rz-muted">Ändere Zutaten und Mengen oder ergänze Notizen – das Original bleibt erhalten.</p>
                    <v-btn v-if="canWrite" color="primary" size="large" block :loading="creating" @click="createVariant()">
                        „Unsere Version“ anlegen
                    </v-btn>
                </div>

                <template v-else>
                    <!-- Portionen -->
                    <div class="rz-servings rz-block">
                        <span class="rz-servings__label">
                            <rz-icon name="users" :size="20"/>
                            {{ recipe.servingsText || 'Portionen' }}
                        </span>
                        <rz-stepper v-model="servings" :label="recipe.servingsText || 'Portionen'"/>
                    </div>

                    <!-- Zutaten -->
                    <div class="rz-section-head">
                        <h2 class="rz-h2">Zutaten</h2>
                        <v-btn v-if="currentVariant && canWrite" variant="text" size="default" @click="editing = !editing">
                            <rz-icon :name="editing ? 'check' : 'pencil'" :size="18" class="me-2"/>
                            {{ editing ? 'Fertig' : 'Anpassen' }}
                        </v-btn>
                    </div>
                    <p v-if="editing" class="rz-edit-hint">Tippe auf eine Zutat oder einen Schritt, um ihn für „Unsere Version“ zu ändern.</p>
                    <p v-if="editing && orphanCount" class="rz-edit-hint rz-edit-hint--warn">
                        {{ orphanCount }} Änderung(en) beziehen sich auf Zutaten/Schritte, die es im Original nicht mehr gibt.
                    </p>

                    <div :class="{'rz-loading': loadingEffective}">
                        <rz-ingredient-list v-if="effective" :steps="effective.steps" :editable="editing"
                                            @select="openIngredient" @add="openIngredient(null, null)"/>
                    </div>

                    <v-btn color="primary" size="x-large" block class="rz-block rz-shop-btn" :loading="shopping" @click="addToShopping()">
                        <rz-icon name="cart" class="me-2"/>
                        Auf die Einkaufsliste
                    </v-btn>

                    <v-btn variant="outlined" size="large" block class="mt-3" :disabled="!effective?.steps.length"
                           :to="{name: 'RzCookPage', params: {id: id}, query: {servings: String(servings), ...(mode === 'ours' && currentVariant ? {variant: String(currentVariant.id)} : {})}}">
                        <rz-icon name="pot" class="me-2"/>
                        Kochmodus
                    </v-btn>

                    <!-- Schritte -->
                    <h2 class="rz-h2 rz-block">Zubereitung</h2>
                    <ol class="rz-steps">
                        <li v-for="(s, idx) in effective?.steps ?? []" :key="s.id ?? `n${s.added_note?.id}`" class="rz-step"
                            :class="{'rz-step--editable': editing}">
                            <component :is="editing ? 'button' : 'div'" class="rz-step__inner" :type="editing ? 'button' : undefined"
                                       @click="editing && openStep(s, idx)">
                                <span class="rz-step__num" :class="{'rz-step__num--added': s.is_added}">{{ idx + 1 }}</span>
                                <div class="rz-step__body">
                                    <div class="rz-step__top">
                                        <strong v-if="s.name" class="rz-step__name">{{ s.name }}</strong>
                                        <span v-if="s.is_added" class="rz-badge rz-badge--outline">ergänzt</span>
                                        <span v-if="s.time" class="rz-step__time"><rz-icon name="timer" :size="16"/>{{ formatMinutes(s.time) }}</span>
                                    </div>
                                    <instructions v-if="s.instructions_markdown" class="rz-step__text" :instructions_html="s.instructions_markdown"
                                                  :ingredient_factor="effective?.factor ?? 1"/>
                                    <p v-else class="rz-step__text">{{ s.instruction }}</p>
                                    <div v-for="n in s.notes" :key="n.id" class="rz-note">
                                        <span class="rz-note__label"><rz-icon name="note" :size="16"/>Unsere Notiz</span>
                                        <p>{{ n.text }}</p>
                                    </div>
                                </div>
                            </component>
                        </li>
                    </ol>
                </template>

                <rz-reviews id="rz-bewertungen" ref="reviews" class="rz-block" :recipe-id="Number(id)" :servings="servings"
                            :can-write="canWrite" @changed="loadRating()"/>

                <div class="rz-footer-links">
                    <router-link :to="{name: 'RecipeViewPageTandoor', params: {id: id}}">Klassische Ansicht</router-link>
                    <a v-if="recipe.sourceUrl" :href="recipe.sourceUrl" target="_blank" rel="noopener">Quelle <rz-icon name="external" :size="14"/></a>
                </div>
            </template>

            <div v-else class="rz-skeleton">
                <v-skeleton-loader type="heading, paragraph, list-item-two-line@4"/>
            </div>
        </main>

        <rz-ingredient-sheet v-if="currentVariant && effective" v-model="ingredientSheet" :variant-id="currentVariant.id"
                             :ingredient="selectedIngredient" :steps="effective.steps" :default-step-id="selectedStepId"
                             :factor="effective.factor" :servings="effective.servings" @saved="afterEdit()"/>
        <rz-step-sheet v-if="currentVariant" v-model="stepSheet" :variant-id="currentVariant.id" :step="selectedStep"
                       :original-index="selectedOriginalIndex" :number="selectedNumber" @saved="afterEdit()"/>

        <v-dialog v-model="confirmDelete" max-width="420">
            <v-card>
                <v-card-title>„Unsere Version“ löschen?</v-card-title>
                <v-card-text>Alle Änderungen und Notizen dieser Version gehen verloren. Das Original bleibt erhalten.</v-card-text>
                <div class="d-flex ga-2 pa-4">
                    <v-btn variant="outlined" class="flex-grow-1" @click="confirmDelete = false">Abbrechen</v-btn>
                    <v-btn color="error" class="flex-grow-1" :loading="creating" @click="deleteVariant()">Löschen</v-btn>
                </div>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import {computed, nextTick, onBeforeUnmount, onMounted, ref, watch} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {useTitle} from '@vueuse/core'
import {ApiApi, Recipe, ViewLog} from '@/openapi'
// @ts-ignore Tandoor-Komponente ohne Typen (Options-API, JS)
import Instructions from '@/components/display/Instructions.vue'
import {useUserPreferenceStore} from '@/stores/UserPreferenceStore'
import {MessageType, useMessageStore} from '@/stores/MessageStore'
import RzIcon from '../components/RzIcon.vue'
import RzStars from '../components/RzStars.vue'
import RzSegment from '../components/RzSegment.vue'
import RzStepper from '../components/RzStepper.vue'
import RzIngredientList from '../components/RzIngredientList.vue'
import RzIngredientSheet from '../components/RzIngredientSheet.vue'
import RzStepSheet from '../components/RzStepSheet.vue'
import RzReviews from '../components/RzReviews.vue'
import {rzApi} from '../services/api'
import {formatMinutes} from '../services/format'
import type {EffectiveIngredient, EffectiveRecipe, EffectiveStep, RatingSummary, RecipeVariant} from '../services/types'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()
const title = useTitle()
const prefs = useUserPreferenceStore()

const recipe = ref<Recipe | null>(null)
const variants = ref<RecipeVariant[]>([])
const effective = ref<EffectiveRecipe | null>(null)
const rating = ref<RatingSummary | null>(null)
const mode = ref<'original' | 'ours'>('original')
const servings = ref(1)
const editing = ref(false)
const loadError = ref('')
const loadingEffective = ref(false)
const creating = ref(false)
const shopping = ref(false)
const confirmDelete = ref(false)

const ingredientSheet = ref(false)
const selectedIngredient = ref<EffectiveIngredient | null>(null)
const selectedStepId = ref<number | null>(null)
const stepSheet = ref(false)
const selectedStep = ref<EffectiveStep | null>(null)
const selectedOriginalIndex = ref(0)
const selectedNumber = ref(1)

const currentVariant = computed(() => variants.value.find(v => v.is_default) ?? variants.value[0] ?? null)
const modeOptions = computed(() => [
    {value: 'original', label: 'Original'},
    {value: 'ours', label: currentVariant.value?.name ?? 'Unsere Version'},
])
const totalTime = computed(() => (recipe.value?.workingTime ?? 0) + (recipe.value?.waitingTime ?? 0))
const orphanCount = computed(() => (effective.value?.orphaned_changes.length ?? 0) + (effective.value?.orphaned_notes.length ?? 0))
const canWrite = computed(() => {
    if (prefs.userSettings?.user?.isSuperuser) return true
    const groups = prefs.activeUserSpace?.groups ?? []
    return groups.some(g => g.name === 'user' || g.name === 'admin')
})

onMounted(() => {
    document.documentElement.classList.add('rz-immersive')
    // geteilte Links und nicht angemeldete Besucher: Tandoors Ansicht (kann Share-Links)
    if (route.query.share || !prefs.isAuthenticated) {
        router.replace({name: 'RecipeViewPageTandoor', params: {id: props.id}, query: route.query})
        return
    }
    load()
})
onBeforeUnmount(() => document.documentElement.classList.remove('rz-immersive'))
watch(() => props.id, () => load())

let effectiveTimer: ReturnType<typeof setTimeout> | undefined
let initializing = false
watch([mode, servings], () => {
    if (mode.value === 'original') editing.value = false
    if (initializing) return
    clearTimeout(effectiveTimer)
    effectiveTimer = setTimeout(loadEffective, 120)
})

async function load() {
    loadError.value = ''
    recipe.value = null
    effective.value = null
    editing.value = false
    const api = new ApiApi()
    try {
        const [r, v] = await Promise.all([api.apiRecipeRetrieve({id: Number(props.id)}), rzApi.variants(Number(props.id))])
        recipe.value = r
        variants.value = v
        title.value = r.name
        initializing = true
        const qServings = Number(route.query.servings)
        servings.value = qServings > 0 ? qServings : (r.servings || 1)
        mode.value = route.query.version === 'original' || !currentVariant.value ? 'original' : 'ours'
        await nextTick()
        initializing = false
        await loadEffective()
        loadRating()
        api.apiViewLogCreate({viewLog: {recipe: Number(props.id)} as ViewLog}).catch(() => undefined)
    } catch (e: any) {
        const status = e?.response?.status ?? e?.status
        loadError.value = status === 404 || status === 403 ? 'Dieses Rezept gibt es nicht oder du darfst es nicht sehen.' : 'Das Rezept konnte nicht geladen werden.'
    }
}

async function loadEffective() {
    if (!recipe.value) return
    const variantId = mode.value === 'ours' ? currentVariant.value?.id ?? null : null
    if (mode.value === 'ours' && variantId === null) {
        effective.value = null
        return
    }
    loadingEffective.value = true
    try {
        effective.value = await rzApi.effective(recipe.value.id!, variantId, servings.value)
    } catch (e: any) {
        useMessageStore().addMessage(MessageType.ERROR, e?.message ?? 'Laden fehlgeschlagen')
    } finally {
        loadingEffective.value = false
    }
}

function loadRating() {
    rzApi.ratings([Number(props.id)]).then(r => rating.value = r[0] ?? null).catch(() => undefined)
}

async function createVariant() {
    creating.value = true
    try {
        const v = await rzApi.createVariant(Number(props.id))
        variants.value = [v, ...variants.value.map(x => ({...x, is_default: false}))]
        await loadEffective()
        editing.value = true
    } catch (e: any) {
        useMessageStore().addMessage(MessageType.ERROR, e?.message ?? 'Anlegen fehlgeschlagen')
    } finally {
        creating.value = false
    }
}

async function deleteVariant() {
    if (!currentVariant.value) return
    creating.value = true
    try {
        await rzApi.deleteVariant(currentVariant.value.id)
        variants.value = variants.value.filter(v => v.id !== currentVariant.value?.id)
        confirmDelete.value = false
        mode.value = 'original'
    } finally {
        creating.value = false
    }
}

function openIngredient(i: EffectiveIngredient | null, step: EffectiveStep | null) {
    selectedIngredient.value = i
    selectedStepId.value = step?.id ?? null
    ingredientSheet.value = true
}

function openStep(s: EffectiveStep, idx: number) {
    selectedStep.value = s
    selectedNumber.value = idx + 1
    // Index des (letzten) Original-Schritts bis einschließlich dieser Position
    const steps = effective.value?.steps ?? []
    let originalIndex = -1
    for (let i = 0; i <= idx; i++) if (!steps[i]?.is_added) originalIndex++
    selectedOriginalIndex.value = Math.max(0, originalIndex)
    stepSheet.value = true
}

async function afterEdit() {
    variants.value = await rzApi.variants(Number(props.id))
    await loadEffective()
}

async function addToShopping() {
    if (!effective.value || !recipe.value) return
    shopping.value = true
    try {
        if (mode.value === 'ours' && currentVariant.value) {
            const r = await rzApi.variantToShopping(currentVariant.value.id, servings.value)
            useMessageStore().addMessage(MessageType.SUCCESS, r.msg, 4000)
        } else {
            const ids = effective.value.steps.flatMap(s => s.ingredients).filter(i => !i.is_header && i.ingredient).map(i => i.ingredient!)
            await new ApiApi().apiRecipeShoppingUpdate({id: recipe.value.id!, recipeShoppingUpdate: {servings: servings.value, ingredients: ids}})
            useMessageStore().addMessage(MessageType.SUCCESS, `${recipe.value.name} wurde auf die Einkaufsliste gesetzt.`, 4000)
        }
    } catch (e: any) {
        useMessageStore().addMessage(MessageType.ERROR, e?.message ?? 'Einkaufsliste konnte nicht ergänzt werden')
    } finally {
        shopping.value = false
    }
}

function goBack() {
    if (window.history.length > 1) router.back()
    else router.push({name: 'StartPage'})
}
</script>

<style scoped>
.rz-recipe {
    background: var(--rz-bg);
    min-height: 100%;
}

.rz-hero {
    position: relative;
    height: min(46vh, 440px);
    background: var(--rz-surface) center / cover no-repeat;
}

.rz-hero__bar {
    position: absolute;
    top: calc(12px + env(safe-area-inset-top));
    left: 16px;
    right: 16px;
    display: flex;
    justify-content: space-between;
}

.rz-sheet-main {
    position: relative;
    margin: -24px auto 0;
    max-width: 760px;
    background: var(--rz-bg);
    border-radius: var(--rz-radius-sheet) var(--rz-radius-sheet) 0 0;
    padding: 24px 20px 40px;
}

.rz-title {
    font-size: 1.75rem;
    line-height: 1.2;
    font-weight: 700;
    letter-spacing: -0.015em;
    color: var(--rz-ink);
    margin: 0;
}

.rz-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 16px;
    margin-top: 10px;
    color: var(--rz-muted);
    font-size: 0.875rem;
}

.rz-meta__item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: inherit;
    text-decoration: none;
}

.rz-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
}

.rz-tag {
    display: inline-flex;
    align-items: center;
    height: 30px;
    padding: 0 12px;
    border-radius: 999px;
    background: var(--rz-surface);
    color: var(--rz-ink-2);
    font-size: 0.8125rem;
    font-weight: 500;
}

.rz-desc {
    margin: 14px 0 0;
    color: var(--rz-ink-2);
    font-size: 0.9375rem;
    line-height: 1.5;
}

.rz-block {
    margin-top: 24px;
}

.rz-callout {
    background: var(--rz-surface-soft);
    border-radius: var(--rz-radius-card);
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.rz-callout p {
    margin: 0;
}

.rz-callout__title {
    font-weight: 700;
    color: var(--rz-ink);
}

.rz-servings {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.rz-servings__label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: var(--rz-ink);
}

.rz-section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 28px;
    min-height: 44px;
}

.rz-h2, :deep(.rz-h2) {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--rz-ink);
    margin: 0;
}

.rz-h2.rz-block {
    margin-top: 32px;
}

.rz-edit-hint {
    background: var(--rz-surface-soft);
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 0.875rem;
    color: var(--rz-ink-2);
    margin: 8px 0;
}

.rz-edit-hint--warn {
    color: rgb(var(--v-theme-warning));
}

.rz-loading {
    opacity: .55;
    transition: opacity .15s;
}

.rz-shop-btn {
    height: 52px !important;
}

.rz-steps {
    list-style: none;
    padding: 0;
    margin: 8px 0 0;
}

.rz-step__inner {
    display: flex;
    gap: 14px;
    width: 100%;
    padding: 14px 0;
    border: 0;
    background: none;
    text-align: left;
    font: inherit;
    color: inherit;
}

.rz-step--editable .rz-step__inner {
    cursor: pointer;
    border-radius: 12px;
}

.rz-step--editable .rz-step__inner:active {
    background: var(--rz-surface-soft);
}

.rz-step__num {
    flex: 0 0 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--rz-surface);
    color: var(--rz-accent);
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.rz-step__num--added {
    background: transparent;
    border: 1.5px dashed var(--rz-accent);
}

.rz-step__body {
    flex: 1;
    min-width: 0;
}

.rz-step__top {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    min-height: 32px;
}

.rz-step__name {
    color: var(--rz-ink);
}

.rz-step__time {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.8125rem;
    color: var(--rz-muted);
}

.rz-step__text {
    margin: 4px 0 0;
    color: var(--rz-ink-2);
    font-size: 0.9375rem;
    line-height: 1.55;
}

.rz-step__text :deep(p) {
    margin: 0 0 0.5em;
    padding: 0;
}

.rz-note {
    margin-top: 10px;
    background: var(--rz-surface-soft);
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 0.875rem;
    color: var(--rz-ink-2);
}

.rz-note p {
    margin: 4px 0 0;
}

.rz-note__label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-weight: 700;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: .04em;
    color: var(--rz-accent);
}

.rz-badge {
    display: inline-flex;
    align-items: center;
    height: 22px;
    padding: 0 9px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid var(--rz-accent);
}

.rz-badge--outline {
    color: var(--rz-accent);
}

.rz-muted, :deep(.rz-muted) {
    color: var(--rz-muted);
}

.rz-footer-links {
    display: flex;
    gap: 20px;
    margin-top: 32px;
    font-size: 0.875rem;
}

.rz-footer-links a {
    color: var(--rz-muted);
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.rz-empty {
    text-align: center;
    padding: 40px 0;
    color: var(--rz-muted);
}
</style>
