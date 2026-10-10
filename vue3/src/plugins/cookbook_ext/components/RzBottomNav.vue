<template>
    <nav v-if="visible" class="rz-nav" aria-label="Hauptnavigation">
        <router-link v-for="item in items" :key="item.label" :to="item.to" class="rz-nav__item"
                     :class="{'rz-nav__item--active': item.active()}">
            <rz-icon :name="item.icon" :size="24" :stroke-width="item.active() ? 2.1 : 1.75"/>
            <span>{{ item.label }}</span>
        </router-link>
    </nav>
</template>

<script setup lang="ts">
/**
 * Eigene untere Navigation (Rezepte, Suche, Einkauf, Import) – ersetzt auf dem Handy Tandoors Leiste.
 * Wird über den Layout-Hook in Tandoor.vue gerendert (projekt/CORE_CHANGES.md).
 */
import {computed, watchEffect} from 'vue'
import {useRoute} from 'vue-router'
import {useDisplay} from 'vuetify'
import {useUserPreferenceStore} from '@/stores/UserPreferenceStore'
import RzIcon from './RzIcon.vue'

const route = useRoute()
const {lgAndUp} = useDisplay()
const prefs = useUserPreferenceStore()

const HIDDEN_ON = new Set(['RzCookPage'])

const visible = computed(() => prefs.isAuthenticated && !lgAndUp.value && !prefs.isPrintMode && !HIDDEN_ON.has(String(route.name)))

watchEffect(() => document.documentElement.classList.toggle('rz-own-nav', visible.value))

const is = (...names: string[]) => () => names.includes(String(route.name))

const items = [
    {label: 'Rezepte', icon: 'book', to: {name: 'StartPage'}, active: is('StartPage', 'RecipeViewPage', 'RecipeViewPageTandoor')},
    {label: 'Suche', icon: 'search', to: {name: 'SearchPage'}, active: is('SearchPage')},
    {label: 'Einkauf', icon: 'cart', to: {name: 'RzShoppingPage'}, active: is('RzShoppingPage', 'ShoppingListPage')},
    {label: 'Import', icon: 'import', to: {name: 'RzImportPage'}, active: is('RzImportPage', 'RecipeImportPage')},
]
</script>

<style scoped>
.rz-nav {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1004;
    display: flex;
    background: var(--rz-bg);
    border-top: 1px solid var(--rz-border);
    padding-bottom: env(safe-area-inset-bottom);
}

.rz-nav__item {
    flex: 1 1 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    min-height: 60px;
    color: var(--rz-muted);
    text-decoration: none;
    font-size: 0.75rem;
    font-weight: 500;
}

.rz-nav__item--active {
    color: var(--rz-accent);
    font-weight: 700;
}
</style>
