# Update-Ablauf

Wie neue Tandoor-Versionen (upstream) in unseren Fork kommen und wie ein neues Image ausgerollt wird.

> **Grundregel:** Tandoor-Migrationen lassen sich **nicht** zurückrollen. Ein „Zurück" gibt es nur über **Backup + vorheriges Image**. Deshalb: vor jedem Update Backup **und** Restore-Test.

Übersicht:

1. Upstream in den Fork holen (`develop` → `main-custom`), Konflikte lösen
2. Lokal testen (Tests, Build, kurz im Browser)
3. Auf der LXC: Backup + Restore-Test
4. Image bauen
5. Ausrollen und prüfen
6. Bei Problemen: zurück auf altes Image + Restore

---

## 1. Upstream mergen (auf dem Mac)

```bash
cd ~/Documents/rezept-app
git fetch upstream
git checkout develop
git merge --ff-only upstream/develop      # develop bleibt unverändertes Upstream
git push origin develop

git checkout main-custom
git merge develop                           # Upstream in unseren Arbeitsbranch
```

Alternativ für **stabile Releases** statt `develop`: `git merge <tag>` (z. B. `2.7.0`) – die Tags gibt es mit `git fetch upstream --tags`.

### Wo Konflikte entstehen können

Unsere Änderungen am Tandoor-Kern stehen vollständig in [CORE_CHANGES.md](CORE_CHANGES.md). Erwartbar sind nur:

| Datei | Was tun bei Konflikt |
|---|---|
| `.gitignore` | Upstream-Version übernehmen und unsere Zeilen wieder einfügen: `/recipes/plugins/*`, `!/recipes/plugins/cookbook_ext/`, `vue3/src/plugins/*`, `!vue3/src/plugins/cookbook_ext/`, `.tools/` |
| `vue3/src/apps/tandoor/Tandoor.vue` | Upstream-Version übernehmen, dann die drei mit „Rezept-App" markierten Zeilen wieder einsetzen (Import `TANDOOR_PLUGINS`, `pluginLayoutComponents`, `<component v-for …>` hinter `</v-bottom-navigation>`) |
| `vue3/src/types/Plugins.ts` | Zeile `layoutComponents?: Component[]` im Typ `TandoorPlugin` wieder einsetzen |

Alles andere (unsere App in `recipes/plugins/cookbook_ext/`, Frontend in `vue3/src/plugins/cookbook_ext/`, `deploy/`, `projekt/`) fasst Upstream nicht an.

Nach dem Lösen: `git add …` und `git commit`.

### Was nach einem Merge zu prüfen ist

Wir hängen an ein paar Tandoor-Interna. Wenn upstream diese ändert, merkt man es an:

| Abhängigkeit | Prüfen |
|---|---|
| Plugin-Lader (`recipes/settings.py`, `cookbook/urls.py`) | `pytest recipes/plugins/cookbook_ext` → `test_plugin.py` muss grün sein; `python manage.py check` zeigt `PLUGIN cookbook_ext loaded` |
| Frontend-Plugins (`vue3/src/types/Plugins.ts`, `main.ts` hängt Plugin-Routen an) | Rezept öffnen → neue Ansicht mit großem Foto? Startseite → „Rezepte"-Übersicht? |
| Routen-Namen `RecipeViewPage`, `StartPage` (E6) | wie oben; wenn Tandoor sie umbenennt, zeigt die App wieder Tandoors Seiten (nichts geht kaputt) |
| Models `Recipe`, `Step`, `Ingredient`, `CookLog`, `ShoppingListEntry` | unsere Tests (`pytest recipes/plugins/cookbook_ext`) |
| Neue Tandoor-Migrationen | `python manage.py makemigrations --check` darf für `cookbook_ext` nichts erzeugen; unsere Migration hängt nur an einer älteren Tandoor-Migration |
| `Dockerfile` von upstream | `deploy/build-image.sh --nur-dockerfile` muss ohne Fehler durchlaufen (erwartet genau eine Zeile `COPY . ./`) |

## 2. Lokal testen

