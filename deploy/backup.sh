#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Rezept-App – nächtliches Backup
#
# Sichert
#   1. die PostgreSQL-Datenbank (pg_dump, custom format)  -> db.dump
#   2. die Medien (Bilder)  als tar.gz                    -> media.tar.gz
# in ein Zielverzeichnis (NAS-Mount) und rotiert:
#   daily/   die letzten KEEP_DAILY  Sicherungen (Standard 7)
#   weekly/  die letzten KEEP_WEEKLY Sicherungen (Standard 4), angelegt am WEEKLY_DAY
#
# Konfiguration über Umgebungsvariablen oder deploy/backup.conf (gleiche Namen):
#   BACKUP_DIR      Ziel, z. B. /mnt/nas/rezept-backup             (Pflicht)
#   REQUIRE_MOUNT   1 = BACKUP_DIR (oder ein Elternordner) muss ein Mountpoint sein,
#                   damit nicht versehentlich auf die lokale Platte gesichert wird (Standard 1)
#   COMPOSE_DIR     Ordner mit docker-compose.yml und .env           (Standard: Ordner dieses Skripts)
#   KEEP_DAILY      Anzahl täglicher Sicherungen                     (Standard 7)
#   KEEP_WEEKLY     Anzahl wöchentlicher Sicherungen                 (Standard 4)
#   WEEKLY_DAY      Wochentag für die Wochensicherung, 1=Mo … 7=So    (Standard 7)
#   BACKUP_ENV      1 = .env (enthält Passwörter!) mitsichern        (Standard 0)
#   LOG_FILE        Logdatei                                          (Standard: $BACKUP_DIR/backup.log)
#
# Exit-Codes:
#   0 ok | 1 Konfigurationsfehler | 2 Ziel nicht verfügbar | 3 DB-Dump fehlgeschlagen
#   4 Medien-Sicherung fehlgeschlagen | 5 Prüfung fehlgeschlagen | 6 Rotation fehlgeschlagen
#   7 läuft bereits
# ---------------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/backup.conf" ] && . "$SCRIPT_DIR/backup.conf"

BACKUP_DIR="${BACKUP_DIR:-}"
REQUIRE_MOUNT="${REQUIRE_MOUNT:-1}"
COMPOSE_DIR="${COMPOSE_DIR:-$SCRIPT_DIR}"
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
WEEKLY_DAY="${WEEKLY_DAY:-7}"
BACKUP_ENV="${BACKUP_ENV:-0}"
DOCKER="${DOCKER:-docker}"
# Nur für Tests: Zeitstempel überschreiben (Format YYYY-MM-DD_HHMMSS und Wochentag 1-7)
NOW="${BACKUP_NOW:-$(date +%Y-%m-%d_%H%M%S)}"
WEEKDAY="${BACKUP_WEEKDAY:-$(date +%u)}"

LOG_FILE="${LOG_FILE:-${BACKUP_DIR:+$BACKUP_DIR/backup.log}}"

log() {
    local line
    line="$(date '+%Y-%m-%d %H:%M:%S') [$1] $2"
    echo "$line"
    if [ -n "${LOG_FILE:-}" ] && [ -d "$(dirname "$LOG_FILE")" ]; then
        echo "$line" >>"$LOG_FILE" 2>/dev/null || true
    fi
}

fail() { # fail <exit-code> <meldung>
    log FEHLER "$2"
    [ -n "${WORK_DIR:-}" ] && [ -d "$WORK_DIR" ] && rm -rf "$WORK_DIR"
    exit "$1"
}

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi
}

is_number() { case "$1" in '' | *[!0-9]*) return 1 ;; *) return 0 ;; esac; }

compose() {
    "$DOCKER" compose --project-directory "$COMPOSE_DIR" -f "$COMPOSE_DIR/docker-compose.yml" "$@"
}

# --- Konfiguration prüfen ----------------------------------------------------
[ -n "$BACKUP_DIR" ] || fail 1 "BACKUP_DIR ist nicht gesetzt (z. B. BACKUP_DIR=/mnt/nas/rezept-backup)"
[ -f "$COMPOSE_DIR/docker-compose.yml" ] || fail 1 "docker-compose.yml nicht gefunden in $COMPOSE_DIR"
for v in KEEP_DAILY KEEP_WEEKLY WEEKLY_DAY; do
    is_number "${!v}" || fail 1 "$v muss eine Zahl sein (ist: '${!v}')"
done
[ "$KEEP_DAILY" -ge 1 ] || fail 1 "KEEP_DAILY muss mindestens 1 sein"
command -v "$DOCKER" >/dev/null 2>&1 || fail 1 "docker nicht gefunden"

# --- Ziel prüfen ---------------------------------------------------------------
if [ "$REQUIRE_MOUNT" = "1" ] && command -v mountpoint >/dev/null 2>&1; then
    p="$BACKUP_DIR"
    mounted=0
    while [ -n "$p" ] && [ "$p" != "/" ]; do
        if [ -d "$p" ] && mountpoint -q "$p"; then mounted=1; break; fi
        p="$(dirname "$p")"
    done
    [ "$mounted" = "1" ] || fail 2 "$BACKUP_DIR liegt auf keinem Mount (NAS nicht eingehängt?). Abbruch, um die lokale Platte nicht zu füllen. (REQUIRE_MOUNT=0 schaltet die Prüfung ab)"
