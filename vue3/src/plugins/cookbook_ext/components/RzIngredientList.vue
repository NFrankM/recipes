<template>
    <div class="rz-ingredients">
        <template v-for="row in rows" :key="row.key">
            <div v-if="row.kind === 'header'" class="rz-ing-header">{{ row.ingredient.note || row.ingredient.food?.name }}</div>

            <component :is="editable ? 'button' : 'div'" v-else class="rz-ing" :type="editable ? 'button' : undefined"
                       :class="{'rz-ing--removed': row.ingredient.status === 'removed', 'rz-ing--editable': editable}"
                       @click="editable && emit('select', row.ingredient, row.step)">
                <span class="rz-ing__amount">
                    <template v-if="!row.ingredient.no_amount">
                        {{ formatAmount(row.ingredient.amount, row.ingredient.unit) }} <span class="rz-ing__unit">{{ unitLabel(row.ingredient) }}</span>
                    </template>
                </span>
                <span class="rz-ing__main">
                    <span class="rz-ing__food">{{ foodLabel(row.ingredient) }}</span>
                    <span v-if="row.ingredient.note" class="rz-ing__note">{{ row.ingredient.note }}</span>
                    <span v-if="row.ingredient.status === 'changed' && row.ingredient.original" class="rz-ing__was">
                        statt {{ ingredientText(row.ingredient.original) }}
                    </span>
                </span>
                <span class="rz-ing__badges">
                    <span v-if="row.ingredient.status === 'changed'" class="rz-badge">geändert</span>
                    <span v-else-if="row.ingredient.status === 'added'" class="rz-badge rz-badge--outline">ergänzt</span>
                    <span v-else-if="row.ingredient.status === 'removed'" class="rz-badge rz-badge--muted">entfernt</span>
                    <rz-icon v-if="editable" name="chevron-right" :size="18" class="rz-ing__chevron"/>
                </span>
            </component>
        </template>

        <button v-if="editable" type="button" class="rz-ing-add" @click="emit('add')">
            <rz-icon name="plus" :size="20"/>
            Zutat ergänzen
        </button>
    </div>
</template>

<script setup lang="ts">
import {computed} from 'vue'
import RzIcon from './RzIcon.vue'
import {foodLabel, formatAmount, ingredientText, unitLabel} from '../services/format'
import type {EffectiveIngredient, EffectiveStep} from '../services/types'

const props = withDefaults(defineProps<{ steps: EffectiveStep[], editable?: boolean }>(), {editable: false})
const emit = defineEmits<{ select: [ingredient: EffectiveIngredient, step: EffectiveStep], add: [] }>()

type Row = { key: string, kind: 'header' | 'ingredient', ingredient: EffectiveIngredient, step: EffectiveStep }

/** Alle Zutaten aller Schritte als flache Liste (wie in Mela); entfernte nur im Bearbeiten-Modus */
const rows = computed<Row[]>(() => {
    const out: Row[] = []
    props.steps.forEach((s, si) => {
        const list = props.editable ? [...s.ingredients, ...s.removed_ingredients] : s.ingredients
        list.forEach((i, ii) => {
            out.push({
                key: `${si}-${i.status}-${i.ingredient ?? 'n'}-${i.change ?? 'n'}-${ii}`,
                kind: i.is_header ? 'header' : 'ingredient',
                ingredient: i,
                step: s,
            })
        })
    })
    return out
})
</script>

<style scoped>
.rz-ingredients {
    display: flex;
    flex-direction: column;
}

.rz-ing-header {
    font-size: 0.8125rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--rz-muted);
    padding: 16px 0 6px;
}

.rz-ing {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 48px;
    padding: 10px 0;
    border: 0;
    border-bottom: 1px solid var(--rz-border);
    background: none;
    text-align: left;
    font: inherit;
    color: var(--rz-ink);
    width: 100%;
}

.rz-ing--editable {
    cursor: pointer;
}

.rz-ing--editable:active {
    background: var(--rz-surface-soft);
}

.rz-ing__amount {
    flex: 0 0 84px;
    font-weight: 700;
    font-size: 0.9375rem;
    font-variant-numeric: tabular-nums;
}

.rz-ing__unit {
    font-weight: 600;
}

.rz-ing__main {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    min-width: 0;
    font-size: 0.9375rem;
    line-height: 1.35;
}

.rz-ing__note, .rz-ing__was {
    font-size: 0.8125rem;
    color: var(--rz-muted);
}

.rz-ing__was {
    text-decoration: line-through;
    text-decoration-color: var(--rz-border-strong);
}

.rz-ing__badges {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
}

.rz-ing__chevron {
    color: var(--rz-border-strong);
}

.rz-ing--removed .rz-ing__amount, .rz-ing--removed .rz-ing__food {
    text-decoration: line-through;
    color: var(--rz-muted);
}

.rz-badge {
    display: inline-flex;
    align-items: center;
    height: 22px;
    padding: 0 9px;
    border-radius: 999px;
    background: var(--rz-accent);
    color: #fff;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid var(--rz-accent);
    white-space: nowrap;
}

.rz-badge--outline {
    background: transparent;
    color: var(--rz-accent);
}

.rz-badge--muted {
    background: var(--rz-surface);
    border-color: var(--rz-surface);
    color: var(--rz-muted);
}

.rz-ing-add {
    display: flex;
    align-items: center;
    gap: 10px;
    min-height: 48px;
    margin-top: 6px;
    border: 0;
    background: none;
    color: var(--rz-accent);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
}
</style>
