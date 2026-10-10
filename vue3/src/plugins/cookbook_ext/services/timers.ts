/**
 * Findet Zeitangaben in Schritt-Texten, z. B. „10 Minuten", „6–8 Min.", „1 Stunde", „30 Sek.".
 * Bei Spannen wird der kleinere Wert als Timer genommen (lieber früher nachsehen).
 */
export type FoundTimer = { label: string, seconds: number }

const RE = /(\d+(?:[.,]\d+)?)(?:\s*(?:-|–|bis)\s*(\d+(?:[.,]\d+)?))?\s*(Stunden|Stunde|Std\.?|Minuten|Minute|Min\.?|Sekunden|Sekunde|Sek\.?)(?![a-zäöü])/gi

function unitSeconds(unit: string): number {
    const u = unit.toLowerCase()
    if (u.startsWith('st')) return 3600
    if (u.startsWith('se')) return 1
    return 60
}

export function findTimers(text: string): FoundTimer[] {
    const out: FoundTimer[] = []
    const seen = new Set<number>()
    for (const m of (text ?? '').matchAll(RE)) {
        const from = parseFloat((m[1] ?? '0').replace(',', '.'))
        const seconds = Math.round(from * unitSeconds(m[3] ?? 'min'))
        if (!seconds || seen.has(seconds)) continue
        seen.add(seconds)
        out.push({label: m[0].replace(/\s+/g, ' ').trim(), seconds})
    }
    return out
}

export function formatClock(total: number): string {
    const s = Math.max(0, Math.round(total))
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const sec = s % 60
    const mm = String(m).padStart(h ? 2 : 1, '0')
    return (h ? `${h}:` : '') + `${mm}:${String(sec).padStart(2, '0')}`
}
