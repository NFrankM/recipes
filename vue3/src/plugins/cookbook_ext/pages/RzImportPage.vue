<template>
    <div class="rz-import">
        <header class="rz-import__head">
            <h1 class="rz-import__title">Importieren</h1>
        </header>

        <!-- Schritt 1: URL -->
        <section v-if="!preview">
            <p class="rz-muted">Link zu einem Rezept einfügen – z. B. aus dem Browser oder einer Koch-App geteilt.</p>
            <label class="rz-url">
                <rz-icon name="link" :size="20"/>
                <input v-model="url" type="url" inputmode="url" placeholder="https://…" aria-label="Rezept-Link" @keyup.enter="load()"/>
                <button v-if="canPaste && !url" type="button" class="rz-url__paste" @click="paste()">
                    <rz-icon name="clipboard" :size="18"/> Einfügen
                </button>
                <button v-else-if="url" type="button" class="rz-url__paste" aria-label="Leeren" @click="url = ''"><rz-icon name="x" :size="18"/></button>
            </label>
            <v-btn block color="primary" size="x-large" class="mt-4" :loading="loading" :disabled="!validUrl" @click="load()">Vorschau laden</v-btn>
            <p v-if="error" class="rz-error">{{ error }}</p>
            <router-link :to="{name: 'RecipeImportPage'}" class="rz-more-link">Weitere Import-Möglichkeiten (Datei, Text, andere Apps)</router-link>
        </section>

        <!-- Schritt 2: Vorschau -->
        <section v-else class="rz-preview">
            <div v-if="preview.duplicates?.length" class="rz-callout">
                <strong>Schon vorhanden?</strong>
                <router-link v-for="d in preview.duplicates" :key="d.id" :to="{name: 'RecipeViewPage', params: {id: d.id}}">{{ d.name }}</router-link>
            </div>

            <div class="rz-preview__img" :style="image ? {backgroundImage: `url(${image})`} : {}"></div>
            <div v-if="(preview.images?.length ?? 0) > 1" class="rz-preview__thumbs">
                <button v-for="i in preview.images!.slice(0, 8)" :key="i" type="button" class="rz-preview__thumb"
                        :class="{'rz-preview__thumb--active': i === image}" :style="{backgroundImage: `url(${i})`}"
                        aria-label="Dieses Bild verwenden" @click="image = i"></button>
            </div>

            <v-text-field v-model="recipe!.name" label="Name" class="mt-4" hide-details="auto"/>
            <div class="rz-preview__meta">
                <span v-if="recipe!.servings"><rz-icon name="users" :size="16"/> {{ recipe!.servings }} {{ recipe!.servingsText || 'Portionen' }}</span>
                <span v-if="time"><rz-icon name="clock" :size="16"/> {{ time }} Min.</span>
                <span>{{ steps.length }} {{ steps.length === 1 ? 'Schritt' : 'Schritte' }}</span>
            </div>

            <div v-if="keywordOptions.length" class="rz-chips">
                <button v-for="k in keywordOptions" :key="k.name" type="button" class="rz-chip" :class="{'rz-chip--active': k.importKeyword}"
                        @click="k.importKeyword = !k.importKeyword">{{ k.label || k.name }}</button>
            </div>

            <h2 class="rz-h2">Zutaten</h2>
            <ul class="rz-preview__ings">
                <li v-for="(i, n) in ingredients" :key="n">{{ i.originalText || [i.amount || '', i.unit?.name, i.food?.name].filter(Boolean).join(' ') }}</li>
            </ul>

            <h2 class="rz-h2">Zubereitung</h2>
            <ol class="rz-preview__steps">
                <li v-for="(s, n) in steps" :key="n">{{ s.instruction }}</li>
            </ol>

            <div class="rz-preview__actions">
                <v-btn block color="primary" size="x-large" :loading="saving" @click="save()">Rezept speichern</v-btn>
                <v-btn block variant="outlined" size="large" :disabled="saving" @click="preview = null">Abbrechen</v-btn>
            </div>
            <p v-if="error" class="rz-error">{{ error }}</p>
        </section>
    </div>
</template>

<script setup lang="ts">
/**
 * Vereinfachter Import: URL → Vorschau → speichern.
 * Nutzt Tandoors vorhandenen Import (/api/recipe-from-source/, ld+json/microdata) – hier wird nichts neu geparst.
 * Für alle anderen Import-Arten verlinkt die Seite auf Tandoors Import (RecipeImportPage).
 */
import {computed, onBeforeUnmount, onMounted, ref} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {ApiApi, Recipe, RecipeFromSourceResponse} from '@/openapi'
import {useFileApi} from '@/composables/useFileApi'
import RzIcon from '../components/RzIcon.vue'

const route = useRoute()
const router = useRouter()
const {updateRecipeImage} = useFileApi()

const url = ref(String(route.query.url ?? ''))
const preview = ref<RecipeFromSourceResponse | null>(null)
const image = ref<string | undefined>()
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const canPaste = typeof navigator !== 'undefined' && !!navigator.clipboard?.readText

const validUrl = computed(() => /^https?:\/\/\S+\.\S+/.test(url.value.trim()))
const recipe = computed(() => preview.value?.recipe)
const steps = computed(() => recipe.value?.steps ?? [])
const ingredients = computed(() => steps.value.flatMap(s => s.ingredients ?? []))
const keywordOptions = computed(() => recipe.value?.keywords ?? [])
const time = computed(() => (recipe.value?.workingTime ?? 0) + (recipe.value?.waitingTime ?? 0))

