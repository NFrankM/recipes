#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Rezept-App – Wiederherstellung aus einer Sicherung von backup.sh
#
# Aufruf:
#   ./restore.sh [Optionen] <sicherungsordner>
#   z. B. ./restore.sh /mnt/nas/rezept-backup/daily/2026-10-10_030001
#
# Optionen:
#   --nur-db        nur die Datenbank wiederherstellen
#   --nur-medien    nur die Medien wiederherstellen
#   --projekt NAME  in ein ANDERES Compose-Projekt wiederherstellen (eigene Volumes),
#                   z. B. für den Restore-Test: --projekt rezept-test
#                   (zusammen mit HTTP_PORT=8081, damit es neben dem Live-System läuft)
#   --ja            ohne Rückfrage (für Automatisierung)
#
# ACHTUNG: Die Ziel-Datenbank und der Medienordner werden vollständig ERSETZT.
#
# Exit-Codes:
#   0 ok | 1 Aufruf-/Konfigurationsfehler | 2 Sicherung unvollständig/beschädigt
#   3 DB-Restore fehlgeschlagen | 4 Medien-Restore fehlgeschlagen | 5 abgebrochen
# ---------------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="${COMPOSE_DIR:-$SCRIPT_DIR}"
DOCKER="${DOCKER:-docker}"

DO_DB=1
DO_MEDIA=1
PROJECT=""
YES=0
SRC=""

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [$1] $2"; }
fail() { log FEHLER "$2"; exit "$1"; }
usage() { sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
    --nur-db) DO_MEDIA=0 ;;
    --nur-medien) DO_DB=0 ;;
    --projekt) shift; PROJECT="${1:-}"; [ -n "$PROJECT" ] || usage ;;
    --ja) YES=1 ;;
    -h | --help) usage ;;
    -*) echo "Unbekannte Option: $1"; usage ;;
    *) SRC="$1" ;;
    esac
    shift
done

[ -n "$SRC" ] || usage
[ -d "$SRC" ] || fail 1 "Sicherungsordner $SRC nicht gefunden"
[ -f "$COMPOSE_DIR/docker-compose.yml" ] || fail 1 "docker-compose.yml nicht gefunden in $COMPOSE_DIR"
command -v "$DOCKER" >/dev/null 2>&1 || fail 1 "docker nicht gefunden"

compose() {
    if [ -n "$PROJECT" ]; then
        "$DOCKER" compose --project-directory "$COMPOSE_DIR" -f "$COMPOSE_DIR/docker-compose.yml" -p "$PROJECT" "$@"
    else
        "$DOCKER" compose --project-directory "$COMPOSE_DIR" -f "$COMPOSE_DIR/docker-compose.yml" "$@"
    fi
}

sha256_check() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum -c --quiet SHA256SUMS; else shasum -a 256 -c --quiet SHA256SUMS; fi
}

# --- Sicherung prüfen ---------------------------------------------------------------
[ "$DO_DB" = 0 ] || [ -s "$SRC/db.dump" ] || fail 2 "$SRC/db.dump fehlt oder ist leer"
[ "$DO_MEDIA" = 0 ] || [ -f "$SRC/media.tar.gz" ] || fail 2 "$SRC/media.tar.gz fehlt"
if [ -f "$SRC/SHA256SUMS" ]; then
    (cd "$SRC" && sha256_check) || fail 2 "Prüfsummen stimmen nicht – Sicherung beschädigt"
    log INFO "Prüfsummen ok"
else
    log WARNUNG "Keine SHA256SUMS vorhanden, Prüfung übersprungen"
fi
[ -f "$SRC/info.txt" ] && log INFO "Sicherung: $(tr '\n' ' ' <"$SRC/info.txt")"

# --- Rückfrage ----------------------------------------------------------------------
ziel="${PROJECT:-Standard-Projekt (LIVE!)}"
was=""
[ "$DO_DB" = 1 ] && was="Datenbank"
[ "$DO_MEDIA" = 1 ] && was="${was:+$was + }Medien"
if [ "$YES" != 1 ]; then
    echo
    echo "Wiederherstellen: $was"
    echo "Aus:              $SRC"
    echo "Nach:             $ziel"
    echo "Die vorhandenen Daten dort werden GELÖSCHT."
    printf 'Zum Fortfahren JA eingeben: '
    read -r answer
    [ "$answer" = "JA" ] || fail 5 "Abgebrochen"
fi

# --- Web-Container stoppen, DB starten ------------------------------------------------
log INFO "Stoppe web_recipes …"
compose stop web_recipes >/dev/null 2>&1 || true

if [ "$DO_DB" = 1 ]; then
    log INFO "Starte db_recipes und warte, bis sie bereit ist …"
    compose up -d --wait db_recipes || fail 3 "db_recipes startet nicht"

    log INFO "Lege Datenbank neu an …"
    compose exec -T db_recipes sh -c '
        dropdb --if-exists --force -U "$POSTGRES_USER" "$POSTGRES_DB" &&
        createdb -U "$POSTGRES_USER" -O "$POSTGRES_USER" "$POSTGRES_DB"' ||
        fail 3 "Datenbank konnte nicht neu angelegt werden"

    log INFO "pg_restore …"
    compose exec -T db_recipes sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --role="$POSTGRES_USER" --exit-on-error' \
        <"$SRC/db.dump" || fail 3 "pg_restore fehlgeschlagen"
    log INFO "Datenbank wiederhergestellt"
fi

if [ "$DO_MEDIA" = 1 ]; then
    log INFO "Stelle Medien wieder her …"
    compose run --rm --no-deps -T --entrypoint sh web_recipes -c '
        find /opt/recipes/mediafiles -mindepth 1 -delete &&
        tar -xzf - -C /opt/recipes/mediafiles' <"$SRC/media.tar.gz" ||
        fail 4 "Medien konnten nicht wiederhergestellt werden"
    log INFO "Medien wiederhergestellt"
fi

log INFO "Starte alle Dienste …"
compose up -d || fail 3 "Dienste konnten nicht gestartet werden"
log INFO "Fertig. Tandoor führt beim Start ggf. Migrationen aus (docker compose logs -f web_recipes)."
exit 0
