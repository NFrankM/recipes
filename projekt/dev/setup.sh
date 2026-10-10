#!/usr/bin/env bash
# Richtet die lokale Dev-Umgebung ohne Admin-Rechte und ohne globale Installationen ein:
#   - uv (Python-Paketmanager) + CPython 3.12  -> .tools/
#   - Node 22                                   -> .tools/node
#   - venv/ mit allen Python-Abhängigkeiten (ohne LDAP/SAML)
#   - vue3/node_modules (yarn, wie upstream)
#   - .env für die Entwicklung (DEBUG=1, SQLite), falls noch nicht vorhanden
#   - Datenbank migrieren
# Alles liegt im Repo und lässt sich mit  rm -rf .tools venv vue3/node_modules  entfernen.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"
UV_VERSION=0.8.22
NODE_MAJOR=22

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  UV_TRIPLE=aarch64-apple-darwin;     NODE_PLATFORM=darwin-arm64 ;;
  Darwin-x86_64) UV_TRIPLE=x86_64-apple-darwin;      NODE_PLATFORM=darwin-x64 ;;
  Linux-x86_64)  UV_TRIPLE=x86_64-unknown-linux-gnu; NODE_PLATFORM=linux-x64 ;;
  Linux-aarch64) UV_TRIPLE=aarch64-unknown-linux-gnu; NODE_PLATFORM=linux-arm64 ;;
  *) echo "Plattform nicht unterstützt"; exit 1 ;;
esac

mkdir -p .tools
if [ ! -x .tools/uv/uv ]; then
  echo "== uv $UV_VERSION"
  curl -fsSL "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-$UV_TRIPLE.tar.gz" | tar xz -C .tools
  mv ".tools/uv-$UV_TRIPLE" .tools/uv
fi
if [ ! -x .tools/node/bin/node ]; then
  NODE_VERSION=$(curl -fsSL https://nodejs.org/dist/index.json | python3 -c "import json,sys;print([v['version'] for v in json.load(sys.stdin) if v['version'].startswith('v$NODE_MAJOR.')][0])")
  echo "== Node $NODE_VERSION"
  curl -fsSL "https://nodejs.org/dist/$NODE_VERSION/node-$NODE_VERSION-$NODE_PLATFORM.tar.gz" | tar xz -C .tools
  mv ".tools/node-$NODE_VERSION-$NODE_PLATFORM" .tools/node
fi

# shellcheck disable=SC1091
. projekt/dev/env.sh

if [ ! -x venv/bin/python ]; then
  echo "== venv (Python 3.12)"
  uv venv venv --python 3.12
fi
echo "== Python-Abhängigkeiten"
grep -vE '^(python-ldap|django-auth-ldap|python3-saml)' requirements.txt > .tools/requirements-dev.txt
uv pip install --python venv/bin/python -r .tools/requirements-dev.txt

echo "== Frontend-Abhängigkeiten"
(cd vue3 && corepack yarn@1.22.22 install --frozen-lockfile)

if [ ! -f .env ]; then
  echo "== .env für Entwicklung anlegen"
  cat > .env <<ENV
# Lokale Entwicklung (nicht committen) – siehe projekt/DEV.md
DEBUG=1
SECRET_KEY=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
ALLOWED_HOSTS=*
TZ=Europe/Berlin
ENV
fi

echo "== Migrationen"
venv/bin/python manage.py migrate
echo "Fertig. Weiter mit: source projekt/dev/env.sh  (siehe projekt/DEV.md)"
