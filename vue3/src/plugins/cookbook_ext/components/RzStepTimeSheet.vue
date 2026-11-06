<template>
    <v-bottom-sheet v-model="open" inset>
        <v-card class="rz-time-sheet">
            <h2 class="rz-time-sheet__title">Zeit für Schritt {{ stepNumber }}</h2>

            <div class="rz-time-row">
                <span class="rz-time-row__label">Aktive Zeit<small>Kneten, Schneiden, Rühren …</small></span>
                <div class="rz-time-inputs">
                    <label><input v-model.number="activeH" type="number" min="0" inputmode="numeric" aria-label="Aktive Zeit Stunden"/> Std.</label>
                    <label><input v-model.number="activeM" type="number" min="0" max="59" inputmode="numeric" aria-label="Aktive Zeit Minuten"/> Min.</label>
                </div>
            </div>
            <div class="rz-time-row">
                <span class="rz-time-row__label">Wartezeit<small>Gare, Ruhen, Backen …</small></span>
                <div class="rz-time-inputs">
                    <label><input v-model.number="waitH" type="number" min="0" inputmode="numeric" aria-label="Wartezeit Stunden"/> Std.</label>
                    <label><input v-model.number="waitM" type="number" min="0" max="59" inputmode="numeric" aria-label="Wartezeit Minuten"/> Min.</label>
                </div>
            </div>
            <div class="rz-time-quick">
                <button v-for="q in QUICK" :key="q.label" type="button" class="rz-time-chip" @click="setWait(q.minutes)">{{ q.label }}</button>
            </div>

            <v-switch v-model="parallel" color="primary" hide-details inset class="mt-2"
                      label="Läuft parallel zum nächsten Schritt (zählt nicht zur Gesamtdauer)"/>

            <p class="rz-time-total">Gesamt: <strong>{{ formatMinutes(total) || '–' }}</strong></p>
            <p v-if="error" class="rz-time-error">{{ error }}</p>

            <v-btn color="primary" size="large" block :loading="saving" @click="save()">Speichern</v-btn>
            <v-btn variant="text" block class="mt-1" :disabled="saving" @click="open = false">Abbrechen</v-btn>
        </v-card>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
/** Zeit eines Original-Schritts bearbeiten: aktive Zeit + Wartezeit (= Step.time) und „läuft parallel“ */
import {computed, ref, watch} from 'vue'
import {rzApi} from '../services/api'
import {formatMinutes} from '../services/format'
import type {EffectiveStep} from '../services/types'

const open = defineModel<boolean>({default: false})
const props = defineProps<{ step: EffectiveStep | null, stepNumber: number }>()
const emit = defineEmits<{ saved: [] }>()

const QUICK = [{label: '30 Min.', minutes: 30}, {label: '1 Std.', minutes: 60}, {label: '2 Std.', minutes: 120}, {label: 'Über Nacht', minutes: 720}]

const activeH = ref(0)
const activeM = ref(0)
const waitH = ref(0)
const waitM = ref(0)
const parallel = ref(false)
const saving = ref(false)
const error = ref('')

const n = (v: unknown) => Math.max(0, Math.floor(Number(v) || 0))
const active = computed(() => n(activeH.value) * 60 + n(activeM.value))
const wait = computed(() => n(waitH.value) * 60 + n(waitM.value))
const total = computed(() => active.value + wait.value)

watch(open, isOpen => {
    if (!isOpen || !props.step) return
    const w = Math.min(props.step.wait_time ?? 0, props.step.time ?? 0)
    const a = (props.step.time ?? 0) - w
    activeH.value = Math.floor(a / 60)
    activeM.value = a % 60
    waitH.value = Math.floor(w / 60)
    waitM.value = w % 60
    parallel.value = !!props.step.parallel
    error.value = ''
})

function setWait(minutes: number) {
    waitH.value = Math.floor(minutes / 60)
    waitM.value = minutes % 60
}

async function save() {
    if (!props.step?.id) return
    saving.value = true
    error.value = ''
    try {
        await rzApi.setStepTiming(props.step.id, {time: total.value, wait_time: wait.value, parallel: parallel.value})
        open.value = false
        emit('saved')
    } catch (e: any) {
        error.value = e?.message || 'Speichern fehlgeschlagen.'
    } finally {
        saving.value = false
    }
}
</script>

<style scoped>
.rz-time-sheet {
    padding: 20px 20px calc(20px + env(safe-area-inset-bottom));
    border-radius: var(--rz-radius-sheet) var(--rz-radius-sheet) 0 0 !important;
}

.rz-time-sheet__title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--rz-ink);
    margin: 0 0 12px;
}

.rz-time-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid var(--rz-border);
}

.rz-time-row__label {
    display: flex;
    flex-direction: column;
    font-weight: 600;
    color: var(--rz-ink);
}

.rz-time-row__label small {
    font-weight: 400;
    color: var(--rz-muted);
    font-size: 0.8125rem;
}

.rz-time-inputs {
    display: flex;
    gap: 8px;
    color: var(--rz-muted);
    font-size: 0.875rem;
}

.rz-time-inputs input {
    width: 56px;
    height: 44px;
    border-radius: var(--rz-radius-field);
    border: 1px solid var(--rz-border-strong);
    text-align: center;
    font: inherit;
    font-size: 1rem;
    color: var(--rz-ink);
    margin-right: 2px;
}

.rz-time-quick {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
}

.rz-time-chip {
    min-height: 40px;
    padding: 0 14px;
    border-radius: 999px;
    border: 0;
    background: var(--rz-surface);
    color: var(--rz-ink-2);
    font: inherit;
    font-size: 0.875rem;
    font-weight: 600;
}

.rz-time-total {
    margin: 12px 0;
    color: var(--rz-ink-2);
}

.rz-time-error {
    color: rgb(var(--v-theme-error));
}
</style>
