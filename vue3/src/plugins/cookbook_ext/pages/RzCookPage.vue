<template>
    <div class="rz-cook" @touchstart.passive="touchStart" @touchend.passive="touchEnd">
        <header class="rz-cook__head">
            <button type="button" class="rz-icon-btn" aria-label="Kochmodus beenden" @click="close()"><rz-icon name="x"/></button>
            <div class="rz-cook__progress">
                <span>Schritt {{ index + 1 }} von {{ steps.length }}</span>
                <div class="rz-cook__bar"><div :style="{width: `${steps.length ? (index + 1) / steps.length * 100 : 0}%`}"></div></div>
            </div>
            <span class="rz-cook__lock" :class="{'rz-cook__lock--on': wakeLockActive}"
                  :title="wakeLockActive ? 'Bildschirm bleibt an' : 'Bildschirm kann ausgehen (Wake Lock braucht HTTPS)'">
                <rz-icon name="pot" :size="20"/>
            </span>
        </header>

        <main v-if="step" class="rz-cook__main">
            <p class="rz-cook__recipe">{{ recipeName }}<span v-if="effective?.variant_name"> · {{ effective.variant_name }}</span></p>
            <h1 v-if="step.name" class="rz-cook__name">{{ step.name }}</h1>
            <span v-if="step.is_added" class="rz-cook__badge">ergänzt</span>

            <ul v-if="stepIngredients.length" class="rz-cook__ings">
                <li v-for="(i, n) in stepIngredients" :key="n">
                    <strong>{{ i.no_amount ? '' : `${formatAmount(i.amount, i.unit)} ${unitLabel(i)}`.trim() }}</strong>
                    <span>{{ foodLabel(i) }}<em v-if="i.note"> – {{ i.note }}</em></span>
                </li>
            </ul>

            <div class="rz-cook__text">
                <instructions v-if="step.instructions_markdown" :key="index" :instructions_html="step.instructions_markdown"
                              :ingredient_factor="effective?.factor ?? 1"/>
                <p v-else>{{ step.instruction }}</p>
            </div>

            <div v-for="n in step.notes" :key="n.id" class="rz-cook__note">
                <span><rz-icon name="note" :size="16"/> Unsere Notiz</span>
                <p>{{ n.text }}</p>
            </div>

            <div v-if="stepTimers.length" class="rz-cook__timers">
                <button v-for="t in stepTimers" :key="t.seconds" type="button" class="rz-timer-btn" @click="startTimer(t.label, t.seconds)">
                    <rz-icon name="timer" :size="20"/> Timer {{ t.label }}
                </button>
            </div>
        </main>
        <main v-else-if="!loading" class="rz-cook__main"><p>Dieses Rezept hat keine Schritte.</p></main>

        <!-- laufende Timer (über alle Schritte hinweg) -->
        <div v-if="timers.length" class="rz-cook__running">
            <div v-for="t in timers" :key="t.id" class="rz-running" :class="{'rz-running--done': t.remaining <= 0}">
                <span class="rz-running__label">{{ t.label }}</span>
                <span class="rz-running__clock">{{ t.remaining <= 0 ? 'Fertig!' : formatClock(t.remaining) }}</span>
                <button v-if="t.remaining > 0" type="button" class="rz-running__btn" :aria-label="t.paused ? 'Weiter' : 'Pause'" @click="t.paused = !t.paused">
                    <rz-icon :name="t.paused ? 'play' : 'pause'" :size="18"/>
                </button>
                <button type="button" class="rz-running__btn" aria-label="Timer entfernen" @click="removeTimer(t.id)"><rz-icon name="x" :size="18"/></button>
            </div>
        </div>

        <footer class="rz-cook__nav">
            <v-btn variant="outlined" size="x-large" :disabled="index === 0" class="rz-cook__navbtn" @click="go(-1)">
                <rz-icon name="chevron-left" class="me-1"/> Zurück
            </v-btn>
            <v-btn v-if="index < steps.length - 1" color="primary" size="x-large" class="rz-cook__navbtn" @click="go(1)">
                Weiter <rz-icon name="chevron-right" class="ms-1"/>
            </v-btn>
            <v-btn v-else color="primary" size="x-large" class="rz-cook__navbtn" @click="finish()">
                <rz-icon name="check" class="me-1"/> Fertig
            </v-btn>
        </footer>
    </div>
</template>

