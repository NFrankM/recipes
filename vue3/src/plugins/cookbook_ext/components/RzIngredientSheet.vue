<template>
    <v-bottom-sheet :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" max-width="640" scrollable>
        <div class="rz-sheet">
            <div class="rz-sheet__handle"></div>
            <div class="rz-sheet__head">
                <h3 class="rz-sheet__title">{{ title }}</h3>
                <button type="button" class="rz-icon-btn" aria-label="Schließen" @click="emit('update:modelValue', false)">
                    <rz-icon name="x"/>
                </button>
            </div>

            <p v-if="ingredient && ingredient.status !== 'added'" class="rz-sheet__orig">
                Original: {{ originalText }}
            </p>

            <div v-if="ingredient?.status === 'removed'" class="rz-sheet__body">
                <p class="rz-sheet__hint">Diese Zutat ist in „Unsere Version“ entfernt.</p>
                <v-btn block color="primary" size="large" :loading="saving" @click="resetChange()">
                    <rz-icon name="undo" class="me-2"/>
                    Wieder aufnehmen
                </v-btn>
            </div>

            <div v-else class="rz-sheet__body">
                <div class="rz-sheet__row">
                    <v-text-field v-model="form.amount" label="Menge" inputmode="decimal" hide-details="auto" class="rz-sheet__amount"
                                  :disabled="form.noAmount"/>
                    <v-combobox v-model="form.unit" label="Einheit" :items="unitNames" hide-details="auto" class="rz-sheet__unit"
                                :disabled="form.noAmount"/>
                </div>
                <p class="rz-sheet__hint">Menge für {{ servingsLabel }}</p>
                <v-combobox v-model="form.food" label="Zutat" :items="foodNames" hide-details="auto" @update:search="searchFood"
                            :error-messages="foodError"/>
                <v-text-field v-model="form.note" label="Notiz (optional)" hide-details="auto"/>
                <v-select v-if="isNew" v-model="form.step" label="Gehört zu Schritt" :items="stepItems" hide-details="auto"/>

                <v-btn block color="primary" size="large" :loading="saving" @click="save()">Speichern</v-btn>

                <div class="rz-sheet__secondary">
                    <v-btn v-if="ingredient && ingredient.status !== 'added'" variant="outlined" :loading="saving" @click="remove()">
                        <rz-icon name="trash" :size="18" class="me-2"/>
                        Entfernen
                    </v-btn>
                    <v-btn v-if="ingredient?.status === 'changed'" variant="outlined" :loading="saving" @click="resetChange()">
                        <rz-icon name="undo" :size="18" class="me-2"/>
                        Original
                    </v-btn>
                    <v-btn v-if="ingredient?.status === 'added'" variant="outlined" :loading="saving" @click="resetChange()">
                        <rz-icon name="trash" :size="18" class="me-2"/>
                        Löschen
                    </v-btn>
                </div>
                <p v-if="error" class="rz-sheet__error">{{ error }}</p>
            </div>
        </div>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import {ApiApi} from '@/openapi'
import RzIcon from './RzIcon.vue'
import {rzApi} from '../services/api'
import {ingredientText} from '../services/format'
import type {EffectiveIngredient, EffectiveStep, IngredientChange} from '../services/types'

const props = defineProps<{
    modelValue: boolean
    variantId: number
    ingredient: EffectiveIngredient | null  // null = neue Zutat ergänzen
    steps: EffectiveStep[]
    defaultStepId?: number | null
    factor: number
    servings: number
}>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean], saved: [] }>()

const form = ref({amount: '', unit: '' as string | null, food: '' as string | null, note: '', step: null as number | null, noAmount: false})
const saving = ref(false)
const error = ref('')
const foodError = ref('')
const foodNames = ref<string[]>([])
const unitNames = ref<string[]>([])

const isNew = computed(() => props.ingredient === null)
const title = computed(() => isNew.value ? 'Zutat ergänzen' : (props.ingredient?.food?.name ?? 'Zutat'))
const servingsLabel = computed(() => `${new Intl.NumberFormat('de-DE').format(props.servings)} ${props.servings === 1 ? 'Portion' : 'Portionen'}`)
const stepItems = computed(() => props.steps.filter(s => s.id !== null).map((s, i) => ({
    value: s.id,
    title: `Schritt ${i + 1}${s.name ? ': ' + s.name : ''}`,
})))

/** Originalwerte (skaliert) der angetippten Zutat */
const original = computed(() => {
    const i = props.ingredient
    if (!i) return null
    if (i.status === 'changed' && i.original) {
        return {food: i.original.food, unit: i.original.unit, amount: i.original.amount, note: i.original.note ?? '', no_amount: i.no_amount}
    }
    return {food: i.food, unit: i.unit, amount: i.amount, note: i.note ?? '', no_amount: i.no_amount}
})
const originalText = computed(() => original.value ? (ingredientText(original.value) || original.value.food?.name || '') : '')

