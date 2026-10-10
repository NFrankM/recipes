<template>
    <div class="rz-shop">
        <header class="rz-shop__head">
            <div>
                <h1 class="rz-shop__title">Einkauf</h1>
                <p class="rz-muted">{{ openCount === 0 ? 'Alles erledigt' : `${openCount} ${openCount === 1 ? 'Artikel' : 'Artikel'} offen` }}</p>
            </div>
            <v-menu location="bottom end">
                <template #activator="{props: p}">
                    <button type="button" class="rz-icon-btn" aria-label="Mehr" v-bind="p"><rz-icon name="more"/></button>
                </template>
                <v-list density="comfortable" min-width="250">
                    <v-list-item :title="showDone ? 'Erledigte ausblenden' : 'Erledigte anzeigen'" @click="showDone = !showDone"/>
                    <v-list-item title="Neu laden" @click="load()"/>
                    <v-list-item :to="{name: 'ShoppingListPage'}" title="Tandoor-Einkaufsliste (Supermärkte, Listen)"/>
                </v-list>
            </v-menu>
        </header>

        <form class="rz-add" @submit.prevent="add()">
            <input v-model="newItem" type="text" placeholder="z. B. 2 Zitronen" aria-label="Artikel hinzufügen" enterkeyhint="done"/>
            <button type="submit" class="rz-icon-btn rz-icon-btn--accent" :disabled="!newItem.trim() || adding" aria-label="Hinzufügen">
                <rz-icon name="plus"/>
            </button>
        </form>

        <div v-if="recipes.length" class="rz-shop__recipes">
            <span v-for="r in recipes" :key="r.id" class="rz-recipe-chip">
                <router-link v-if="r.recipeId" :to="{name: 'RecipeViewPage', params: {id: r.recipeId}}">{{ r.label }}</router-link>
                <span v-else>{{ r.label }}</span>
                <button type="button" :aria-label="`${r.label} von der Liste nehmen`" @click="removeRecipe(r.id)"><rz-icon name="x" :size="14"/></button>
            </span>
        </div>

        <section v-for="g in groups" :key="g.name" class="rz-group">
            <h2 class="rz-group__title">{{ g.name }}</h2>
            <button v-for="row in g.rows" :key="row.key" type="button" class="rz-item" :class="{'rz-item--done': row.checked}"
                    :aria-pressed="row.checked" @click="toggle(row)">
                <span class="rz-check" :class="{'rz-check--on': row.checked}"><rz-icon v-if="row.checked" name="check" :size="16" :stroke-width="2.5"/></span>
                <span class="rz-item__main">
                    <span class="rz-item__name">{{ row.name }}</span>
                    <span v-if="row.sources" class="rz-item__src">{{ row.sources }}</span>
                </span>
                <span class="rz-item__amount">{{ row.amountText }}</span>
            </button>
        </section>

        <section v-if="showDone && doneRows.length" class="rz-group">
            <h2 class="rz-group__title">Erledigt</h2>
            <button v-for="row in doneRows" :key="row.key" type="button" class="rz-item rz-item--done" @click="toggle(row)">
                <span class="rz-check rz-check--on"><rz-icon name="check" :size="16" :stroke-width="2.5"/></span>
                <span class="rz-item__main"><span class="rz-item__name">{{ row.name }}</span></span>
                <span class="rz-item__amount">{{ row.amountText }}</span>
            </button>
        </section>

        <p v-if="!loading && entries.length === 0" class="rz-empty">Die Einkaufsliste ist leer. Rezepte kommen über „Auf die Einkaufsliste“ hierher.</p>
    </div>
</template>

<script setup lang="ts">
/**
 * Schlanke Einkaufsliste im Rezept-App-Design auf Basis von Tandoors Einkaufslisten-Einträgen:
 * gleiche Lebensmittel+Einheit aus mehreren Rezepten werden zusammengefasst, Gruppierung nach Supermarkt-Kategorie,
 * Antippen hakt ab (alle zusammengefassten Einträge auf einmal). Tandoors volle Einkaufsliste bleibt unter /shopping.
 */
import {computed, onBeforeUnmount, onMounted, ref} from 'vue'
import {ApiApi, ShoppingListEntry} from '@/openapi'
import {MessageType, useMessageStore} from '@/stores/MessageStore'
import RzIcon from '../components/RzIcon.vue'
import {formatAmount} from '../services/format'

