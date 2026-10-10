#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Baut das Docker-Image der Rezept-App aus diesem Fork (Multi-Stage):
#   Stage 1 (deploy/image/Dockerfile.frontend): Vue-Frontend mit Node 22 bauen
#   Stage 2 (Tandoors Dockerfile im Repo-Root, UNVERÄNDERT): Python/nginx-Image wie upstream,
#           ergänzt um eine Zeile, die das gebaute Frontend aus Stage 1 übernimmt.
# Das Dockerfile wird bei jedem Build neu zusammengesetzt – Änderungen von upstream am
# Dockerfile kommen so automatisch mit (siehe projekt/UPDATE.md).
#
# Aufruf (im Repo-Root oder aus deploy/):
#   deploy/build-image.sh                 # Tag: rezept-app:<datum>-<commit>, zusätzlich rezept-app:aktuell
#   deploy/build-image.sh --nur-dockerfile  # nur das zusammengesetzte Dockerfile ausgeben (Prüfung)
#
# Umgebungsvariablen:
#   IMAGE_NAME  (Standard: rezept-app)
#   PUSH=1      zusätzlich in eine Registry pushen (IMAGE_NAME muss dann z. B. ghcr.io/nfrankm/rezept-app sein)
#   PLATFORM    z. B. linux/amd64 (Standard: Plattform des bauenden Rechners)
#
# Exit-Codes: 0 ok | 1 Voraussetzung fehlt | 2 Dockerfile-Struktur unerwartet | 3 Build fehlgeschlagen
# ---------------------------------------------------------------------------
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
IMAGE_NAME="${IMAGE_NAME:-rezept-app}"
DOCKER="${DOCKER:-docker}"

[ -f Dockerfile ] || { echo "FEHLER: Dockerfile im Repo-Root fehlt"; exit 1; }
[ -f deploy/image/Dockerfile.frontend ] || { echo "FEHLER: deploy/image/Dockerfile.frontend fehlt"; exit 1; }

# Tandoors Dockerfile muss genau eine Zeile „COPY . ./" haben – dahinter wird das Frontend eingefügt
anchors=$(grep -c '^COPY \. \./[[:space:]]*$' Dockerfile || true)
if [ "$anchors" != "1" ]; then
    echo "FEHLER: Erwartete genau eine Zeile 'COPY . ./' in Tandoors Dockerfile, gefunden: $anchors."
    echo "Upstream hat das Dockerfile geändert → deploy/build-image.sh anpassen (siehe projekt/UPDATE.md)."
    exit 2
fi

compose_dockerfile() {
    cat deploy/image/Dockerfile.frontend
    echo "# ---------------------------------------------------------------------------"
    echo "# Stage 2 – Tandoors Dockerfile (unverändert aus dem Repo-Root)"
    echo "# ---------------------------------------------------------------------------"
    awk '{ print } /^COPY \. \.\/[[:space:]]*$/ {
        print "# Rezept-App: gebautes Frontend aus Stage 1 übernehmen"
        print "COPY --from=frontend /src/cookbook/static/vue3 ./cookbook/static/vue3"
    }' Dockerfile
}

if [ "${1:-}" = "--nur-dockerfile" ]; then
    compose_dockerfile
    exit 0
fi

command -v "$DOCKER" >/dev/null 2>&1 || { echo "FEHLER: docker nicht gefunden"; exit 1; }

COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo unbekannt)
TAG="$(date +%Y%m%d)-$COMMIT"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    TAG="$TAG-dirty"
    echo "WARNUNG: Es gibt nicht committete Änderungen – Tag endet auf -dirty."
fi

echo "Baue $IMAGE_NAME:$TAG …"
args=(build -f - -t "$IMAGE_NAME:$TAG" -t "$IMAGE_NAME:aktuell" --label "org.opencontainers.image.revision=$COMMIT"
      --label "org.opencontainers.image.source=https://github.com/NFrankM/recipes")
[ -n "${PLATFORM:-}" ] && args+=(--platform "$PLATFORM")
if ! compose_dockerfile | DOCKER_BUILDKIT=1 "$DOCKER" "${args[@]}" .; then
    echo "FEHLER: Build fehlgeschlagen"
    exit 3
fi

if [ "${PUSH:-0}" = "1" ]; then
    "$DOCKER" push "$IMAGE_NAME:$TAG"
    "$DOCKER" push "$IMAGE_NAME:aktuell"
fi

echo
echo "Fertig: $IMAGE_NAME:$TAG (auch als $IMAGE_NAME:aktuell)"
echo "In deploy/.env eintragen:  TANDOOR_IMAGE=$IMAGE_NAME:$TAG"
echo "Dann (nach Backup!):       cd deploy && docker compose up -d"
