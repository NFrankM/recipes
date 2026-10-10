import {TandoorPlugin} from '@/types/Plugins.ts'
import vuetify from '@/vuetify'
import {applyRezeptTheme} from './theme/applyTheme'

/**
 * Frontend-Teil der Rezept-App-Erweiterungen (Gegenstück zu recipes/plugins/cookbook_ext).
 * Wird von Tandoor automatisch über src/types/Plugins.ts (import.meta.glob) geladen –
 * noch bevor die App gemountet wird. Deshalb können wir hier das Theme setzen.
 */
applyRezeptTheme(vuetify as any)

export const plugin: TandoorPlugin = {
    name: 'Rezept-App',
    basePath: 'cookbook_ext',
    defaultLocale: import('@/plugins/cookbook_ext/locales/en.json'),
    localeFiles: import.meta.glob('@/plugins/cookbook_ext/locales/*.json'),

    routes: [],
    settingRoutes: [],

    navigationDrawer: [],
    bottomNavigation: [],
    userNavigation: [],
}