fi
mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly" 2>/dev/null || fail 2 "Kann $BACKUP_DIR nicht anlegen"
[ -w "$BACKUP_DIR" ] || fail 2 "$BACKUP_DIR ist nicht beschreibbar"

# --- Sperre gegen parallele Läufe ---------------------------------------------
if command -v flock >/dev/null 2>&1; then
    exec 9>"$BACKUP_DIR/.backup.lock"
    flock -n 9 || fail 7 "Es läuft bereits ein Backup"
fi

log INFO "Backup startet → $BACKUP_DIR (Projekt: $COMPOSE_DIR)"

WORK_DIR="$BACKUP_DIR/daily/.${NOW}.unvollstaendig"
TARGET="$BACKUP_DIR/daily/$NOW"
[ -e "$TARGET" ] && fail 1 "Ziel $TARGET existiert bereits"
mkdir -p "$WORK_DIR" || fail 2 "Kann $WORK_DIR nicht anlegen"

# --- 1. Datenbank -------------------------------------------------------------------
log INFO "Datenbank-Dump (pg_dump -Fc) …"
if ! compose exec -T db_recipes sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' >"$WORK_DIR/db.dump"; then
    fail 3 "pg_dump fehlgeschlagen (läuft der Container db_recipes?)"
fi
[ -s "$WORK_DIR/db.dump" ] || fail 3 "Datenbank-Dump ist leer"
log INFO "Datenbank-Dump ok ($(du -h "$WORK_DIR/db.dump" | cut -f1))"

# --- 2. Medien ---------------------------------------------------------------------
# "run" statt "exec": funktioniert auch, wenn der Web-Container gerade nicht läuft.
log INFO "Medien sichern (tar.gz) …"
if ! compose run --rm --no-deps -T --entrypoint tar web_recipes -czf - -C /opt/recipes/mediafiles . >"$WORK_DIR/media.tar.gz"; then
    fail 4 "Sichern der Medien fehlgeschlagen"
fi
log INFO "Medien ok ($(du -h "$WORK_DIR/media.tar.gz" | cut -f1))"

# --- optional: .env -----------------------------------------------------------------
if [ "$BACKUP_ENV" = "1" ] && [ -f "$COMPOSE_DIR/.env" ]; then
    (umask 077 && cp "$COMPOSE_DIR/.env" "$WORK_DIR/env.backup") || fail 4 ".env konnte nicht kopiert werden"
    log INFO ".env mitgesichert (enthält Passwörter!)"
fi

# --- 3. Prüfen ---------------------------------------------------------------------
log INFO "Prüfe Sicherung …"
compose exec -T db_recipes pg_restore --list <"$WORK_DIR/db.dump" >/dev/null ||
    fail 5 "pg_restore --list kann den Dump nicht lesen"
tar -tzf "$WORK_DIR/media.tar.gz" >/dev/null || fail 5 "media.tar.gz ist beschädigt"

{
    echo "zeitpunkt=$NOW"
    echo "image=$(compose config --images 2>/dev/null | tr '\n' ' ')"
    echo "host=$(hostname)"
} >"$WORK_DIR/info.txt"
(cd "$WORK_DIR" && sha256 db.dump media.tar.gz >SHA256SUMS) || fail 5 "Prüfsummen konnten nicht erstellt werden"

mv "$WORK_DIR" "$TARGET" || fail 5 "Konnte $WORK_DIR nicht nach $TARGET verschieben"
WORK_DIR=""
log INFO "Tägliche Sicherung fertig: $TARGET"

# --- 4. Wochensicherung ------------------------------------------------------------
if [ "$WEEKDAY" = "$WEEKLY_DAY" ] && [ "$KEEP_WEEKLY" -gt 0 ]; then
    cp -R "$TARGET" "$BACKUP_DIR/weekly/$NOW" || fail 6 "Wochensicherung konnte nicht kopiert werden"
    log INFO "Wochensicherung angelegt: $BACKUP_DIR/weekly/$NOW"
fi

# --- 5. Rotation ------------------------------------------------------------------
rotate() { # rotate <ordner> <behalten>
    local dir="$1" keep="$2" count=0 d
    # neueste zuerst (Namen sind sortierbare Zeitstempel); versteckte/unvollständige Ordner ignorieren
    for d in $(ls -1 "$dir" | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}$' | sort -r); do
        count=$((count + 1))
        if [ "$count" -gt "$keep" ]; then
            rm -rf "${dir:?}/$d" || return 1
            log INFO "Rotation: $dir/$d gelöscht"
        fi
    done
}
rotate "$BACKUP_DIR/daily" "$KEEP_DAILY" || fail 6 "Rotation daily fehlgeschlagen"
rotate "$BACKUP_DIR/weekly" "$KEEP_WEEKLY" || fail 6 "Rotation weekly fehlgeschlagen"

# Reste abgebrochener Läufe (älter als 1 Tag) entfernen
find "$BACKUP_DIR/daily" -maxdepth 1 -name '.*.unvollstaendig' -mtime +0 -exec rm -rf {} + 2>/dev/null || true

log INFO "Backup erfolgreich beendet"
exit 0
