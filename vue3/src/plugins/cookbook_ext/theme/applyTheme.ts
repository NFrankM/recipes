import type {App} from 'vue'
import {RZ_COLORS} from './tokens'
import './rezept-theme.css'

type VuetifyInstance = {
    theme: { themes: { value: Record<string, any> } },
    defaults: { value: Record<string, any> },
}

/**
 * Macht das Rezept-App-Design zum Standard, ohne Tandoors vuetify.ts zu ändern.
 *
 * Tandoor erzeugt die Vuetify-Instanz in src/vuetify.ts und lädt Plugins (diese Datei über plugin.ts)
 * bevor die App gemountet wird. Theme-Farben und Komponenten-Defaults sind in Vuetify reaktive Refs –
 * wir überschreiben deshalb hier zentral:
 *  - das Theme „light" (Tandoors Standard-Theme, wird auch von UserPreferenceStore.updateTheme() gesetzt)
 *  - globale Defaults für Buttons, Karten, Chips, Eingabefelder
 * Tandoors eigene Defaults (z. B. VChip.closeIcon, VCardActions) bleiben erhalten (Merge statt Ersetzen).
 */
export function applyRezeptTheme(vuetify: VuetifyInstance) {
    const themes = vuetify.theme.themes.value
    const light = themes.light

    light.colors = {
        ...light.colors,
        background: RZ_COLORS['rz-bg'],
        surface: '#FFFFFF',
        'surface-bright': '#FFFFFF',
        'surface-light': RZ_COLORS['rz-surface'],
        'surface-variant': RZ_COLORS['rz-ink-2'],
        'on-surface-variant': '#FFFFFF',
        'on-background': RZ_COLORS['rz-ink'],
        'on-surface': RZ_COLORS['rz-ink'],

        primary: RZ_COLORS['rz-accent'],
        'primary-darken-1': RZ_COLORS['rz-accent-dark'],
        secondary: RZ_COLORS['rz-muted'],
        'secondary-darken-1': RZ_COLORS['rz-ink-2'],
        info: RZ_COLORS['rz-accent'],
        success: '#4A7C64',
        warning: '#B7832F',
        error: '#B3412F',

        // Tandoor-eigene semantische Farben in ruhigem Blaugrau
        tandoor: RZ_COLORS['rz-accent-dark'],
        save: RZ_COLORS['rz-accent'],
        create: RZ_COLORS['rz-accent'],
        edit: RZ_COLORS['rz-muted'],
        delete: '#B3412F',
        cancel: RZ_COLORS['rz-muted'],
        recipeImagePlaceholderBg: RZ_COLORS['rz-surface'],

        ...RZ_COLORS,
    }
    light.variables = {
        ...light.variables,
        'border-color': RZ_COLORS['rz-border-strong'],
        'border-opacity': 0.7,
        'high-emphasis-opacity': 1,
        'medium-emphasis-opacity': 0.78,
        'hover-opacity': 0.05,
        'theme-code': RZ_COLORS['rz-surface-soft'],
        'theme-on-code': RZ_COLORS['rz-ink'],
    }

    // Akzentfarben auch im dunklen Theme (falls jemand „Tandoor Dark" wählt) angleichen
    if (themes.dark) {
        themes.dark.colors = {
            ...themes.dark.colors,
            primary: '#8FA9BE',
            tandoor: '#8FA9BE',
            save: '#8FA9BE',
            create: '#8FA9BE',
            ...RZ_COLORS,
        }
    }

    const d = vuetify.defaults.value
    const merge = (key: string, values: Record<string, any>) => {
        d[key] = {...(d[key] ?? {}), ...values}
    }

    merge('VBtn', {elevation: 0})  // Radius per CSS, damit Icon-Buttons rund bleiben
    merge('VCard', {rounded: 'rz-card', elevation: 0, border: true})
    merge('VSheet', {rounded: 'rz-card'})
    merge('VChip', {rounded: 'pill', variant: 'flat', color: 'rz-surface'})
    merge('VAlert', {rounded: 'rz', variant: 'tonal'})
    merge('VRating', {color: 'rz-accent-dark', activeColor: 'rz-accent-dark'})
    merge('VTabs', {color: 'primary'})
    merge('VCheckbox', {color: 'primary'})
    merge('VCheckboxBtn', {color: 'primary'})
    merge('VRadio', {color: 'primary'})
    merge('VProgressLinear', {color: 'primary'})
    merge('VProgressCircular', {color: 'primary'})
    merge('VAppBar', {flat: true})
    merge('VBottomNavigation', {elevation: 0, color: 'primary'})

    const field = {variant: 'outlined', rounded: 'rz', color: 'primary'}
    for (const key of ['VTextField', 'VTextarea', 'VSelect', 'VAutocomplete', 'VCombobox', 'VNumberInput', 'VFileInput', 'VDateInput']) {
        merge(key, field)
    }
}

/** Optional als Vue-Plugin nutzbar: app.use(rezeptTheme, vuetify) */
export default {
    install(_app: App, vuetify: VuetifyInstance) {
        applyRezeptTheme(vuetify)
    },
}
