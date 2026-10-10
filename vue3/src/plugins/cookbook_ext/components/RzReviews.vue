<template>
    <section class="rz-reviews">
        <div class="rz-reviews__head">
            <h2 class="rz-h2">Bewertungen</h2>
            <span v-if="summary && summary.count" class="rz-reviews__avg">
                <rz-stars :model-value="summary.average ?? 0" :size="16"/>
                {{ formatAvg(summary.average) }} · {{ summary.count }}
            </span>
        </div>

        <p v-if="!loading && logs.length === 0" class="rz-muted">Noch keine Bewertungen.</p>

        <article v-for="log in logs" :key="log.id" class="rz-review">
            <div class="rz-review__top">
                <span class="rz-avatar">{{ (log.createdBy?.displayName ?? '?').charAt(0).toUpperCase() }}</span>
                <span class="rz-review__who">
                    <strong>{{ log.createdBy?.displayName }}</strong>
                    <span class="rz-muted">{{ formatDate(log.createdAt) }}</span>
                </span>
                <rz-stars v-if="log.rating" :model-value="log.rating" :size="14"/>
            </div>
            <p v-if="log.comment" class="rz-review__text">{{ log.comment }}</p>
            <div v-if="photosByLog[log.id!]?.length" class="rz-review__photos">
                <a v-for="p in photosByLog[log.id!]" :key="p.id" :href="p.image" target="_blank" rel="noopener" class="rz-review__photo">
                    <img :src="p.image" alt="Foto zur Bewertung" loading="lazy"/>
                </a>
            </div>
        </article>

        <v-btn v-if="canWrite" block variant="outlined" size="large" class="mt-2" @click="openSheet()">
            <rz-icon name="camera" :size="20" class="me-2"/>
            Bewertung oder Foto hinzufügen
        </v-btn>

        <v-bottom-sheet v-model="sheet" max-width="640" scrollable>
            <div class="rz-sheet">
                <div class="rz-sheet__handle"></div>
                <div class="rz-sheet__head">
                    <h3 class="rz-sheet__title">Wie war's?</h3>
                    <button type="button" class="rz-icon-btn" aria-label="Schließen" @click="sheet = false">
                        <rz-icon name="x"/>
                    </button>
                </div>
                <div class="rz-sheet__body">
                    <rz-stars v-model="form.rating" input :size="30"/>
                    <v-textarea v-model="form.comment" label="Kommentar (optional)" rows="2" auto-grow hide-details="auto"/>
                    <div class="rz-sheet__row">
                        <v-text-field v-model="form.date" type="date" label="Gekocht am" hide-details="auto"/>
                        <v-text-field v-model="form.servings" label="Portionen" inputmode="numeric" hide-details="auto" style="max-width: 120px"/>
                    </div>

                    <div class="rz-photo-pick">
                        <label class="rz-photo-pick__btn">
                            <input type="file" accept="image/*" multiple @change="pickFiles"/>
                            <rz-icon name="camera" :size="20"/>
                            Fotos wählen
                        </label>
                        <div v-for="(f, i) in files" :key="i" class="rz-photo-pick__thumb">
                            <img :src="f.url" alt=""/>
                            <button type="button" aria-label="Foto entfernen" @click="files.splice(i, 1)">
                                <rz-icon name="x" :size="14"/>
                            </button>
                        </div>
                    </div>

                    <v-btn block color="primary" size="large" :loading="saving" :disabled="!canSave" @click="save()">Speichern</v-btn>
                    <p v-if="error" class="rz-sheet__error">{{ error }}</p>
                </div>
            </div>
        </v-bottom-sheet>
    </section>
</template>

<script setup lang="ts">
import {computed, onMounted, ref, watch} from 'vue'
import {DateTime} from 'luxon'
import {ApiApi, CookLog} from '@/openapi'
import RzIcon from './RzIcon.vue'
import RzStars from './RzStars.vue'
import {rzApi} from '../services/api'
import type {CookLogPhoto, RatingSummary} from '../services/types'

const props = defineProps<{ recipeId: number, servings: number, canWrite: boolean }>()
const emit = defineEmits<{ changed: [] }>()

const logs = ref<CookLog[]>([])
const photos = ref<CookLogPhoto[]>([])
const summary = ref<RatingSummary | null>(null)
const loading = ref(false)

const sheet = ref(false)
const saving = ref(false)
const error = ref('')
const form = ref({rating: 0, comment: '', date: '', servings: ''})
const files = ref<{ file: File, url: string }[]>([])

