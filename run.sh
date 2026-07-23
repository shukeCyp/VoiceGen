#!/usr/bin/env bash
# VoiceGen launcher: build Vue static assets, then start pywebview via uv.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

FRONTEND_DIR="$ROOT/frontend"
DIST_INDEX="$FRONTEND_DIR/dist/index.html"
REQUIREMENTS="$ROOT/requirements.txt"

log() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# ── tools ───────────────────────────────────────────────────
command -v npm >/dev/null 2>&1 || die "未找到 npm，请先安装 Node.js"
command -v uv  >/dev/null 2>&1 || die "未找到 uv，请先安装: https://docs.astral.sh/uv/"
command -v ffmpeg >/dev/null 2>&1 || log "警告: 未找到 ffmpeg，配音合并可能失败"

# ── 1) build frontend (static files for pywebview) ──────────
log "编译前端 (Vue → frontend/dist)…"
cd "$FRONTEND_DIR"
if [[ ! -d node_modules ]]; then
  log "安装前端依赖 (npm install)…"
  npm install
fi
npm run build
cd "$ROOT"

[[ -f "$DIST_INDEX" ]] || die "前端构建失败：缺少 $DIST_INDEX"
log "静态资源就绪: $DIST_INDEX"

# ── 2) start Python with uv (pywebview loads local dist) ────
# main.py 无 --dev 时使用 frontend/dist/index.html 的 file:// 静态页
log "使用 uv 启动 VoiceGen (pywebview + 静态前端)…"
exec uv run --with-requirements "$REQUIREMENTS" python "$ROOT/main.py" "$@"
