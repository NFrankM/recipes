/** Typen der Erweiterungs-API (siehe projekt/API_ERWEITERUNGEN.md) */

export type Named = { id: number, name: string, plural_name?: string | null }

export type IngredientStatus = 'original' | 'changed' | 'added' | 'removed'

export type EffectiveIngredient = {
    status: IngredientStatus
    ingredient: number | null
    change: number | null
    food: Named | null
    unit: Named | null
    amount: number
    base_amount: number
    note: string
    is_header: boolean
    no_amount: boolean
    order: number
    original: null | { food: Named | null, unit: Named | null, amount: number, note: string }
}

export type StepNote = { id: number, text: string, time: number, position: number }

export type EffectiveStep = {
    id: number | null
    name: string
    instruction: string
    instructions_markdown: string | null
    time: number
    is_added: boolean
    added_note: StepNote | null
    notes: StepNote[]
    ingredients: EffectiveIngredient[]
    removed_ingredients: EffectiveIngredient[]
}

export type EffectiveRecipe = {
    recipe: number
    variant: number | null
    variant_name: string | null
    base_servings: number
    servings: number
    factor: number
    steps: EffectiveStep[]
    orphaned_changes: number[]
    orphaned_notes: number[]
}

export type ChangeAction = 'replace' | 'add' | 'remove'

export type IngredientChange = {
    id?: number
    variant: number
    action: ChangeAction
    ingredient?: number | null
    step?: number | null
    food?: number | null
    food_name?: string
    food_data?: Named | null
    unit?: number | null
    unit_name?: string
    unit_data?: Named | null
    amount?: number | null
    note?: string
    order?: number
}

export type VariantStepNote = {
    id?: number
    variant: number
    step?: number | null
    position?: number
    text: string
    time?: number
}

export type RecipeVariant = {
    id: number
    recipe: number
    name: string
    is_default: boolean
    created_by: { id: number, display_name: string }
    created_at: string
    updated_at: string
    ingredient_changes: IngredientChange[]
    step_notes: VariantStepNote[]
}

export type RatingSummary = { recipe: number, average: number | null, count: number, cooked: number }

export type CookLogPhoto = { id: number, cook_log: number, recipe: number, image: string, created_at: string }
