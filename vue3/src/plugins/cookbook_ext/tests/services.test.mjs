// Tests für reine Hilfsfunktionen des Frontend-Plugins.
// Ausführen (ohne zusätzliche Abhängigkeiten, Node ≥ 22.6):
//   node --experimental-strip-types --test vue3/src/plugins/cookbook_ext/tests/*.test.mjs
import {test} from 'node:test'
import assert from 'node:assert/strict'
import {formatAmount, formatMinutes, ingredientText} from '../services/format.ts'
import {findTimers, formatClock} from '../services/timers.ts'

const g = {id: 1, name: 'g'}
const el = {id: 2, name: 'EL'}

test('Mengen: Brüche bei Stück/EL, Dezimal bei g/ml', () => {
    assert.equal(formatAmount(1.5, el), '1½')
    assert.equal(formatAmount(0.5, null), '½')
    assert.equal(formatAmount(0.25, el), '¼')
    assert.equal(formatAmount(2 / 3, el), '⅔')
    assert.equal(formatAmount(3, el), '3')
    assert.equal(formatAmount(12.5, g), '12,5')
    assert.equal(formatAmount(1.5, g), '1,5')
    assert.equal(formatAmount(250, g), '250')
    assert.equal(formatAmount(1234, g), '1.234')
    assert.equal(formatAmount(0, g), '')
    assert.equal(formatAmount(12.3, el), '12,3')  // ab 10 keine Brüche
})

test('Zutatentext mit Plural', () => {
    assert.equal(ingredientText({food: {id: 1, name: 'Ei', plural_name: 'Eier'}, unit: null, amount: 2}), '2 Eier')
    assert.equal(ingredientText({food: {id: 1, name: 'Mehl'}, unit: g, amount: 200}), '200 g Mehl')
    assert.equal(ingredientText({food: {id: 1, name: 'Salz'}, unit: null, amount: 0, no_amount: true}), 'Salz')
})

test('Minuten', () => {
    assert.equal(formatMinutes(35), '35 Min.')
    assert.equal(formatMinutes(60), '1 Std.')
    assert.equal(formatMinutes(95), '1 Std. 35 Min.')
    assert.equal(formatMinutes(0), '')
})

test('Timer aus Text', () => {
    assert.deepEqual(findTimers('10 Minuten köcheln lassen.'), [{label: '10 Minuten', seconds: 600}])
    assert.deepEqual(findTimers('zugedeckt 6–8 Minuten stocken').map(t => t.seconds), [360])
    assert.deepEqual(findTimers('1 Stunde ruhen, dann 30 Sek. rühren').map(t => t.seconds), [3600, 30])
    assert.deepEqual(findTimers('ca. 1,5 Std. backen').map(t => t.seconds), [5400])
    assert.deepEqual(findTimers('5 Min. braten, nochmal 5 Min.').length, 1)  // doppelte zusammengefasst
    assert.deepEqual(findTimers('2 Minzblätter'), [])  // „Min" mitten im Wort zählt nicht
    assert.deepEqual(findTimers(''), [])
})

test('Uhr', () => {
    assert.equal(formatClock(299.4), '4:59')
    assert.equal(formatClock(3725), '1:02:05')
    assert.equal(formatClock(-3), '0:00')
})
