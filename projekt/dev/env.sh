# Dev-Umgebung aktivieren:  source projekt/dev/env.sh
# Setzt PATH auf die repo-lokalen Toolchains in .tools/ und aktiviert venv/.
_REPO="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
export PATH="$_REPO/.tools/node/bin:$_REPO/.tools/uv:$PATH"
export UV_CACHE_DIR="$_REPO/.tools/uv-cache"
export UV_PYTHON_INSTALL_DIR="$_REPO/.tools/python"
export COREPACK_HOME="$_REPO/.tools/corepack"
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
export npm_config_cache="$_REPO/.tools/npm-cache"
export YARN_CACHE_FOLDER="$_REPO/.tools/yarn-cache"
alias yarn="corepack yarn@1.22.22"
# shellcheck disable=SC1091
[ -f "$_REPO/venv/bin/activate" ] && . "$_REPO/venv/bin/activate"
unset _REPO
