<template>
    <div class="rz-cat-picker">
        <button v-for="c in options" :key="c.id" type="button" class="rz-cat-chip" :class="{'rz-cat-chip--active': selected.has(c.id)}"
                :aria-pressed="selected.has(c.id)" :disabled="disabled" @click="toggle(c.id)">
            <rz-icon v-if="selected.has(c.id)" name="check" :size="15"/>{{ c.name }}
        </button>
        <form v-if="adding" class="rz-cat-new" @submit.prevent="add()">
            <input ref="input" v-model="newName" maxlength="64" placeholder="Neue Kategorie" aria-label="Name der neuen Kategorie"/>
            <button type="submit" class="rz-cat-chip rz-cat-chip--active" :disabled="!newName.trim() || busy" aria-label="Anlegen">
                <rz-icon name="check" :size="16"/>
            </button>
            <button type="button" class="rz-cat-chip" aria-label="Abbrechen" @click="adding = false"><rz-icon name="x" :size="16"/></button>
        </form>
        <button v-else-if="allowCreate" type="button" class="rz-cat-chip rz-cat-chip--ghost" :disabled="disabled" @click="startAdd()">
            <rz-icon name="plus" :size="15"/>Neu
        </button>
        <p v-if="error" class="rz-cat-error">{{ error }}</p>
    </div>
</template>

<script setup lang="ts">
/** Auswahl der Kategorien als Chips (Mehrfachauswahl) – mit „Neu“ direkt anlegen */
import {computed, nextTick, ref} from 'vue'
import RzIcon from './RzIcon.vue'
import {useCategories} from '../services/categories'

const model = defineModel<number[]>({default: () => []})
withDefaults(defineProps<{ disabled?: boolean, allowCreate?: boolean }>(), {disabled: false, allowCreate: true})

const {categories, ensure, create} = useCategories()
ensure().catch(() => undefined)

const options = computed(() => categories.value)
const selected = computed(() => new Set(model.value))
const adding = ref(false)
const newName = ref('')
const busy = ref(false)
const error = ref('')
const input = ref<HTMLInputElement | null>(null)

function toggle(id: number) {
    model.value = selected.value.has(id) ? model.value.filter(x => x !== id) : [...model.value, id]
}

async function startAdd() {
    adding.value = true
    newName.value = ''
    error.value = ''
    await nextTick()
    input.value?.focus()
}

async function add() {
    busy.value = true
    error.value = ''
    try {
        const c = await create(newName.value.trim())
        if (!selected.value.has(c.id)) model.value = [...model.value, c.id]
        adding.value = false
    } catch (e: any) {
        error.value = e?.message || 'Anlegen fehlgeschlagen.'
    } finally {
        busy.value = false
    }
}
</script>

<style scoped>
.rz-cat-picker {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.rz-cat-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 44px;
    padding: 0 16px;
    border-radius: 999px;
    border: 1px solid transparent;
    background: var(--rz-surface);
    color: var(--rz-ink-2);
    font: inherit;
    font-size: 0.9375rem;
    font-weight: 600;
    cursor: pointer;
}

.rz-cat-chip--active {
    background: var(--rz-accent);
    color: #fff;
}

.rz-cat-chip--ghost {
    background: var(--rz-bg);
    border-color: var(--rz-border-strong);
    color: var(--rz-accent);
}

.rz-cat-chip:disabled {
    opacity: .6;
}

.rz-cat-new {
    display: inline-flex;
    gap: 6px;
}

.rz-cat-new input {
    min-height: 44px;
    width: 170px;
    padding: 0 14px;
    border-radius: 999px;
    border: 1px solid var(--rz-border-strong);
    font: inherit;
    font-size: 0.9375rem;
    color: var(--rz-ink);
    outline: none;
}

.rz-cat-new input:focus {
    border-color: var(--rz-accent);
}

.rz-cat-error {
    width: 100%;
    margin: 0;
    color: rgb(var(--v-theme-error));
    font-size: 0.875rem;
}
</style>
