<template>
    <div class="rz-stepper" role="group" :aria-label="label">
        <button type="button" class="rz-stepper__btn" :disabled="modelValue <= min" aria-label="weniger" @click="change(-1)">
            <rz-icon name="minus" :size="20"/>
        </button>
        <span class="rz-stepper__value" aria-live="polite">{{ display }}</span>
        <button type="button" class="rz-stepper__btn" :disabled="modelValue >= max" aria-label="mehr" @click="change(1)">
            <rz-icon name="plus" :size="20"/>
        </button>
    </div>
</template>

<script setup lang="ts">
import {computed} from 'vue'
import RzIcon from './RzIcon.vue'

const props = withDefaults(defineProps<{ modelValue: number, min?: number, max?: number, label?: string }>(), {
    min: 1,
    max: 99,
    label: 'Portionen',
})
const emit = defineEmits<{ 'update:modelValue': [value: number] }>()

const display = computed(() => new Intl.NumberFormat('de-DE', {maximumFractionDigits: 1}).format(props.modelValue))

function change(delta: number) {
    // bei krummen Werten (z. B. 1,5) zuerst auf ganze Zahl runden
    const base = delta > 0 ? Math.floor(props.modelValue) : Math.ceil(props.modelValue)
    emit('update:modelValue', Math.min(props.max, Math.max(props.min, base + delta)))
}
</script>

<style scoped>
.rz-stepper {
    display: inline-flex;
    align-items: center;
    background: var(--rz-surface);
    border-radius: 999px;
    padding: 2px;
}

.rz-stepper__btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 0;
    background: transparent;
    color: var(--rz-ink);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
}

.rz-stepper__btn:disabled {
    color: var(--rz-border-strong);
    cursor: default;
}

.rz-stepper__btn:not(:disabled):active {
    background: #fff;
}

.rz-stepper__value {
    min-width: 36px;
    text-align: center;
    font-weight: 700;
    font-size: 1.0625rem;
    color: var(--rz-ink);
}
</style>
