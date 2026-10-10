<template>
    <svg class="rz-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" :stroke-width="strokeWidth"
         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path v-for="(d, i) in paths" :key="i" :d="d"/>
    </svg>
</template>

<script setup lang="ts">
/**
 * Schlichte Strich-Icons (24er Raster, 1,75 px Strich) – Design-Vorgabe „keine gefüllten Icons, keine Emojis“.
 * Eigene, einfache Pfade im Stil gängiger Line-Icon-Sets.
 */
import {computed} from 'vue'

const ICONS: Record<string, string[]> = {
    'arrow-left': ['M19 12H5', 'M12 19l-7-7 7-7'],
    'more': ['M12 12h.01', 'M19 12h.01', 'M5 12h.01'],
    'clock': ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z', 'M12 7v5l3 2'],
    'users': ['M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20', 'M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z', 'M20 20v-1.5a3.5 3.5 0 0 0-2.5-3.35', 'M15.5 4.15a3.5 3.5 0 0 1 0 6.7'],
    'minus': ['M5 12h14'],
    'plus': ['M12 5v14', 'M5 12h14'],
    'cart': ['M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.6a2 2 0 0 0 2-1.5L21 8H6.2', 'M10 21h.01', 'M17 21h.01'],
    'pencil': ['M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z'],
    'check': ['M20 6L9 17l-5-5'],
    'x': ['M18 6L6 18', 'M6 6l12 12'],
    'trash': ['M4 7h16', 'M10 11v6', 'M14 11v6', 'M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12', 'M9 7V4h6v3'],
    'undo': ['M9 14L4 9l5-5', 'M4 9h10.5a5.5 5.5 0 0 1 0 11H11'],
    'camera': ['M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z', 'M12 17a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z'],
    'note': ['M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z', 'M14 3v6h6', 'M8 13h8', 'M8 17h5'],
    'timer': ['M10 2h4', 'M12 14l3-3', 'M12 22a8 8 0 1 0 0-16 8 8 0 0 0 0 16z'],
    'chevron-right': ['M9 18l6-6-6-6'],
    'chevron-down': ['M6 9l6 6 6-6'],
    'star': ['M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z'],
    'swap': ['M7 16V4', 'M3 8l4-4 4 4', 'M17 8v12', 'M21 16l-4 4-4-4'],
    'book': ['M4 19.5A2.5 2.5 0 0 1 6.5 17H20', 'M6.5 3H20v18H6.5A2.5 2.5 0 0 1 4 18.5v-13A2.5 2.5 0 0 1 6.5 3z'],
    'external': ['M15 3h6v6', 'M10 14L21 3', 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6'],
}

const props = withDefaults(defineProps<{ name: string, size?: number | string, strokeWidth?: number | string }>(), {
    size: 22,
    strokeWidth: 1.75,
})

const paths = computed(() => ICONS[props.name] ?? [])
</script>

<style scoped>
.rz-icon {
    display: inline-block;
    flex-shrink: 0;
    vertical-align: middle;
}
</style>
