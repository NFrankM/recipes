<template>
    <v-bottom-sheet v-model="open" inset scrollable>
        <v-card class="rz-plan">
            <div class="rz-plan__head">
                <h2 class="rz-plan__title">Zeitplan</h2>
                <button type="button" class="rz-plan__close" aria-label="Schließen" @click="open = false"><rz-icon name="x"/></button>
            </div>

            <rz-segment v-model="mode" :options="MODES"/>
            <label class="rz-plan__input">
                <span>{{ mode === 'start' ? 'Ich starte um' : 'Fertig sein um' }}</span>
                <input v-model="anchorText" type="datetime-local" step="300"/>
            </label>

            <p v-if="!hasTimes" class="rz-plan__hint">Für dieses Rezept sind noch keine Schrittzeiten hinterlegt. Tippe in der Rezeptansicht auf
                „⋯ → Zeiten bearbeiten“.</p>

            <template v-else>
                <div class="rz-plan__summary">
                    <span>Start <strong>{{ formatSlot(schedule.start, showDay) }}</strong></span>
                    <span>Fertig <strong>{{ formatSlot(schedule.end, showDay) }}</strong></span>
                    <span>Dauer <strong>{{ formatDuration(schedule.totalMinutes) }}</strong></span>
                </div>

                <ol class="rz-plan__list">
                    <li v-for="item in schedule.items" :key="item.index" class="rz-plan__item"
                        :class="{'rz-plan__item--day': dayChanged(item.index)}">
                        <span class="rz-plan__time">{{ formatSlot(item.start, showDay) }}</span>
                        <span class="rz-plan__step">
                            <strong>{{ item.index + 1 }}. {{ label(item.index) }}</strong>
                            <small>
                                <template v-if="item.minutes">{{ formatDuration(item.minutes) }}</template>
                                <template v-if="item.parallel"> · parallel</template>
                                <template v-if="item.minutes"> · bis {{ formatSlot(item.end, showDay) }}</template>
                            </small>
                        </span>
                    </li>
                </ol>

                <v-btn variant="outlined" size="large" block class="mt-4" @click="exportIcs()">
                    <rz-icon name="calendar" class="me-2"/>In den Kalender (.ics, mit Erinnerungen)
                </v-btn>
            </template>
        </v-card>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
/**
 * „Zeitplan“: Startzeit (Standard: jetzt) oder Zielzeit eingeben → Uhrzeit je Schritt, mehrtägig mit Wochentag.
 * Rechnet mit den Schritten der gewählten Fassung (Original / Unsere Version).
 */
import {computed, ref, watch} from 'vue'
import RzIcon from './RzIcon.vue'
import RzSegment from './RzSegment.vue'
import {buildSchedule, formatDuration, formatSlot, roundedNow, scheduleToIcs, toLocalInput} from '../services/schedule'
import type {EffectiveStep} from '../services/types'

const open = defineModel<boolean>({default: false})
const props = defineProps<{ steps: EffectiveStep[], recipeName: string, recipeId: number }>()

const MODES = [{value: 'start', label: 'Startzeit'}, {value: 'end', label: 'Fertig um'}]
const mode = ref<'start' | 'end'>('start')
const anchorText = ref(toLocalInput(roundedNow()))

watch(open, isOpen => {
    if (isOpen) anchorText.value = toLocalInput(roundedNow())
})

const scheduleSteps = computed(() => props.steps.map(s => ({
    time: s.time ?? 0, parallel: !!s.parallel, name: s.name, instruction: s.instruction,
})))
const hasTimes = computed(() => scheduleSteps.value.some(s => s.time > 0))
const anchor = computed(() => {
    const d = new Date(anchorText.value)
    return isNaN(d.getTime()) ? roundedNow() : d
})
const schedule = computed(() => buildSchedule(scheduleSteps.value, anchor.value, mode.value))
watch(mode, (m, old) => {
    // beim Umschalten die bisher berechnete Gegenzeit übernehmen, damit nichts springt
    const before = buildSchedule(scheduleSteps.value, anchor.value, old)
    anchorText.value = toLocalInput(m === 'end' ? before.end : before.start)
}, {flush: 'sync'})
const showDay = computed(() => schedule.value.multiDay || schedule.value.start.toDateString() !== new Date().toDateString())

function dayChanged(index: number) {
    if (index === 0) return false
    const items = schedule.value.items
    return items[index]?.start.toDateString() !== items[index - 1]?.start.toDateString()
}

function label(index: number) {
    const s = props.steps[index]
    if (!s) return ''
    if (s.name?.trim()) return s.name.trim()
    const text = (s.instruction ?? '').replace(/\s+/g, ' ').trim()
    return text.length > 70 ? text.slice(0, 68) + '…' : text
}

function exportIcs() {
    const ics = scheduleToIcs(props.recipeName, scheduleSteps.value, schedule.value, `rezept${props.recipeId}`)
    const blob = new Blob([ics], {type: 'text/calendar;charset=utf-8'})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Zeitplan ${props.recipeName}.ics`.replace(/[\\/:*?"<>|]/g, '')
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 10_000)
}
</script>

<style scoped>
.rz-plan {
    padding: 20px 20px calc(20px + env(safe-area-inset-bottom));
    border-radius: var(--rz-radius-sheet) var(--rz-radius-sheet) 0 0 !important;
}

.rz-plan__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}

.rz-plan__title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--rz-ink);
    margin: 0;
}

.rz-plan__close {
    width: 44px;
    height: 44px;
    border: 0;
    background: none;
    color: var(--rz-muted);
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.rz-plan__input {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-top: 14px;
    font-weight: 600;
    color: var(--rz-ink);
}

.rz-plan__input span {
    white-space: nowrap;
}

.rz-plan__input input {
    flex: 1;
    min-width: 0;
    max-width: 260px;
    min-height: 44px;
    padding: 0 12px;
    border-radius: var(--rz-radius-field);
    border: 1px solid var(--rz-border-strong);
    background: var(--rz-bg);
    font: inherit;
    font-weight: 500;
    color: var(--rz-ink);
}

.rz-plan__hint {
    margin-top: 16px;
    color: var(--rz-muted);
}

.rz-plan__summary {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 18px;
    margin: 16px 0 6px;
    padding: 12px 14px;
    border-radius: var(--rz-radius-field);
    background: var(--rz-surface-soft);
    color: var(--rz-muted);
    font-size: 0.875rem;
}

.rz-plan__summary strong {
    color: var(--rz-ink);
}

.rz-plan__list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.rz-plan__item {
    display: grid;
    grid-template-columns: 82px minmax(0, 1fr);
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid var(--rz-border);
}

.rz-plan__item--day {
    border-top: 2px solid var(--rz-accent);
}

.rz-plan__time {
    font-weight: 700;
    color: var(--rz-accent);
    font-variant-numeric: tabular-nums;
}

.rz-plan__step {
    display: flex;
    flex-direction: column;
    color: var(--rz-ink);
}

.rz-plan__step strong {
    font-weight: 600;
    font-size: 0.9375rem;
}

.rz-plan__step small {
    color: var(--rz-muted);
    font-size: 0.8125rem;
}
</style>