```bash
source projekt/dev/env.sh
projekt/dev/setup.sh            # installiert geänderte Python-/Frontend-Abhängigkeiten nach und migriert
pytest recipes/plugins/cookbook_ext -o addopts="" -q
node --experimental-strip-types --test vue3/src/plugins/cookbook_ext/tests/*.test.mjs
(cd vue3 && yarn build)
python manage.py runserver      # kurz durchklicken: Übersicht, Rezept, „Unsere Version", Einkauf, Kochmodus
```

Optional die komplette Tandoor-Suite: `pytest cookbook/tests -o addopts="" -q -n auto`.

Dann pushen: `git push origin main-custom`.

## 3. Backup und Restore-Test (auf der LXC)

```bash
lxc# cd /opt/rezept-app/deploy
lxc# ./backup.sh
```

Danach den Restore-Test aus [BACKUP.md](BACKUP.md#5-restore-test-vor-jedem-update-und-z-b-einmal-im-monat) durchführen. Erst wenn der grün ist, weiter.

Den aktuell laufenden Image-Tag notieren (für den Rückweg):

```bash
lxc# grep TANDOOR_IMAGE .env
lxc# docker compose images web_recipes
```

## 4. Image bauen (auf der LXC)

```bash
lxc# cd /opt/rezept-app
lxc# git fetch origin && git checkout main-custom && git pull --ff-only
lxc# deploy/build-image.sh
#   … Fertig: rezept-app:20261011-27b8a4d (auch als rezept-app:aktuell)
```

Das Skript setzt das Dockerfile aus zwei Teilen zusammen: unserer Frontend-Stage (`deploy/image/Dockerfile.frontend`, Node 22 + yarn) und **Tandoors unverändertem Dockerfile**, in das nach `COPY . ./` eine Zeile eingefügt wird, die das gebaute Frontend übernimmt. Änderungen von upstream am Dockerfile kommen damit automatisch mit. Kontrolle des zusammengesetzten Dockerfiles: `deploy/build-image.sh --nur-dockerfile`.

Der Build braucht ca. 2–3 GB freien Platz und auf einer kleinen LXC 5–15 Minuten. Alte Images aufräumen: `docker image ls rezept-app` und `docker image rm rezept-app:<alter-tag>` (den vorherigen Tag als Rückweg behalten!).

**Alternative:** Image auf einem anderen Rechner bauen und in eine Registry schieben, z. B. GitHub Container Registry: `IMAGE_NAME=ghcr.io/nfrankm/rezept-app PUSH=1 deploy/build-image.sh` (vorher `docker login ghcr.io`). Achtung Architektur: Proxmox ist meist `linux/amd64` – auf einem Mac mit Apple-Chip dann `PLATFORM=linux/amd64` setzen.

## 5. Ausrollen

```bash
lxc# cd /opt/rezept-app/deploy
lxc# sed -i 's/^TANDOOR_IMAGE=.*/TANDOOR_IMAGE=rezept-app:20261011-27b8a4d/' .env    # neuen Tag eintragen
lxc# docker compose up -d
lxc# docker compose logs -f web_recipes       # Migrationen laufen, warten auf „Starting gunicorn"
```

Prüfen:
- [ ] `docker compose ps` – beide Container laufen
- [ ] Übersicht lädt, Rezept mit „Unsere Version" öffnen, Portionen ändern
- [ ] Einkaufsliste öffnen
- [ ] Ein Foto wird angezeigt

## 6. Wenn etwas schiefgeht

Weil Migrationen gelaufen sein können, reicht es **nicht**, nur den alten Image-Tag einzutragen. Rückweg:

```bash
lxc# cd /opt/rezept-app/deploy
lxc# sed -i 's/^TANDOOR_IMAGE=.*/TANDOOR_IMAGE=rezept-app:<vorheriger-tag>/' .env
lxc# ./restore.sh /mnt/nas/rezept-backup/daily/<sicherung-von-schritt-3>
```

`restore.sh` stoppt Tandoor, spielt Datenbank und Bilder der Sicherung ein und startet mit dem alten Image. Alles, was zwischen Backup und Rückweg eingegeben wurde, ist dann weg – deshalb das Update zu einer ruhigen Zeit machen.

Als letzte Rückfallebene gibt es das Proxmox-Backup der ganzen LXC.
