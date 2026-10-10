# Prompts für Claude Code – Rezept-App

Einen Prompt nach dem anderen nutzen. Erst weitermachen, wenn die Phase läuft und getestet ist.
`CLAUDE.md` liegt im Repo-Root und wird automatisch gelesen.

---

## Phase 1 – Infrastruktur (Original-Tandoor zum Testen)

```
Lies CLAUDE.md. Erstelle im Ordner deploy/ alles für den Betrieb von Tandoor 2.x (offizielles Image, aktuelle stabile Version prüfen) in einer Proxmox-LXC:
- docker-compose.yml mit Tandoor und PostgreSQL 16, benannten Volumes für DB, Medien und Static, sowie restart-Policies
- .env.example mit allen nötigen Variablen und Kommentaren (SECRET_KEY, DB, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS für den Tailscale-Hostnamen)
- projekt/SETUP_LXC.md: LXC anlegen (Debian, unprivilegiert, nesting=1, keyctl=1), Docker installieren, Tailscale in der LXC einrichten (inkl. /dev/net/tun), App erreichbar unter http://<tailscale-name>; optional tailscale serve für HTTPS
- deploy/backup.sh: pg_dump (custom format) + tar der Medien, Ziel per Variable (NAS-Mount), Rotation 7 täglich / 4 wöchentlich, Logging, Exit-Codes
- deploy/restore.sh und projekt/BACKUP.md mit Cron-Eintrag und einer Anleitung für den Restore-Test
Zeig mir zuerst den Plan, dann umsetzen. Am Ende Befehle zum Prüfen auflisten.
```

## Phase 2 – Fork & Dev-Umgebung

```
Wir arbeiten jetzt im Fork von TandoorRecipes/recipes. Analysiere die Repo-Struktur (Django-Apps, Vue-Frontend-Ordner, Build-Prozess, Models für Recipe, Step, Ingredient, Food, Unit, CookLog, Kommentare, Shopping) und schreib projekt/ARCHITEKTUR.md mit den für uns relevanten Stellen.
Richte eine lokale Dev-Umgebung ein (Backend + Vite-Dev-Server mit Hot Reload, PostgreSQL per Docker) und dokumentiere sie in projekt/DEV.md.
Lege die leere Django-App für unsere Erweiterungen an (Name laut CLAUDE.md) und registriere sie mit minimalem Eingriff. Notiere den Eingriff in projekt/CORE_CHANGES.md.
Prüfe außerdem: Decken CookLog und Kommentare unsere Anforderung "beliebig viele Bewertungen mit Kommentar und Fotos" ab? Antworte mit Empfehlung, noch nichts umbauen.
```

## Phase 3 – Theme & Grundoptik

```
Setze das Design aus CLAUDE.md als eigenes Vuetify-Theme um (Farben, Plus Jakarta Sans, Radien, Button- und Chip-Defaults). Mach es zum Standard-Theme, ohne Tandoors Kern-Komponenten umzuschreiben. Wo Overrides nötig sind, nutze möglichst zentrale Stellen.
Prüfe das Ergebnis auf Handybreite (390 px) und liste mir die Screens auf, die danach noch stark vom Zieldesign abweichen.
```

## Phase 4 – Hooks / "Unsere Version" (Backend)

```
Implementiere in unserer Erweiterungs-App das Varianten-Konzept aus CLAUDE.md:
- Models RecipeVariant, VariantIngredientChange, VariantStepNote. Gleiche sie vorher mit Tandoors Models ab und schlag ggf. Verbesserungen vor.
- Migrationen, Admin, DRF-Serializer und ViewSets, die zu Tandoors API-Stil und Berechtigungen (Space/User) passen
- Eine Service-Funktion, die aus Rezept + Variante die "effektive" Zutatenliste und Schritte berechnet, inklusive Skalierung auf n Portionen
- Die Einkaufsliste soll die effektive Variante übernehmen können
- Tests für Service und API
Erst den Plan zeigen, dann umsetzen.
```

## Phase 5 – Rezeptansicht neu

```
Baue die Rezeptansicht im Vue-Frontend nach dem Zieldesign aus CLAUDE.md neu, als eigene Komponente bzw. View:
großes Foto mit abgerundetem Sheet, Tags, Sterne und Anzahl Bewertungen, Segment "Original / Unsere Version", Portions-Stepper mit Live-Skalierung, Zutaten mit Badges "geändert"/"ergänzt", Button "Auf die Einkaufsliste", nummerierte Schritte mit "Unsere Notiz", Bewertungen und Kommentare mit "Bewertung oder Foto hinzufügen".
Dazu ein Editor, mit dem man Änderungen für "Unsere Version" bequem am Handy anlegt (Zutat antippen → ersetzen/Menge ändern/entfernen; Schritt antippen → Notiz).
Mobile first, Touch-Targets mindestens 44 px.
```

## Phase 6 – Übersicht, Kochmodus, Einkaufsliste, Import

```
Setze die Übersicht nach Zieldesign um (Suchfeld, Filter-Chips, 2-spaltiges Kartenraster, untere Navigation: Rezepte, Suche, Einkauf, Import).
Danach:
- Kochmodus: ein Schritt pro Bildschirm, große Schrift, Wake Lock, Zutaten des Schritts sichtbar, Timer aus Zeitangaben
- Einkaufsliste: Zutaten aus mehreren Rezepten zusammengefasst, nach Kategorie gruppiert, abhakbar
- Import: URL einfügen → Vorschau → speichern (nutzt Tandoors vorhandenen Import)
Für jeden Screen zuerst einen kurzen Plan zeigen.
```

## Phase 7 – Eigenes Image & Deployment

```
Erstelle aus unserem Fork ein eigenes Docker-Image (Multi-Stage-Build wie upstream) und passe deploy/docker-compose.yml an. Ergänze projekt/UPDATE.md: Upstream-Änderungen mergen, Konflikte lösen, Backup vor dem Update, Image bauen, ausrollen, Restore-Test.
```
