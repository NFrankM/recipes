<template>
    <div class="rz-cats">
        <header class="rz-cats__head">
            <h1 class="rz-cats__title">Kategorien</h1>
            <v-btn v-if="canWrite && categories.length" variant="text" @click="editing = !editing">
                <rz-icon :name="editing ? 'check' : 'pencil'" :size="18" class="me-2"/>{{ editing ? 'Fertig' : 'Bearbeiten' }}
            </v-btn>
        </header>
        <p class="rz-muted">{{ editing ? 'Tippe auf eine Kategorie, um sie umzubenennen oder zu löschen.' : 'Rezepte nach Kategorie ansehen.' }}</p>

        <rz-category-tiles grid :can-write="canWrite && !editing" @select="open" @created="c => open(c)"/>
        <p v-if="loaded && !categories.length" class="rz-muted">Noch keine Kategorien.</p>

        <v-dialog v-model="dialog" max-width="420">
            <v-card v-if="current" class="pa-2">
                <v-card-title>Kategorie bearbeiten</v-card-title>
                <v-card-text>
                    <v-text-field v-model="name" label="Name" hide-details="auto" :error-messages="error" @keyup.enter="rename()"/>
                    <p class="rz-muted mt-3">{{ current.recipe_count }} {{ current.recipe_count === 1 ? 'Rezept' : 'Rezepte' }}. Beim Löschen bleiben die Rezepte erhalten.</p>
                </v-card-text>
                <v-card-actions>
                    <v-btn color="error" variant="text" :loading="busy === 'delete'" @click="remove()">Löschen</v-btn>
                    <v-spacer/>
                    <v-btn variant="text" @click="dialog = false">Abbrechen</v-btn>
                    <v-btn color="primary" variant="flat" :loading="busy === 'rename'" :disabled="!name.trim()" @click="rename()">Speichern</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import {ref} from 'vue'
import {useRouter} from 'vue-router'
import RzIcon from '../components/RzIcon.vue'
import RzCategoryTiles from '../components/RzCategoryTiles.vue'
import {useCategories} from '../services/categories'
import {rzApi} from '../services/api'
import {useCanWrite} from '../services/permissions'
import type {Category} from '../services/types'

const router = useRouter()
const {categories, loaded, reload} = useCategories()
reload().catch(() => undefined)  // Anzahl und Bilder aktuell halten

const canWrite = useCanWrite()
const editing = ref(false)
const dialog = ref(false)
const current = ref<Category | null>(null)
const name = ref('')
const error = ref('')
const busy = ref<'' | 'rename' | 'delete'>('')

function open(c: Category) {
    if (editing.value) {
        current.value = c
        name.value = c.name
        error.value = ''
        dialog.value = true
    } else {
        router.push({name: 'StartPage', query: {filter: `cat${c.id}`}})
    }
}

async function rename() {
    if (!current.value || !name.value.trim()) return
    busy.value = 'rename'
    try {
        await rzApi.renameCategory(current.value.id, name.value.trim())
        await reload()
        dialog.value = false
    } catch (e: any) {
        error.value = e?.message || 'Speichern fehlgeschlagen.'
    } finally {
        busy.value = ''
    }
}

async function remove() {
    if (!current.value) return
    busy.value = 'delete'
    try {
        await rzApi.deleteCategory(current.value.id)
        await reload()
        dialog.value = false
    } catch (e: any) {
        error.value = e?.message || 'Löschen fehlgeschlagen.'
    } finally {
        busy.value = ''
    }
}
</script>

<style scoped>
.rz-cats {
    max-width: 960px;
    margin: 0 auto;
    padding: calc(16px + env(safe-area-inset-top)) 20px 24px;
}

.rz-cats__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.rz-cats__title {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--rz-ink);
    margin: 0;
}

.rz-muted {
    color: var(--rz-muted);
    margin: 4px 0 18px;
}
</style>
