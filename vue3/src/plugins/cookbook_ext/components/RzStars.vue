<template>
    <div class="rz-stars" :class="{'rz-stars--input': input}" role="img" :aria-label="`${display} von 5 Sternen`">
        <component :is="input ? 'button' : 'span'" v-for="n in 5" :key="n" class="rz-star" :type="input ? 'button' : undefined"
                   :style="{width: input ? '44px' : `${size}px`, height: input ? '44px' : `${size}px`}"
                   :aria-label="input ? `${n} Sterne` : undefined" @click="input && set(n)">
            <svg :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true">
                <defs>
                    <clipPath :id="`${uid}-${n}`">
                        <rect x="0" y="0" :width="24 * fill(n)" height="24"/>
                    </clipPath>
                </defs>
                <path :d="STAR" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
                <path :d="STAR" fill="currentColor" :clip-path="`url(#${uid}-${n})`"/>
            </svg>
        </component>
    </div>
</template>

<script setup lang="ts">
import {computed} from 'vue'

const STAR = 'M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z'

const props = withDefaults(defineProps<{ modelValue?: number | null, size?: number, input?: boolean }>(), {
    modelValue: 0,
    size: 16,
    input: false,
})
const emit = defineEmits<{ 'update:modelValue': [value: number] }>()

const uid = `rzs${Math.random().toString(36).slice(2, 8)}`
const display = computed(() => Math.round((props.modelValue ?? 0) * 10) / 10)

function fill(n: number) {
    const v = props.modelValue ?? 0
    return Math.max(0, Math.min(1, v - (n - 1)))
}

function set(n: number) {
    emit('update:modelValue', props.modelValue === n ? 0 : n)
}
</script>

<style scoped>
.rz-stars {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    color: var(--rz-accent-dark);
}

.rz-star {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: 0;
    padding: 0;
    color: inherit;
}

.rz-stars--input .rz-star {
    cursor: pointer;
    border-radius: 50%;
}

.rz-stars--input .rz-star:focus-visible {
    outline: 2px solid var(--rz-accent);
}
</style>