const photosByLog = computed(() => {
    const map: Record<number, CookLogPhoto[]> = {}
    photos.value.forEach(p => (map[p.cook_log] ??= []).push(p))
    return map
})
const canSave = computed(() => form.value.rating > 0 || form.value.comment.trim() !== '' || files.value.length > 0)

onMounted(load)
watch(() => props.recipeId, load)

async function load() {
    loading.value = true
    try {
        const api = new ApiApi()
        const all: CookLog[] = []
        for (let page = 1; page < 20; page++) {
            const r = await api.apiCookLogList({recipe: props.recipeId, page, pageSize: 100})
            all.push(...(r.results ?? []))
            if (!r.next) break
        }
        // nur echte Bewertungen/Kommentare zeigen, neueste zuerst
        logs.value = all.filter(l => l.rating || l.comment).sort((a, b) => (b.createdAt?.getTime() ?? 0) - (a.createdAt?.getTime() ?? 0))
        const [s, p] = await Promise.all([rzApi.ratings([props.recipeId]), rzApi.photos(props.recipeId)])
        summary.value = s[0] ?? null
        photos.value = p
        // Logs, die nur Fotos haben, trotzdem anzeigen
        const withPhotos = new Set(p.map(x => x.cook_log))
        all.filter(l => !l.rating && !l.comment && withPhotos.has(l.id!)).forEach(l => logs.value.push(l))
    } finally {
        loading.value = false
    }
}

function openSheet() {
    error.value = ''
    files.value = []
    form.value = {rating: 0, comment: '', date: DateTime.now().toISODate()!, servings: String(props.servings)}
    sheet.value = true
}

function pickFiles(e: Event) {
    const input = e.target as HTMLInputElement
    Array.from(input.files ?? []).forEach(f => files.value.push({file: f, url: URL.createObjectURL(f)}))
    input.value = ''
}

async function save() {
    saving.value = true
    error.value = ''
    try {
        const date = form.value.date ? DateTime.fromISO(form.value.date).set({hour: 12}).toJSDate() : new Date()
        const servings = parseInt(form.value.servings, 10)
        const log = await new ApiApi().apiCookLogCreate({
            cookLog: {
                recipe: props.recipeId,
                rating: form.value.rating || null,
                comment: form.value.comment.trim() || null,
                servings: isFinite(servings) && servings > 0 ? servings : null,
                createdAt: date,
            } as CookLog,
        })
        for (const f of files.value) {
            await rzApi.uploadPhoto(log.id!, f.file)
        }
        sheet.value = false
        await load()
        emit('changed')
    } catch (e: any) {
        error.value = e?.message ?? 'Speichern fehlgeschlagen'
    } finally {
        saving.value = false
    }
}

function formatAvg(v: number | null) {
    return v == null ? '' : new Intl.NumberFormat('de-DE', {maximumFractionDigits: 1}).format(v)
}

function formatDate(d?: Date) {
    return d ? DateTime.fromJSDate(d).setLocale('de').toLocaleString(DateTime.DATE_MED) : ''
}

defineExpose({load})
</script>

<style scoped>
.rz-reviews__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
}

.rz-reviews__avg {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--rz-muted);
    font-size: 0.875rem;
}

.rz-review {
    padding: 14px 0;
    border-bottom: 1px solid var(--rz-border);
}

.rz-review__top {
    display: flex;
    align-items: center;
    gap: 10px;
}

.rz-review__who {
    flex: 1;
    display: flex;
    flex-direction: column;
    line-height: 1.25;
    font-size: 0.875rem;
}

.rz-review__text {
    margin: 8px 0 0;
    color: var(--rz-ink-2);
    font-size: 0.9375rem;
}

.rz-review__photos {
    display: flex;
    gap: 8px;
    margin-top: 10px;
    overflow-x: auto;
}

.rz-review__photo img {
    width: 88px;
    height: 88px;
    object-fit: cover;
    border-radius: 12px;
    display: block;
}

.rz-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--rz-surface);
    color: var(--rz-accent);
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.rz-photo-pick {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.rz-photo-pick__btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 44px;
    padding: 0 16px;
    border-radius: var(--rz-radius-field);
    border: 1px dashed var(--rz-border-strong);
    color: var(--rz-accent);
    font-weight: 600;
    cursor: pointer;
}

.rz-photo-pick__btn input {
    display: none;
}

.rz-photo-pick__thumb {
    position: relative;
}

.rz-photo-pick__thumb img {
    width: 64px;
    height: 64px;
    object-fit: cover;
    border-radius: 10px;
    display: block;
}

.rz-photo-pick__thumb button {
    position: absolute;
    top: -6px;
    right: -6px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    border: 1px solid var(--rz-border);
    background: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
</style>