<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {ApiApi} from '@/openapi'
// @ts-ignore Tandoor-Komponente ohne Typen (Options-API, JS)
import Instructions from '@/components/display/Instructions.vue'
import RzIcon from '../components/RzIcon.vue'
import {rzApi} from '../services/api'
import {foodLabel, formatAmount, unitLabel} from '../services/format'
import {findTimers, formatClock} from '../services/timers'
import type {EffectiveRecipe} from '../services/types'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()

const effective = ref<EffectiveRecipe | null>(null)
const recipeName = ref('')
const index = ref(Number(route.query.schritt ?? 0) || 0)
const loading = ref(true)

const steps = computed(() => effective.value?.steps ?? [])
const step = computed(() => steps.value[index.value] ?? null)
const stepIngredients = computed(() => (step.value?.ingredients ?? []).filter(i => !i.is_header))
const stepTimers = computed(() => {
    if (!step.value) return []
    const found = findTimers(`${step.value.instruction ?? ''} ${(step.value.notes ?? []).map(n => n.text).join(' ')}`)
    // Schrittdauer nur, wenn der Text selbst keine Zeitangabe enthält (sonst doppelt, z. B. „6–8 Minuten" + 8 Min.)
    if (step.value.time && found.length === 0) {
        found.unshift({label: `${step.value.time} Min.`, seconds: step.value.time * 60})
    }
    return found
})

// ---------------------------------------------------------------- Laden
onMounted(async () => {
    document.documentElement.classList.add('rz-immersive', 'rz-fullscreen')
    requestWakeLock()
    document.addEventListener('visibilitychange', onVisibility)
    try {
        const variant = route.query.variant ? Number(route.query.variant) : null
        const servings = route.query.servings ? Number(route.query.servings) : undefined
        const [eff, r] = await Promise.all([
            rzApi.effective(Number(props.id), variant, servings),
            new ApiApi().apiRecipeRetrieve({id: Number(props.id)}),
        ])
        effective.value = eff
        recipeName.value = r.name
        index.value = Math.min(index.value, Math.max(0, eff.steps.length - 1))
    } finally {
        loading.value = false
    }
})

onBeforeUnmount(() => {
    document.documentElement.classList.remove('rz-immersive', 'rz-fullscreen')
    document.removeEventListener('visibilitychange', onVisibility)
    wakeLock?.release().catch(() => undefined)
    clearInterval(tick)
})

// ---------------------------------------------------------------- Navigation
function go(delta: number) {
    const next = Math.min(steps.value.length - 1, Math.max(0, index.value + delta))
    if (next === index.value) return
    index.value = next
    router.replace({query: {...route.query, schritt: String(next)}})
    window.scrollTo({top: 0})
}

let touchX = 0
let touchY = 0

function touchStart(e: TouchEvent) {
    touchX = e.changedTouches[0]?.clientX ?? 0
    touchY = e.changedTouches[0]?.clientY ?? 0
}

function touchEnd(e: TouchEvent) {
    const t = e.changedTouches[0]
    if (!t) return
    const dx = t.clientX - touchX
    const dy = t.clientY - touchY
    if (Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 1.5) go(dx < 0 ? 1 : -1)
}

function close() {
    router.replace({name: 'RecipeViewPage', params: {id: props.id}})
}

function finish() {
    router.replace({name: 'RecipeViewPage', params: {id: props.id}, hash: '#rz-bewertungen'})
}

// ---------------------------------------------------------------- Wake Lock
let wakeLock: any = null
const wakeLockActive = ref(false)

async function requestWakeLock() {
    try {
        const nav = navigator as any
        if (!nav.wakeLock) return
        wakeLock = await nav.wakeLock.request('screen')
        wakeLockActive.value = true
        wakeLock.addEventListener('release', () => wakeLockActive.value = false)
    } catch {
        wakeLockActive.value = false
    }
}

function onVisibility() {
    // Browser geben den Wake Lock beim Wechsel in den Hintergrund frei → neu anfordern
    if (document.visibilityState === 'visible') requestWakeLock()
}

// ---------------------------------------------------------------- Timer
type RunningTimer = { id: number, label: string, remaining: number, paused: boolean, alerted: boolean }
const timers = ref<RunningTimer[]>([])
let nextTimerId = 1
let tick: ReturnType<typeof setInterval> | undefined
let lastTick = Date.now()

function startTimer(label: string, seconds: number) {
    timers.value.push({id: nextTimerId++, label, remaining: seconds, paused: false, alerted: false})
    if (!tick) {
        lastTick = Date.now()
        tick = setInterval(onTick, 250)
    }
}

function removeTimer(id: number) {
    timers.value = timers.value.filter(t => t.id !== id)
}