type Row = { key: string, name: string, amountText: string, sources: string, checked: boolean, ids: number[], category: string }

const entries = ref<ShoppingListEntry[]>([])
const loading = ref(false)
const showDone = ref(true)
const newItem = ref('')
const adding = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | undefined

onMounted(() => {
    load()
    refreshTimer = setInterval(() => document.visibilityState === 'visible' && load(true), 30000)
    document.addEventListener('visibilitychange', onVisible)
})
onBeforeUnmount(() => {
    clearInterval(refreshTimer)
    document.removeEventListener('visibilitychange', onVisible)
})

function onVisible() {
    if (document.visibilityState === 'visible') load(true)
}

async function load(silent = false) {
    if (!silent) loading.value = true
    try {
        const api = new ApiApi()
        const all: ShoppingListEntry[] = []
        for (let page = 1; page < 20; page++) {
            const r = await api.apiShoppingListEntryList({page, pageSize: 200})
            all.push(...(r.results ?? []))
            if (!r.next) break
        }
        const now = new Date()
        entries.value = all.filter(e => !e.delayUntil || e.delayUntil <= now)
    } catch (e: any) {
        if (!silent) useMessageStore().addMessage(MessageType.ERROR, 'Einkaufsliste konnte nicht geladen werden')
    } finally {
        loading.value = false
    }
}

function buildRows(list: ShoppingListEntry[]): Row[] {
    const map = new Map<string, { entries: ShoppingListEntry[] }>()
    list.forEach(e => {
        const key = `${e.food?.id ?? e.food?.name}|${e.unit?.id ?? ''}|${e.checked ? 1 : 0}`
        if (!map.has(key)) map.set(key, {entries: []})
        map.get(key)!.entries.push(e)
    })
    return [...map.entries()].map(([key, {entries: es}]) => {
        const first = es[0]!
        const amount = es.reduce((sum, e) => sum + (Number(e.amount) || 0), 0)
        const unit = first.unit ? {id: first.unit.id!, name: first.unit.name, plural_name: first.unit.pluralName} : null
        const unitName = unit ? (amount > 1 && unit.plural_name ? unit.plural_name : unit.name) : ''
        const foodName = first.food ? (amount > 1 && !unit && first.food.pluralName ? first.food.pluralName : first.food.name) : '?'
        const sources = [...new Set(es.map(e => e.listRecipeData?.recipeData?.name || e.listRecipeData?.name).filter(Boolean))].join(', ')
        return {
            key, name: foodName, sources, checked: !!first.checked, ids: es.map(e => e.id!),
            amountText: amount > 0 ? `${formatAmount(amount, unit)} ${unitName}`.trim() : '',
            category: first.food?.supermarketCategory?.name ?? '',
        }
    }).sort((a, b) => a.name.localeCompare(b.name, 'de'))
}

const openRows = computed(() => buildRows(entries.value.filter(e => !e.checked)))
const doneRows = computed(() => buildRows(entries.value.filter(e => e.checked)))
const openCount = computed(() => openRows.value.length)

const groups = computed(() => {
    const map = new Map<string, Row[]>()
    openRows.value.forEach(r => {
        const name = r.category || 'Sonstiges'
        if (!map.has(name)) map.set(name, [])
        map.get(name)!.push(r)
    })
    return [...map.entries()]
        .sort(([a], [b]) => a === 'Sonstiges' ? 1 : b === 'Sonstiges' ? -1 : a.localeCompare(b, 'de'))
        .map(([name, rows]) => ({name, rows}))
})

const recipes = computed(() => {
    const map = new Map<number, { id: number, label: string, recipeId: number | null }>()
    entries.value.forEach(e => {
        const lr = e.listRecipeData
        if (lr?.id && !map.has(lr.id)) {
            const name = lr.recipeData?.name || lr.name || 'Rezept'
            map.set(lr.id, {id: lr.id, label: lr.name && lr.recipeData?.name ? `${lr.recipeData.name} (${lr.name})` : name, recipeId: lr.recipe ?? null})
        }
    })
    return [...map.values()]
})