onMounted(() => {
    document.documentElement.classList.add('rz-immersive')
    if (validUrl.value) load()  // z. B. über ?url=… (Teilen-Funktion)
})

onBeforeUnmount(() => document.documentElement.classList.remove('rz-immersive'))

async function paste() {
    try {
        url.value = (await navigator.clipboard.readText()).trim()
    } catch {
        error.value = 'Zugriff auf die Zwischenablage nicht erlaubt – bitte lange tippen und „Einfügen“ wählen.'
    }
}

async function load() {
    if (!validUrl.value) return
    loading.value = true
    error.value = ''
    try {
        const r = await new ApiApi().apiRecipeFromSourceCreate({recipeFromSource: {url: url.value.trim()}})
        if (r.recipeId != null) {
            // Tandoor hat das Rezept direkt angelegt (z. B. Tandoor-Share-Link)
            router.push({name: 'RecipeViewPage', params: {id: r.recipeId}})
            return
        }
        if (r.error || !r.recipe) {
            error.value = r.msg || 'Auf dieser Seite wurde kein Rezept gefunden.'
            return
        }
        // Schlagwörter standardmäßig übernehmen, die es schon gibt
        r.recipe.keywords?.forEach(k => k.importKeyword = k.importKeyword ?? !!k.id)
        image.value = r.recipe.imageUrl || r.images?.[0]
        preview.value = r
    } catch (e: any) {
        const body = await e?.response?.json?.().catch(() => null)
        error.value = body?.msg || 'Die Seite konnte nicht geladen werden. Ist der Link richtig?'
    } finally {
        loading.value = false
    }
}

async function save() {
    if (!recipe.value) return
    saving.value = true
    error.value = ''
    try {
        const data = {...recipe.value, keywords: (recipe.value.keywords ?? []).filter(k => k.importKeyword)}
        const created = await new ApiApi().apiRecipeCreate({recipe: data as unknown as Recipe})
        if (image.value) await updateRecipeImage(created.id!, null, image.value).catch(() => undefined)
        router.push({name: 'RecipeViewPage', params: {id: created.id!}})
    } catch {
        error.value = 'Speichern fehlgeschlagen.'
    } finally {
        saving.value = false
    }
}
</script>

<style scoped>
.rz-import {
    max-width: 720px;
    margin: 0 auto;
    padding: calc(16px + env(safe-area-inset-top)) 20px 32px;
}

.rz-import__title {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--rz-ink);
    margin: 0 0 8px;
}

.rz-muted {
    color: var(--rz-muted);
}

.rz-url {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 52px;
    margin-top: 12px;
    padding: 0 8px 0 14px;
    border-radius: var(--rz-radius-field);
    background: var(--rz-surface);
    color: var(--rz-muted);
}

.rz-url input {
    flex: 1;
    min-width: 0;
    border: 0;
    outline: none;
    background: transparent;
    font: inherit;
    font-size: 1rem;
    color: var(--rz-ink);
}

.rz-url__paste {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 40px;
    padding: 0 10px;
    border: 0;
    border-radius: 10px;
    background: var(--rz-bg);
    color: var(--rz-accent);
    font: inherit;
    font-weight: 600;
}

.rz-error {
    color: rgb(var(--v-theme-error));
    margin-top: 12px;
}

.rz-more-link {
    display: block;
    margin-top: 28px;
    color: var(--rz-muted);
    font-size: 0.875rem;
}

.rz-callout {
    display: flex;
    flex-direction: column;
    gap: 4px;
    background: var(--rz-surface-soft);
    border-radius: var(--rz-radius-card);
    padding: 14px 16px;
    margin-bottom: 16px;
}

.rz-callout a {
    color: var(--rz-accent);
    font-weight: 600;
}

.rz-preview__img {
    aspect-ratio: 4 / 3;
    border-radius: var(--rz-radius-card);
    background: var(--rz-surface) center / cover no-repeat;
}

.rz-preview__thumbs {
    display: flex;
    gap: 8px;
    margin-top: 10px;
    overflow-x: auto;
}

.rz-preview__thumb {
    flex: 0 0 56px;
    height: 56px;
    border-radius: 10px;
    border: 2px solid transparent;
    background: var(--rz-surface) center / cover no-repeat;
}

.rz-preview__thumb--active {
    border-color: var(--rz-accent);
}

.rz-preview__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 16px;
    margin-top: 12px;
    color: var(--rz-muted);
    font-size: 0.875rem;
}

.rz-preview__meta span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.rz-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
}

.rz-chip {
    height: 34px;
    padding: 0 14px;
    border-radius: 999px;
    border: 0;
    background: var(--rz-surface);
    color: var(--rz-muted);
    font: inherit;
    font-size: 0.8125rem;
    font-weight: 600;
}

.rz-chip--active {
    background: var(--rz-accent);
    color: #fff;
}

.rz-h2 {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--rz-ink);
    margin: 24px 0 8px;
}

.rz-preview__ings {
    list-style: none;
    padding: 0;
    margin: 0;
}

.rz-preview__ings li {
    padding: 10px 0;
    border-bottom: 1px solid var(--rz-border);
    font-size: 0.9375rem;
}

.rz-preview__steps {
    padding-left: 22px;
    margin: 0;
    color: var(--rz-ink-2);
    font-size: 0.9375rem;
    line-height: 1.55;
}

.rz-preview__steps li {
    margin-bottom: 10px;
    padding: 0;
}

.rz-preview__actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 24px;
}
</style>