function onTick() {
    const now = Date.now()
    const dt = (now - lastTick) / 1000
    lastTick = now
    timers.value.forEach(t => {
        if (t.paused || t.remaining <= 0) return
        t.remaining -= dt
        if (t.remaining <= 0 && !t.alerted) {
            t.alerted = true
            alarm()
        }
    })
}

function alarm() {
    try {
        navigator.vibrate?.([300, 150, 300, 150, 300])
    } catch { /* nicht unterstützt */ }
    try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
        ;[0, 0.35, 0.7].forEach(offset => {
            const osc = ctx.createOscillator()
            const gain = ctx.createGain()
            osc.frequency.value = 880
            gain.gain.setValueAtTime(0.2, ctx.currentTime + offset)
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + offset + 0.3)
            osc.connect(gain).connect(ctx.destination)
            osc.start(ctx.currentTime + offset)
            osc.stop(ctx.currentTime + offset + 0.3)
        })
    } catch { /* kein Audio */ }
}
</script>

<style scoped>
.rz-cook {
    min-height: 100vh;
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
    background: var(--rz-bg);
    max-width: 760px;
    margin: 0 auto;
}

.rz-cook__head {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: calc(12px + env(safe-area-inset-top)) 20px 8px;
}

.rz-cook__progress {
    flex: 1;
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--rz-muted);
}

.rz-cook__bar {
    height: 4px;
    border-radius: 2px;
    background: var(--rz-surface);
    margin-top: 6px;
    overflow: hidden;
}

.rz-cook__bar div {
    height: 100%;
    background: var(--rz-accent);
    transition: width .2s;
}

.rz-cook__lock {
    color: var(--rz-border-strong);
}

.rz-cook__lock--on {
    color: var(--rz-accent);
}

.rz-cook__main {
    flex: 1;
    padding: 12px 20px 24px;
}

.rz-cook__recipe {
    color: var(--rz-muted);
    font-size: 0.875rem;
    margin: 0 0 6px;
}

.rz-cook__name {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--rz-ink);
    margin: 0 0 8px;
}

.rz-cook__badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    border: 1px solid var(--rz-accent);
    color: var(--rz-accent);
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 8px;
}

.rz-cook__ings {
    list-style: none;
    padding: 12px 16px;
    margin: 4px 0 18px;
    background: var(--rz-surface-soft);
    border-radius: var(--rz-radius-card);
}

.rz-cook__ings li {
    display: flex;
    gap: 12px;
    padding: 6px 0;
    font-size: 1.0625rem;
    color: var(--rz-ink);
}

.rz-cook__ings strong {
    flex: 0 0 86px;
}

.rz-cook__ings em {
    color: var(--rz-muted);
    font-style: normal;
}

.rz-cook__text {
    font-size: 1.375rem;
    line-height: 1.55;
    color: var(--rz-ink);
}

.rz-cook__text :deep(p) {
    margin: 0 0 0.6em;
    padding: 0;
}

.rz-cook__note {
    margin-top: 16px;
    background: var(--rz-surface-soft);
    border-radius: 14px;
    padding: 12px 14px;
}

.rz-cook__note span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: .04em;
    text-transform: uppercase;
    color: var(--rz-accent);
}

.rz-cook__note p {
    margin: 4px 0 0;
    font-size: 1.0625rem;
    color: var(--rz-ink-2);
}

.rz-cook__timers {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 20px;
}

.rz-timer-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 48px;
    padding: 0 18px;
    border-radius: 999px;
    border: 1px solid var(--rz-border-strong);
    background: var(--rz-bg);
    color: var(--rz-accent);
    font: inherit;
    font-weight: 700;
}

.rz-cook__running {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 0 20px 10px;
}

.rz-running {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 6px 6px 16px;
    border-radius: 14px;
    background: var(--rz-surface);
}

.rz-running--done {
    background: var(--rz-accent);
    color: #fff;
    animation: rz-blink 1s step-start infinite;
}

@keyframes rz-blink {
    50% {
        opacity: .65;
    }
}

.rz-running__label {
    flex: 1;
    font-size: 0.875rem;
}

.rz-running__clock {
    font-size: 1.25rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}

.rz-running__btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 0;
    background: rgba(255, 255, 255, .7);
    color: inherit;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.rz-cook__nav {
    position: sticky;
    bottom: 0;
    display: flex;
    gap: 12px;
    padding: 12px 20px calc(12px + env(safe-area-inset-bottom));
    background: var(--rz-bg);
    border-top: 1px solid var(--rz-border);
}

.rz-cook__navbtn {
    flex: 1 1 0;
    height: 56px !important;
}
</style>