async function toggle(row: Row) {
    const checked = !row.checked
    // sofort anzeigen, dann speichern
    entries.value.forEach(e => {
        if (row.ids.includes(e.id!)) e.checked = checked
    })
    try {
        await new ApiApi().apiShoppingListEntryBulkCreate({shoppingListEntryBulk: {ids: row.ids, checked}})
    } catch {
        useMessageStore().addMessage(MessageType.ERROR, 'Speichern fehlgeschlagen – bitte neu laden')
    }
}

async function add() {
    const text = newItem.value.trim()
    if (!text) return
    adding.value = true
    try {
        const api = new ApiApi()
        const parsed = await api.apiIngredientParserPostCreate({ingredientParserRequest: {ingredient: text}})
        const ing = parsed.ingredient
        await api.apiShoppingListEntryCreate({
            shoppingListEntry: {
                amount: Math.max(Number(ing?.amount) || 1, 0),
                unit: ing?.unit ?? null,
                food: ing?.food ?? {name: text},
            } as unknown as ShoppingListEntry,
        })
        newItem.value = ''
        await load(true)
    } catch {
        useMessageStore().addMessage(MessageType.ERROR, 'Artikel konnte nicht hinzugefügt werden')
    } finally {
        adding.value = false
    }
}

async function removeRecipe(id: number) {
    try {
        await new ApiApi().apiShoppingListRecipeDestroy({id})
        await load(true)
    } catch {
        useMessageStore().addMessage(MessageType.ERROR, 'Konnte nicht entfernt werden')
    }
}
</script>

<style scoped>
.rz-shop {
    max-width: 720px;
    margin: 0 auto;
    padding: 20px 20px 32px;
}

.rz-shop__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
}

.rz-shop__title {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--rz-ink);
    margin: 0;
}

.rz-muted {
    color: var(--rz-muted);
    margin: 2px 0 0;
    font-size: 0.875rem;
}

.rz-icon-btn--accent {
    background: var(--rz-accent);
    border-color: var(--rz-accent);
    color: #fff;
}

.rz-icon-btn--accent:disabled {
    opacity: .4;
}

.rz-add {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 16px;
    padding: 4px 4px 4px 16px;
    border-radius: var(--rz-radius-field);
    background: var(--rz-surface);
}

.rz-add input {
    flex: 1;
    min-width: 0;
    height: 44px;
    border: 0;
    outline: none;
    background: transparent;
    font: inherit;
    font-size: 1rem;
    color: var(--rz-ink);
}

.rz-shop__recipes {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
}

.rz-recipe-chip {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    height: 34px;
    padding-left: 12px;
    border-radius: 999px;
    background: var(--rz-surface-soft);
    border: 1px solid var(--rz-border);
    font-size: 0.8125rem;
    font-weight: 600;
}

.rz-recipe-chip a {
    color: var(--rz-ink-2);
    text-decoration: none;
}

.rz-recipe-chip button {
    width: 34px;
    height: 34px;
    border: 0;
    background: none;
    color: var(--rz-muted);
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.rz-group {
    margin-top: 22px;
}

.rz-group__title {
    font-size: 0.8125rem;
    font-weight: 700;
    letter-spacing: .05em;
    text-transform: uppercase;
    color: var(--rz-muted);
    margin: 0 0 4px;
}

.rz-item {
    display: flex;
    align-items: center;
    gap: 14px;
    width: 100%;
    min-height: 56px;
    padding: 8px 0;
    border: 0;
    border-bottom: 1px solid var(--rz-border);
    background: none;
    font: inherit;
    text-align: left;
    color: var(--rz-ink);
    cursor: pointer;
}

.rz-check {
    flex: 0 0 26px;
    height: 26px;
    border-radius: 50%;
    border: 1.75px solid var(--rz-border-strong);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #fff;
}

.rz-check--on {
    background: var(--rz-accent);
    border-color: var(--rz-accent);
}

.rz-item__main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
}

.rz-item__name {
    font-size: 1rem;
    font-weight: 600;
}

.rz-item__src {
    font-size: 0.75rem;
    color: var(--rz-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.rz-item__amount {
    flex-shrink: 0;
    font-size: 0.9375rem;
    color: var(--rz-ink-2);
    font-variant-numeric: tabular-nums;
}

.rz-item--done .rz-item__name, .rz-item--done .rz-item__amount {
    text-decoration: line-through;
    color: var(--rz-muted);
}

.rz-empty {
    text-align: center;
    color: var(--rz-muted);
    padding: 40px 0;
}
</style>
