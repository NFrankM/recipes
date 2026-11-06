import {computed} from 'vue'
import {useUserPreferenceStore} from '@/stores/UserPreferenceStore'

/** Darf der Benutzer im aktiven Space schreiben (Gruppe user oder admin)? Gäste nur lesen. */
export function useCanWrite() {
    const prefs = useUserPreferenceStore()
    return computed(() => {
        if (prefs.userSettings?.user?.isSuperuser) return true
        const groups = prefs.activeUserSpace?.groups ?? []
        return groups.some(g => g.name === 'user' || g.name === 'admin')
    })
}
