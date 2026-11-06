<template>
    <div class="rz-cat-tiles" :class="{'rz-cat-tiles--grid': grid}">
        <button v-for="c in categories" :key="c.id" type="button" class="rz-cat-tile" :class="{'rz-cat-tile--active': activeId === c.id}"
                :aria-pressed="activeId === c.id" @click="emit('select', c)">
            <span class="rz-cat-tile__img" :style="c.image ? {backgroundImage: `url(${c.image})`} : {}">
                <rz-icon v-if="!c.image" name="book" :size="26"/>
            </span>
            <span class="rz-cat-tile__name">{{ c.name }}</span>
            <span class="rz-cat-tile__count">{{ c.recipe_count }} {{ c.recipe_count === 1 ? 'Rezept' : 'Rezepte' }}</span>
        </button>
        <button v-if="canWrite" type="button" class="rz-cat-tile rz-cat-tile--new" @click="dialog = true">
            <span class="rz-cat-tile__img"><rz-icon name="plus" :size="26"/></span>
            <span class="rz-cat-tile__name">Neue Kategorie</span>
        </button>

        <v-dialog v-model="dialog" max-width="420">
            <v-card class="pa-2">
                <v-card-title>Neue Kategorie</v-card-title>
                <v-card-text>
                    <v-text-field v-model="name" label="Name, z. B. Suppen" autofocus hide-details="auto" :error-messages="error"
                                  @keyup.enter="save()"/>
                </v-card-text>
                <v-card-actions>
                    <v-spacer/>
                    <v-btn variant="text" @click="dialog = false">Abbrechen</v-btn>
                    <v-btn color="primary" variant="flat" :loading="saving" :disabled="!name.trim()" @click="save()">Anlegen</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
/** Kacheln je Kategorie (Startseite: waagerecht scrollbar, Kategorien-Seite: Raster) plus „Neue Kategorie“ */
import {ref, watch} from 'vue'
import RzIcon from './RzIcon.vue'
import {useCategories} from '../services/categories'
import type {Category} from '../services/types'

withDefaults(defineProps<{ activeId?: number | null, grid?: boolean, canWrite?: boolean }>(), {activeId: null, grid: false, canWrite: true})
const emit = defineEmits<{ select: [Category], created: [Category] }>()

const {categories, ensure, create} = useCategories()
const dialog = ref(false)
const name = ref('')
const error = ref('')
const saving = ref(false)

ensure().catch(() => undefined)
watch(dialog, open => {
    if (open) {
        name.value = ''
        error.value = ''
    }
})

async function save() {
    if (!name.value.trim()) return
    saving.value = true
    error.value = ''
    try {
        const c = await create(name.value.trim())
        dialog.value = false
        emit('created', c)
    } catch (e: any) {
        error.value = e?.message || 'Anlegen fehlgeschlagen.'
    } finally {
        saving.value = false
    }
}
</script>

<style scoped>
.rz-cat-tiles {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    margin: 0 -20px;
    padding: 0 20px 4px;
    scrollbar-width: none;
}

.rz-cat-tiles::-webkit-scrollbar {
    display: none;
}

.rz-cat-tiles--grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px 14px;
    overflow: visible;
    margin: 0;
    padding: 0;
}

@media (min-width: 720px) {
    .rz-cat-tiles--grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

.rz-cat-tile {
    flex: 0 0 116px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    border: 0;
    padding: 0;
    background: none;
    font: inherit;
    text-align: left;
    color: var(--rz-ink);
    cursor: pointer;
    min-width: 0;
}

.rz-cat-tile__img {
    width: 100%;
    aspect-ratio: 1;
    margin-bottom: 6px;
    border-radius: var(--rz-radius-card);
    background: var(--rz-surface) center / cover no-repeat;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--rz-muted);
    border: 2px solid transparent;
}

.rz-cat-tiles--grid .rz-cat-tile__img {
    aspect-ratio: 4 / 3;
}

.rz-cat-tile--active .rz-cat-tile__img {
    border-color: var(--rz-accent);
}

.rz-cat-tile--new .rz-cat-tile__img {
    background: var(--rz-bg);
    border: 1.5px dashed var(--rz-border-strong);
    color: var(--rz-accent);
}

.rz-cat-tile__name {
    font-weight: 700;
    font-size: 0.9375rem;
    line-height: 1.25;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
}

.rz-cat-tile__count {
    color: var(--rz-muted);
    font-size: 0.8125rem;
}
</style>
