import type {EffectiveIngredient, Named} from './types'

const FRACTIONS: [number, string][] = [[0.25, '¼'], [1 / 3, '⅓'], [0.5, '½'], [2 / 3, '⅔'], [0.75, '¾']]
const NO_FRACTION_UNITS = new Set(['g', 'kg', 'ml', 'l', 'mg', 'cl', 'dl'])

/** Menge hübsch formatieren: 1.5 → „1½", 200 → „200", 0.333 → „⅓", 12.345 g → „12,35" */
export function formatAmount(amount: number, unit?: Named | null): string {
    if (!isFinite(amount) || amount <= 0) return ''
    const unitName = (unit?.name ?? '').toLowerCase()
    const whole = Math.floor(amount)
    const rest = amount - whole
    if (!NO_FRACTION_UNITS.has(unitName) && whole < 10) {
        if (rest < 0.02) return String(whole)
        for (const [value, sign] of FRACTIONS) {
            if (Math.abs(rest - value) < 0.02) return (whole > 0 ? String(whole) : '') + sign
        }
    }
    const digits = amount >= 100 ? 0 : (amount >= 10 ? 1 : 2)
    return new Intl.NumberFormat('de-DE', {maximumFractionDigits: digits}).format(amount)
}

function name(obj: Named | null | undefined, plural: boolean): string {
    if (!obj) return ''
    return plural && obj.plural_name ? obj.plural_name : obj.name
}

export function unitLabel(i: Pick<EffectiveIngredient, 'unit' | 'amount' | 'no_amount'>): string {
    return name(i.unit, !i.no_amount && i.amount > 1)
}

export function foodLabel(i: Pick<EffectiveIngredient, 'food' | 'amount' | 'no_amount' | 'unit'>): string {
    // „2 Eier", aber „200 g Mehl" (Plural am Lebensmittel nur ohne Einheit)
    return name(i.food, !i.no_amount && i.amount > 1 && !i.unit)
}

/** „200 g Mehl" in einer Zeile */
export function ingredientText(i: EffectiveIngredient | { food: Named | null, unit: Named | null, amount: number, no_amount?: boolean }): string {
    const noAmount = 'no_amount' in i ? !!i.no_amount : false
    const amount = noAmount ? '' : formatAmount(i.amount, i.unit)
    const unit = noAmount ? '' : name(i.unit, i.amount > 1)
    return [amount, unit, name(i.food, !noAmount && i.amount > 1 && !i.unit)].filter(Boolean).join(' ')
}

export function formatMinutes(min: number): string {
    if (!min) return ''
    if (min < 60) return `${min} Min.`
    const h = Math.floor(min / 60)
    const m = min % 60
    return m ? `${h} Std. ${m} Min.` : `${h} Std.`
}
