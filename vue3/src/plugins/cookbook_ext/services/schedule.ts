/**
 * Zeitplan-Rechner: aus den Schrittzeiten (Minuten) Uhrzeiten berechnen.
 * - vorwärts: „Ich starte um 8 Uhr“ → Beginn jedes Schritts
 * - rückwärts: „Das Brot soll um 12 Uhr fertig sein“ → nötige Startzeit
 * Ein Schritt mit `parallel` läuft neben dem nächsten her: er beginnt zur selben Zeit wie der nächste Schritt
 * und schiebt die folgenden Schritte nicht nach hinten (zählt nicht zur Gesamtdauer, solange er nicht länger dauert).
 */

export type ScheduleStep = { time: number, parallel?: boolean, name?: string, instruction?: string }
export type ScheduleItem = { index: number, start: Date, end: Date, minutes: number, parallel: boolean }
export type Schedule = { items: ScheduleItem[], start: Date, end: Date, totalMinutes: number, multiDay: boolean }

const MIN = 60_000

/** Versatz jedes Schritts ab Start (Minuten) und Gesamtdauer */
function offsets(steps: ScheduleStep[]) {
    let cursor = 0
    let maxEnd = 0
    const items = steps.map((s, index) => {
        const minutes = Math.max(0, Math.round(Number(s.time) || 0))
        const start = cursor
        const end = start + minutes
        if (!s.parallel) cursor = end
        maxEnd = Math.max(maxEnd, end)
        return {index, start, end, minutes, parallel: !!s.parallel}
    })
    return {items, total: Math.max(cursor, maxEnd)}
}

export function buildSchedule(steps: ScheduleStep[], anchor: Date, mode: 'start' | 'end' = 'start'): Schedule {
    const {items, total} = offsets(steps)
    const start = mode === 'start' ? new Date(anchor.getTime()) : new Date(anchor.getTime() - total * MIN)
    const end = new Date(start.getTime() + total * MIN)
    return {
        items: items.map(i => ({
            index: i.index, minutes: i.minutes, parallel: i.parallel,
            start: new Date(start.getTime() + i.start * MIN), end: new Date(start.getTime() + i.end * MIN),
        })),
        start, end, totalMinutes: total,
        multiDay: start.toDateString() !== end.toDateString(),
    }
}

/** „Sa 20:00“ (mit Wochentag) oder „20:00“ */
export function formatSlot(d: Date, withDay: boolean): string {
    const time = d.toLocaleTimeString('de-DE', {hour: '2-digit', minute: '2-digit'})
    if (!withDay) return time
    const day = d.toLocaleDateString('de-DE', {weekday: 'short'}).replace('.', '')
    return `${day} ${time}`
}

/** Dauer lesbar, auch über mehrere Tage: „1 Tag 4 Std.“, „2 Std. 15 Min.“, „45 Min.“ */
export function formatDuration(min: number): string {
    if (!min) return '0 Min.'
    const d = Math.floor(min / 1440)
    const h = Math.floor((min % 1440) / 60)
    const m = min % 60
    return [d ? `${d} ${d === 1 ? 'Tag' : 'Tage'}` : '', h ? `${h} Std.` : '', m ? `${m} Min.` : ''].filter(Boolean).join(' ')
}

/** Wert für <input type="datetime-local"> in lokaler Zeit */
export function toLocalInput(d: Date): string {
    const p = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`
}

/** Jetzt, aufgerundet auf die nächsten 5 Minuten */
export function roundedNow(now = new Date()): Date {
    const d = new Date(now.getTime())
    d.setSeconds(0, 0)
    d.setMinutes(Math.ceil(d.getMinutes() / 5) * 5)
    return d
}

function icsDate(d: Date): string {
    return d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
}

function icsText(s: string): string {
    return s.replace(/\\/g, '\\\\').replace(/;/g, '\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n')
}

/** Zeilen über 75 Zeichen falten (RFC 5545) */
function fold(line: string): string {
    const out: string[] = []
    let rest = line
    while (rest.length > 74) {
        out.push(rest.slice(0, 74))
        rest = ' ' + rest.slice(74)
    }
    out.push(rest)
    return out.join('\r\n')
}

/** Kalenderdatei: ein Termin je Schritt mit Zeit, jeweils mit Erinnerung zum Beginn */
export function scheduleToIcs(recipeName: string, steps: ScheduleStep[], schedule: Schedule, uidBase = 'rezepteapp', now = new Date()): string {
    const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Rezepteapp//Zeitplan//DE', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH']
    schedule.items.forEach(item => {
        const step = steps[item.index] ?? {time: 0}
        const label = step.name?.trim() || (step.instruction ?? '').trim().split(/(?<=[.!?])\s/)[0]?.slice(0, 60) || `Schritt ${item.index + 1}`
        const end = item.minutes ? item.end : new Date(item.start.getTime() + 5 * MIN)
        lines.push('BEGIN:VEVENT',
            `UID:${uidBase}-${schedule.start.getTime()}-${item.index}@rezepteapp`,
            `DTSTAMP:${icsDate(now)}`,
            `DTSTART:${icsDate(item.start)}`,
            `DTEND:${icsDate(end)}`,
            fold(`SUMMARY:${icsText(`${recipeName}: ${item.index + 1}. ${label}`)}`),
            fold(`DESCRIPTION:${icsText(step.instruction ?? '')}`),
            'BEGIN:VALARM', 'ACTION:DISPLAY', fold(`DESCRIPTION:${icsText(`${recipeName}: ${label}`)}`), 'TRIGGER:PT0M', 'END:VALARM',
            'END:VEVENT')
    })
    lines.push('END:VCALENDAR')
    return lines.join('\r\n') + '\r\n'
}
