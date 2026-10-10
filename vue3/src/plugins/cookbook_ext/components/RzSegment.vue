<template>
    <div class="rz-segment" role="tablist">
        <button v-for="o in options" :key="String(o.value)" type="button" role="tab" class="rz-segment__item"
                :class="{'rz-segment__item--active': o.value === modelValue}" :aria-selected="o.value === modelValue"
                @click="emit('update:modelValue', o.value)">
            {{ o.label }}
        </button>
    </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: any, options: { value: any, label: string }[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: any] }>()
</script>

<style scoped>
.rz-segment {
    display: flex;
    background: var(--rz-surface);
    border-radius: 999px;
    padding: 4px;
    gap: 4px;
}

.rz-segment__item {
    flex: 1 1 0;
    min-height: 40px;
    border: 0;
    border-radius: 999px;
    background: transparent;
    color: var(--rz-ink-2);
    font: inherit;
    font-weight: 600;
    font-size: 0.9375rem;
    cursor: pointer;
    transition: background-color .15s, color .15s;
}

.rz-segment__item--active {
    background: var(--rz-accent);
    color: #fff;
}

.rz-segment__item:focus-visible {
    outline: 2px solid var(--rz-accent);
    outline-offset: 2px;
}
</style>
