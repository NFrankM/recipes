# Auftrag: Nachtlauf (selbstständig, ohne Rückfragen)

Ich schlafe und kann nicht antworten. Arbeite die Phasen aus `PROMPTS.md` **der Reihe nach selbstständig** ab, so weit du kommst. Ziel: Am Morgen soll möglichst viel fertig, getestet, committet und sauber dokumentiert sein.

## Sonderregeln für diesen Lauf (gehen CLAUDE.md vor)

1. **Nicht auf mein OK warten.** CLAUDE.md-Regel 3 („Plan zeigen und warten") gilt heute Nacht so: Schreib den Plan der Phase oben in `projekt/FORTSCHRITT.md` und setze ihn dann direkt um.
2. **Bei echten Unklarheiten** triffst du die vernünftigste Entscheidung, dokumentierst sie in `projekt/ENTSCHEIDUNGEN.md` (Frage, Optionen, Wahl, Grund) und machst weiter. Nur wenn etwas wirklich nicht ohne mich geht, notierst du es dort unter **„Offen für Frank"** und machst mit dem nächsten unabhängigen Teil weiter.
3. **Kleine Schritte, oft committen:** Nach jedem abgeschlossenen, lauffähigen Teilschritt committest du auf `main-custom` mit einer deutschen Commit-Message. Danach versuchst du `git push origin main-custom`. Wenn der Push scheitert (z. B. fehlende Anmeldung), ist das ok: Notier es einmal in FORTSCHRITT.md und committe nur lokal weiter.
4. **Nie:** auf `develop` committen, force-pushen, Git-History umschreiben, Secrets oder echte Passwörter committen, Dateien außerhalb dieses Repos ändern oder löschen, Systemeinstellungen ändern, globale Installationen mit sudo durchführen. Python-Pakete nur in einer venv im Repo (`venv/`, steht bereits in `.gitignore`), Node-Pakete nur lokal in `vue3/`.
5. **Tests:** Für alles Eigene (Models, Services, API) schreibst du Tests und führst sie aus. Committe nichts, was bekanntermaßen kaputt ist. Wenn etwas nach drei ernsthaften Versuchen nicht läuft, dokumentierst du Fehler und Stand in FORTSCHRITT.md, committest den sauberen Teil und gehst weiter.
6. **Kern so wenig wie möglich anfassen** (siehe CLAUDE.md). Jede Kernänderung kommt in `projekt/CORE_CHANGES.md`.
7. **Umgebung prüfen statt annehmen:** Prüfe zu Beginn, was auf diesem Mac vorhanden ist (`python3 --version`, `node --version`, `docker --version`, `psql`). Fehlt Docker, baust du Phase 1 trotzdem vollständig (Dateien und Doku) und validierst so weit wie möglich, z. B. mit `bash -n` für Skripte und YAML-Syntax-Checks. Für die Dev-Umgebung nimmst du dann SQLite oder einen lokalen Weg ohne Docker und dokumentierst das.
8. **Der Klon ist flach (`--depth 1`).** Für die Arbeit reicht das. Kein `--unshallow` nötig.

## Reihenfolge und Abnahmekriterien

**Phase 1 – Infrastruktur** (Prompt 1 in PROMPTS.md)
- Fertig, wenn: `deploy/docker-compose.yml`, `deploy/.env.example`, `deploy/backup.sh`, `deploy/restore.sh`, `projekt/SETUP_LXC.md` und `projekt/BACKUP.md` existieren und die Skripte `bash -n` bestehen. Wenn Docker verfügbar ist: `docker compose config` läuft fehlerfrei.
- Verwende die aktuelle stabile Tandoor-Image-Version, die in `version.py` bzw. in den Repo-Dateien steht.

**Phase 2 – Architektur & Dev-Umgebung** (Prompt 2)
- Fertig, wenn: `projekt/ARCHITEKTUR.md` beschreibt die relevanten Models (Recipe, Step, Ingredient, Food, Unit, CookLog, Comment, Shopping*, Keyword), API-Struktur, Berechtigungen (Space/User) und den Aufbau von `vue3/` (Routing, Theme, Komponenten). `projekt/DEV.md` enthält funktionierende Start-Befehle. Die eigene Django-App `cookbook_ext` ist angelegt, registriert und `python manage.py check` läuft fehlerfrei.
- Entscheide anhand des Codes, ob CookLog und Kommentare unsere Bewertungen abdecken, und dokumentiere die Entscheidung in ENTSCHEIDUNGEN.md.

**Phase 3 – Theme & Grundoptik** (Prompt 3)
- Fertig, wenn: Ein eigenes Vuetify-Theme mit den Design-Tokens aus CLAUDE.md ist Standard, Plus Jakarta Sans ist eingebunden und `npm run build` (bzw. der Build-Befehl aus `vue3/package.json`) läuft durch. Liste in FORTSCHRITT.md auf, welche Screens noch abweichen.

**Phase 4 – „Unsere Version" Backend** (Prompt 4)
- Fertig, wenn: Models, Migrationen, Admin, Serializer, ViewSets und die Service-Funktion für die effektive Zutatenliste inklusive Skalierung existieren. Tests decken ab: Ersetzen, Ergänzen, Entfernen, Mengenänderung, Skalierung, Schrittnotizen und Berechtigungen. Alle Tests sind grün.

**Phase 5 – Rezeptansicht neu** (Prompt 5)
- Fertig, wenn: Die neue Rezeptansicht mit Segment „Original / Unsere Version", Portions-Stepper, Badges „geändert"/„ergänzt" und Schrittnotizen im Frontend funktioniert, an die API aus Phase 4 angebunden ist und der Build durchläuft.

**Phase 6 und 7** nur, wenn alles davor fertig ist.

## Protokoll (wichtig für morgen früh)

Führe `projekt/FORTSCHRITT.md` laufend, mit diesen Abschnitten:
- **Stand jetzt:** 3–5 Sätze, was fertig ist und was nicht
- **Pro Phase:** Plan, erledigt, getestet mit (Befehle + Ergebnis), Commits
- **Probleme:** was nicht ging und warum
- **Für Frank zu tun:** konkrete Schritte, z. B. „auf Proxmox LXC anlegen, siehe SETUP_LXC.md"

Zum Schluss (oder wenn du an eine Grenze kommst): FORTSCHRITT.md aktualisieren, committen, Push versuchen.

Fang jetzt an mit der Umgebungsprüfung, dann Phase 1.
