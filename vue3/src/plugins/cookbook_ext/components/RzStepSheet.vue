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

            <div class="rz-sheet__body">
                <template v-if="mode === 'note'">
                    <v-textarea v-model="text" label="Unsere Notiz" rows="3" auto-grow hide-details="auto" autofocus
                                placeholder="z. B. Pfanne richtig heiß werden lassen"/>
                    <v-btn block color="primary" size="large" :loading="saving" :disabled="!text.trim()" @click="saveNote()">Speichern</v-btn>
                    <div class="rz-sheet__secondary">
                        <v-btn v-if="existingNote" variant="outlined" :loading="saving" @click="deleteNote()">
                            <rz-icon name="trash" :size="18" class="me-2"/>
                            Notiz löschen
                        </v-btn>
                        <v-btn v-if="step?.id" variant="outlined" @click="startInsert()">
                            <rz-icon name="plus" :size="18" class="me-2"/>
                            Schritt danach
                        </v-btn>
                    </div>
                </template>

                <template v-else>
                    <v-textarea v-model="text" label="Was ist zu tun?" rows="3" auto-grow hide-details="auto" autofocus/>
                    <v-text-field v-model="time" label="Dauer in Minuten (optional)" inputmode="numeric" hide-details="auto"/>
                    <v-btn block color="primary" size="large" :loading="saving" :disabled="!text.trim()" @click="saveAdded()">Speichern</v-btn>
                    <v-btn v-if="step?.is_added && step.added_note" variant="outlined" :loading="saving" @click="deleteAdded()">
                        <rz-icon name="trash" :size="18" class="me-2"/>
                        Schritt löschen
                    </v-btn>
                </template>
                <p v-if="error" class="rz-sheet__error">{{ error }}</p>
            </div>
        </div>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import RzIcon from './RzIcon.vue'
import {rzApi} from '../services/api'
import type {EffectiveStep} from '../services/types'

const props = defineProps<{
    modelValue: boolean
    variantId: number
    step: EffectiveStep | null
    /** Index des Original-Schritts (0-basiert) – für „Schritt danach“ */
    originalIndex: number
    number: number
}>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean], saved: [] }>()

const mode = ref<'note' | 'added'>('note')
const text = ref('')
const time = ref('')
const saving = ref(false)
const error = ref('')

const existingNote = computed(() => props.step?.notes?.[0] ?? null)
const title = computed(() => {
    if (props.step?.is_added) return 'Eigener Schritt'
    if (mode.value === 'added') return `Neuer Schritt nach Schritt ${props.number}`
    return `Schritt ${props.number}`
})

watch(() => props.modelValue, open => {
    if (!open) return
    error.value = ''
    if (props.step?.is_added) {
        mode.value = 'added'
        text.value = props.step.added_note?.text ?? props.step.instruction
        time.value = props.step.time ? String(props.step.time) : ''
    } else {
        mode.value = 'note'
        text.value = existingNote.value?.text ?? ''
        time.value = ''
    }
})

function startInsert() {
    mode.value = 'added'
    text.value = ''
    time.value = ''
}

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

function minutes() {
    const n = parseInt(time.value, 10)
    return isFinite(n) && n > 0 ? n : 0
}

function saveNote() {
    if (existingNote.value) return run(() => rzApi.updateNote(existingNote.value!.id, {text: text.value}))
    return run(() => rzApi.createNote({variant: props.variantId, step: props.step!.id, text: text.value}))
}

function deleteNote() {
    if (existingNote.value) return run(() => rzApi.deleteNote(existingNote.value!.id))
}

function saveAdded() {
    const note = props.step?.is_added ? props.step.added_note : null
    if (note) return run(() => rzApi.updateNote(note.id, {text: text.value, time: minutes()}))
    // „Schritt danach“: vor dem nächsten Original-Schritt einfügen
    return run(() => rzApi.createNote({variant: props.variantId, step: null, position: props.originalIndex + 1, text: text.value, time: minutes()}))
}

function deleteAdded() {
    const note = props.step?.added_note
    if (note) return run(() => rzApi.deleteNote(note.id))
}
</script>
