/**
 * Design-Tokens der Rezept-App (Quelle: CLAUDE.md, Abschnitt „Design"; Blaugrau/Schrift seit 2026-11 passend zum Logo).
 * Werden als Vuetify-Theme-Farben (rz-*) und als CSS-Variablen (--rz-*) bereitgestellt.
 */
export const RZ_COLORS = {
    'rz-bg': '#FFFFFF',
    'rz-surface': '#EEF2F5',
    'rz-surface-soft': '#F2F5F8',
    'rz-border': '#E3E9EE',
    'rz-border-strong': '#C9D4DD',
    'rz-ink': '#2E3A46',
    'rz-ink-2': '#3B4A58',
    'rz-muted': '#5E6F80',
    'rz-accent': '#5D7488',
    'rz-accent-dark': '#485D71',
} as const

export const RZ_RADIUS = {
    field: 14,
    card: 16,
    sheet: 24,
} as const

export const RZ_FONT = `'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`

/** Mindestgröße für Touch-Ziele (px) */
export const RZ_TOUCH = 44
