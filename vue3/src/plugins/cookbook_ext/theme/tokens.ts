/**
 * Design-Tokens der Rezept-App (Quelle: CLAUDE.md, Abschnitt „Design").
 * Werden als Vuetify-Theme-Farben (rz-*) und als CSS-Variablen (--rz-*) bereitgestellt.
 */
export const RZ_COLORS = {
    'rz-bg': '#FFFFFF',
    'rz-surface': '#EEF2F5',
    'rz-surface-soft': '#F2F5F8',
    'rz-border': '#E3E9EE',
    'rz-border-strong': '#C9D4DD',
    'rz-ink': '#1E2A35',
    'rz-ink-2': '#2E3E4C',
    'rz-muted': '#52687A',
    'rz-accent': '#3E5A70',
    'rz-accent-dark': '#2F4A5E',
} as const

export const RZ_RADIUS = {
    field: 14,
    card: 16,
    sheet: 24,
} as const

export const RZ_FONT = `'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`

/** Mindestgröße für Touch-Ziele (px) */
export const RZ_TOUCH = 44
