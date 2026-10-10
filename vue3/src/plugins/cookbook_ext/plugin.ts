import {TandoorPlugin} from '@/types/Plugins.ts'
import vuetify from '@/vuetify'
import {applyRezeptTheme} from './theme/applyTheme'
import RzBottomNav from './components/RzBottomNav.vue'

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

    routes: [
        // Übersicht ersetzt Tandoors Startseite (gleicher Trick wie bei der Rezeptansicht, E6)
        {
            path: '/', name: 'StartPage', meta: {title: 'Home'},
            component: () => import('@/plugins/cookbook_ext/pages/RzHomePage.vue'),
        },
        {
            path: '/start-klassisch', name: 'StartPageTandoor', meta: {title: 'Home'},
            component: () => import('@/pages/StartPage.vue'),
        },
        {
            path: '/recipe/:id/kochen', name: 'RzCookPage', props: true, meta: {title: 'Kochmodus'},
            component: () => import('@/plugins/cookbook_ext/pages/RzCookPage.vue'),
        },
        {
            path: '/einkauf', name: 'RzShoppingPage', meta: {title: 'Shopping_list'},
            component: () => import('@/plugins/cookbook_ext/pages/RzShoppingPage.vue'),
        },
        {
            path: '/import', name: 'RzImportPage', meta: {title: 'Import'},
            component: () => import('@/plugins/cookbook_ext/pages/RzImportPage.vue'),
        },
        // Ersetzt Tandoors Rezeptansicht: gleicher Routenname → vue-router entfernt die Tandoor-Route beim Hinzufügen,
        // alle bestehenden Links ({name: 'RecipeViewPage'}) führen damit automatisch zur neuen Ansicht (ENTSCHEIDUNGEN.md E6).
        {
            path: '/recipe/:id', name: 'RecipeViewPage', props: true, meta: {title: 'Recipe'},
            component: () => import('@/plugins/cookbook_ext/pages/RzRecipePage.vue'),
        },
        // Tandoors ursprüngliche Ansicht bleibt erreichbar (Share-Links, Nährwerte, Eigenschaften …)
        {
            path: '/recipe/:id/klassisch', name: 'RecipeViewPageTandoor', props: true, meta: {title: 'Recipe'},
            component: () => import('@/pages/RecipeViewPage.vue'),
        },
    ],
    settingRoutes: [],

    navigationDrawer: [],
    bottomNavigation: [],
    userNavigation: [],

    // eigene untere Navigation (Hook in Tandoor.vue, siehe projekt/CORE_CHANGES.md)
    layoutComponents: [RzBottomNav],
}
