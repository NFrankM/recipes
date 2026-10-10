import {getCookie} from '@/utils/cookie'
import {useDjangoUrls} from '@/composables/useDjangoUrls'
import type {CookLogPhoto, EffectiveRecipe, IngredientChange, RatingSummary, RecipeVariant, VariantStepNote} from './types'

/**
 * Kleiner Client für die Endpunkte von cookbook_ext.
 * Bewusst getrennt vom generierten Tandoor-Client (src/openapi), damit dieser nicht neu generiert werden muss.
 */
export class RzApiError extends Error {
    constructor(public status: number, public data: any) {
        super(RzApiError.text(data) || `HTTP ${status}`)
    }

    /** Erste lesbare Fehlermeldung aus einer DRF-Antwort */
    static text(data: any): string {
        if (!data) return ''
        if (typeof data === 'string') return data
        if (Array.isArray(data)) return RzApiError.text(data[0])
        if (data.detail) return String(data.detail)
        if (data.msg) return String(data.msg)
        const first = Object.values(data)[0]
        return RzApiError.text(first)
    }
}

async function request<T>(method: string, path: string, body?: any, query?: Record<string, any>): Promise<T> {
    let url = useDjangoUrls().getDjangoUrl(path)
    if (query) {
        const params = new URLSearchParams()
        Object.entries(query).forEach(([k, v]) => {
            if (v === undefined || v === null || v === '') return
            if (Array.isArray(v)) v.forEach(x => params.append(k, String(x)))
            else params.append(k, String(v))
        })
        const qs = params.toString()
        if (qs) url += '?' + qs
    }
    const headers: Record<string, string> = {'X-CSRFToken': getCookie('csrftoken') ?? '', 'Accept': 'application/json'}
    let payload: BodyInit | undefined
    if (body instanceof FormData) {
        payload = body
    } else if (body !== undefined) {
        headers['Content-Type'] = 'application/json'
        payload = JSON.stringify(body)
    }
    const r = await fetch(url, {method, headers, body: payload, credentials: 'same-origin'})
    if (r.status === 204) return undefined as T
    const data = await r.json().catch(() => null)
    if (!r.ok) throw new RzApiError(r.status, data)
    return data as T
}

export const rzApi = {
    effective(recipeId: number, variantId: number | null, servings?: number) {
        return request<EffectiveRecipe>('GET', `api/effective-recipe/${recipeId}`, undefined, {variant: variantId, servings})
    },
    variants(recipeId: number) {
        return request<RecipeVariant[]>('GET', 'api/recipe-variant', undefined, {recipe: recipeId})
    },
    createVariant(recipeId: number, name = 'Unsere Version', isDefault = true) {
        return request<RecipeVariant>('POST', 'api/recipe-variant', {recipe: recipeId, name, is_default: isDefault})
    },
    updateVariant(id: number, data: Partial<RecipeVariant>) {
        return request<RecipeVariant>('PATCH', `api/recipe-variant/${id}`, data)
    },
    deleteVariant(id: number) {
        return request<void>('DELETE', `api/recipe-variant/${id}`)
    },
    variantToShopping(variantId: number, servings: number) {
        return request<{ msg: string, list_recipe: number, entries: number }>('POST', `api/recipe-variant/${variantId}/shopping`, {servings})
    },

    createChange(change: IngredientChange) {
        return request<IngredientChange>('POST', 'api/variant-ingredient-change', change)
    },
    updateChange(id: number, change: Partial<IngredientChange>) {
        return request<IngredientChange>('PATCH', `api/variant-ingredient-change/${id}`, change)
    },
    deleteChange(id: number) {
        return request<void>('DELETE', `api/variant-ingredient-change/${id}`)
    },

    createNote(note: VariantStepNote) {
        return request<VariantStepNote>('POST', 'api/variant-step-note', note)
    },
    updateNote(id: number, note: Partial<VariantStepNote>) {
        return request<VariantStepNote>('PATCH', `api/variant-step-note/${id}`, note)
    },
    deleteNote(id: number) {
        return request<void>('DELETE', `api/variant-step-note/${id}`)
    },

    ratings(recipeIds: number[]) {
        return request<RatingSummary[]>('GET', 'api/recipe-rating', undefined, {recipe: recipeIds})
    },
    photos(recipeId: number) {
        return request<CookLogPhoto[]>('GET', 'api/cook-log-photo', undefined, {recipe: recipeId})
    },
    uploadPhoto(cookLogId: number, file: File) {
        const fd = new FormData()
        fd.append('cook_log', String(cookLogId))
        fd.append('image', file)
        return request<CookLogPhoto>('POST', 'api/cook-log-photo', fd)
    },
    deletePhoto(id: number) {
        return request<void>('DELETE', `api/cook-log-photo/${id}`)
    },
}
