// Zeitplan-Rechner. Ausführen: node --experimental-strip-types --test vue3/src/plugins/cookbook_ext/tests/*.test.mjs
import {test} from 'node:test'
import assert from 'node:assert/strict'
import {buildSchedule, formatDuration, formatSlot, roundedNow, scheduleToIcs} from '../services/schedule.ts'

process.env.TZ = 'Europe/Berlin'

// Brot mit Übernacht-Führung: Sauerteig 12 Std., Hauptteig 15 Min., Stockgare 2 Std., Ofen vorheizen 45 Min. (parallel), backen 50 Min.
const brot = [
    {name: 'Sauerteig ansetzen', time: 720},
    {name: 'Hauptteig kneten', time: 15},
    {name: 'Stockgare', time: 120},
    {name: 'Ofen vorheizen', time: 45, parallel: true},
    {name: 'Backen', time: 50},
]
const t = (s) => new Date(s)
const hhmm = (d) => formatSlot(d, true)

test('vorwärts: Start Sa 08:00, Datumswechsel und Wochentag', () => {
    const s = buildSchedule(brot, t('2026-11-07T08:00:00'), 'start')  // Samstag
    assert.deepEqual(s.items.map(i => hhmm(i.start)), ['Sa 08:00', 'Sa 20:00', 'Sa 20:15', 'Sa 22:15', 'Sa 22:15'])
    assert.equal(hhmm(s.end), 'Sa 23:05')
    assert.equal(s.totalMinutes, 905)  // vorheizen zählt nicht
    assert.equal(s.multiDay, false)
})

test('rückwärts: fertig So 12:00 → Start Sa 20:55', () => {
    const s = buildSchedule(brot, t('2026-11-08T12:00:00'), 'end')
    assert.equal(hhmm(s.start), 'Sa 20:55')
    assert.equal(hhmm(s.items[1].start), 'So 08:55')
    assert.equal(hhmm(s.end), 'So 12:00')
    assert.equal(s.multiDay, true)
})

test('paralleler Schritt, der länger dauert, verlängert das Ende', () => {
    const s = buildSchedule([{time: 10}, {time: 60, parallel: true}, {time: 20}], t('2026-11-07T10:00:00'))
    assert.equal(s.totalMinutes, 70)
    assert.equal(formatSlot(s.items[2].start, false), '10:10')
})

test('Schritte ohne Zeit bekommen dieselbe Uhrzeit wie der nächste', () => {
    const s = buildSchedule([{time: 0}, {time: 30}, {time: 0}], t('2026-11-07T10:00:00'))
    assert.deepEqual(s.items.map(i => formatSlot(i.start, false)), ['10:00', '10:00', '10:30'])
})

test('Dauer und gerundetes Jetzt', () => {
    assert.equal(formatDuration(905), '15 Std. 5 Min.')
    assert.equal(formatDuration(1680), '1 Tag 4 Std.')
    assert.equal(formatDuration(45), '45 Min.')
    assert.equal(formatSlot(roundedNow(t('2026-11-07T08:01:30')), false), '08:05')
})

test('ics: ein Termin je Schritt mit Erinnerung, UTC-Zeiten, Sonderzeichen maskiert', () => {
    const steps = [{name: 'Teig, kneten; gut', time: 15, instruction: 'Alles\nverkneten.'}, {time: 0, instruction: 'Servieren. Fertig.'}]
    const s = buildSchedule(steps, t('2026-11-07T08:00:00'))
    const ics = scheduleToIcs('Brot', steps, s, 'r1', t('2026-11-06T12:00:00Z'))
    assert.equal((ics.match(/BEGIN:VEVENT/g) || []).length, 2)
    assert.equal((ics.match(/BEGIN:VALARM/g) || []).length, 2)
    assert.match(ics, /DTSTART:20261107T070000Z/)
    assert.match(ics, /SUMMARY:Brot: 1\. Teig\\, kneten\; gut/)
    assert.match(ics, /SUMMARY:Brot: 2\. Servieren\./)
    assert.match(ics, /DESCRIPTION:Alles\\nverkneten\./)
    assert.ok(ics.split('\r\n').every(l => l.length <= 75))
})