watch(() => props.modelValue, open => {
    if (!open) return
    error.value = ''
    foodError.value = ''
    const i = props.ingredient
    form.value = {
        amount: i && !i.no_amount ? new Intl.NumberFormat('de-DE', {maximumFractionDigits: 3, useGrouping: false}).format(i.amount) : '',
        unit: i?.unit?.name ?? null,
        food: i?.food?.name ?? null,
        note: i?.note ?? '',
        step: props.defaultStepId ?? stepItems.value[stepItems.value.length - 1]?.value ?? null,
        noAmount: !!i?.no_amount && i.status !== 'added',
    }
    loadUnits()
})

function parseAmount(text: string): number | null {
    const t = (text ?? '').toString().trim().replace(',', '.')
    if (!t) return null
    const n = Number(t)
    return isFinite(n) && n >= 0 ? n : NaN
}

let unitsLoaded = false

function loadUnits() {
    if (unitsLoaded) return
    new ApiApi().apiUnitList({pageSize: 200}).then(r => {
        unitNames.value = (r.results ?? []).map(u => u.name)
        unitsLoaded = true
    }).catch(() => undefined)
}

let searchTimer: ReturnType<typeof setTimeout> | undefined

function searchFood(query: string) {
    clearTimeout(searchTimer)
    if (!query || query.length < 2) return
    searchTimer = setTimeout(() => {
        new ApiApi().apiFoodList({query, pageSize: 15}).then(r => {
            foodNames.value = (r.results ?? []).map(f => f.name)
        }).catch(() => undefined)
    }, 250)
}

const same = (a?: string | null, b?: string | null) => (a ?? '').trim().toLowerCase() === (b ?? '').trim().toLowerCase()

async function run(action: () => Promise<any>) {
    saving.value = true
    error.value = ''
    try {
        await action()
        emit('saved')
        emit('update:modelValue', false)
    } catch (e: any) {
        error.value = e?.message ?? 'Speichern fehlgeschlagen'
    } finally {
        saving.value = false
    }
}

function save() {
    foodError.value = ''
    const food = (form.value.food ?? '').toString().trim()
    if (!food) {
        foodError.value = 'Bitte eine Zutat angeben'
        return
    }
    const amount = form.value.noAmount ? null : parseAmount(form.value.amount)
    if (Number.isNaN(amount)) {
        error.value = 'Die Menge ist keine gültige Zahl'
        return
    }
    // Eingegebene Menge gilt für die aktuell gewählten Portionen → auf Grundportionen umrechnen
    const baseAmount = amount === null ? null : amount / (props.factor || 1)
    const unit = (form.value.unit ?? '').toString().trim()
    const i = props.ingredient

    if (isNew.value) {
        return run(() => rzApi.createChange({
            variant: props.variantId, action: 'add', step: form.value.step, food_name: food,
            unit_name: unit || undefined, amount: baseAmount, note: form.value.note, order: 100,
        }))
    }
    if (!i) return

    if (i.status === 'added' && i.change) {
        return run(() => rzApi.updateChange(i.change!, {
            food_name: food, unit_name: unit || undefined, unit: unit ? undefined : null, amount: baseAmount, note: form.value.note,
        }))
    }

    // Ersetzen / Menge ändern: nur Abweichungen vom Original speichern (leere Felder = Original behalten)
    const o = original.value!
    const payload: Partial<IngredientChange> = {variant: props.variantId, action: 'replace', ingredient: i.ingredient,
        food: null, unit: null, amount: null, note: ''}
    let changed = false
    if (!same(food, o.food?.name)) {
        payload.food_name = food
        changed = true
    }
    if (unit && !same(unit, o.unit?.name)) {
        payload.unit_name = unit
        changed = true
    }
    if (amount !== null && Math.abs(amount - o.amount) > 0.001) {
        payload.amount = baseAmount
        changed = true
    }
    if (!same(form.value.note, o.note)) {
        payload.note = form.value.note.trim()
        changed = true
    }

    if (!changed) {
        // nichts mehr anders als im Original → vorhandene Änderung entfernen
        if (i.change) return run(() => rzApi.deleteChange(i.change!))
        emit('update:modelValue', false)
        return
    }
    if (i.change) {
        return run(() => rzApi.updateChange(i.change!, payload))
    }
    return run(() => rzApi.createChange(payload as IngredientChange))
}

function remove() {
    const i = props.ingredient
    if (!i) return
    if (i.change) return run(() => rzApi.updateChange(i.change!, {action: 'remove'}))
    return run(() => rzApi.createChange({variant: props.variantId, action: 'remove', ingredient: i.ingredient}))
}

function resetChange() {
    const i = props.ingredient
    if (i?.change) return run(() => rzApi.deleteChange(i.change!))
}
</script>
