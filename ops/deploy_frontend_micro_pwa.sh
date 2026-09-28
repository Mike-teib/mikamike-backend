#!/usr/bin/env bash
set -euo pipefail

DEST="/home/mike/mikamike/app/frontend"
BACKUP_ROOT="/home/mike/mikamike/ops-backups"
SOURCE_DIR=""
EXPECTED_INDEX_SHA=""

usage() {
  cat <<'EOF'
Usage:
  sudo bash ops/deploy_frontend_micro_pwa.sh --source /chemin/frontend-vnext --expected-index-sha SHA256

Déploiement CIBLÉ : index/app/styles/PWA/micro uniquement.
Ne touche pas à parent.html, parent.js, parent.css, .well-known, backend, DB, Caddy, DNS.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE_DIR="${2:-}"; shift 2 ;;
    --expected-index-sha) EXPECTED_INDEX_SHA="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Argument inconnu: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -n "$SOURCE_DIR" && -d "$SOURCE_DIR" ]] || { echo "SOURCE_DIR invalide" >&2; exit 2; }
[[ "$EXPECTED_INDEX_SHA" =~ ^[0-9a-f]{64}$ ]] || { echo "SHA attendu invalide" >&2; exit 2; }
[[ -d "$DEST" ]] || { echo "Destination absente: $DEST" >&2; exit 2; }

FILES=(
  "index.html"
  "app.js"
  "styles.css"
  "manifest.webmanifest"
  "service-worker.js"
  "native-bridge.js"
  "icons/mikamike-192.svg"
  "icons/mikamike-512.svg"
)

for rel in "${FILES[@]}"; do
  [[ -f "$SOURCE_DIR/$rel" ]] || { echo "Source absente: $SOURCE_DIR/$rel" >&2; exit 2; }
done

CURRENT_INDEX_SHA="$(sha256sum "$DEST/index.html" | awk '{print $1}')"
if [[ "$CURRENT_INDEX_SHA" != "$EXPECTED_INDEX_SHA" ]]; then
  echo "REFUS: index.html production a changé." >&2
  echo "attendu=$EXPECTED_INDEX_SHA reel=$CURRENT_INDEX_SHA" >&2
  exit 3
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$BACKUP_ROOT/FRONTEND_MICRO_PWA_BEFORE_$TS"
STAGE="/home/mike/mikamike/.stage-frontend-micro-pwa-$TS"
mkdir -p "$BACKUP/files" "$STAGE"
trap 'rm -rf "$STAGE"' EXIT

{
  echo "timestamp_utc=$TS"
  echo "dest=$DEST"
  echo "index_sha_before=$CURRENT_INDEX_SHA"
  echo "source=$SOURCE_DIR"
} > "$BACKUP/MANIFEST.txt"

find "$DEST" -maxdepth 2 -type f -printf '%P\n' | sort > "$BACKUP/file-list-before.txt"
find "$DEST" -maxdepth 2 -type f -exec sha256sum {} \; | sort > "$BACKUP/sha256-before.txt"

for rel in "${FILES[@]}"; do
  mkdir -p "$BACKUP/files/$(dirname "$rel")" "$STAGE/$(dirname "$rel")"
  if [[ -f "$DEST/$rel" ]]; then
    cp -a "$DEST/$rel" "$BACKUP/files/$rel"
    echo "$rel" >> "$BACKUP/existed-before.txt"
  else
    echo "$rel" >> "$BACKUP/missing-before.txt"
  fi
  cp -a "$SOURCE_DIR/$rel" "$STAGE/$rel"
done

cat > "$BACKUP/ROLLBACK.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
DEST="$DEST"
BACKUP="$BACKUP"
if [[ -f "\$BACKUP/existed-before.txt" ]]; then
  while IFS= read -r rel; do
    mkdir -p "\$DEST/\$(dirname "\$rel")"
    install -m 0644 "\$BACKUP/files/\$rel" "\$DEST/\$rel"
  done < "\$BACKUP/existed-before.txt"
fi
if [[ -f "\$BACKUP/missing-before.txt" ]]; then
  while IFS= read -r rel; do rm -f "\$DEST/\$rel"; done < "\$BACKUP/missing-before.txt"
fi
echo "ROLLBACK_OK \$BACKUP"
EOF
chmod 700 "$BACKUP/ROLLBACK.sh"

for rel in "${FILES[@]}"; do
  mkdir -p "$DEST/$(dirname "$rel")"
  install -m 0644 "$STAGE/$rel" "$DEST/$rel"
done

find "$DEST" -maxdepth 2 -type f -exec sha256sum {} \; | sort > "$BACKUP/sha256-after.txt"

smoke() {
  local url="$1"
  curl --fail --silent --show-error --location --max-time 20 "$url" >/dev/null
}

if ! smoke "https://app.mikamike.fr/" \
   || ! smoke "https://app.mikamike.fr/app.js" \
   || ! smoke "https://app.mikamike.fr/native-bridge.js" \
   || ! smoke "https://app.mikamike.fr/manifest.webmanifest" \
   || ! smoke "https://app.mikamike.fr/service-worker.js"; then
  echo "SMOKE_FAIL -> rollback automatique" >&2
  bash "$BACKUP/ROLLBACK.sh"
  exit 4
fi

if curl --fail --silent --show-error --max-time 20 "https://app.mikamike.fr/api/health" >/dev/null 2>&1; then
  echo "API_HEALTH_OK /api/health"
elif curl --fail --silent --show-error --max-time 20 "https://app.mikamike.fr/health" >/dev/null 2>&1; then
  echo "API_HEALTH_OK /health"
else
  echo "API_HEALTH_FAIL -> rollback automatique" >&2
  bash "$BACKUP/ROLLBACK.sh"
  exit 5
fi

echo "FRONTEND_MICRO_PWA_DEPLOY_OK"
echo "backup=$BACKUP"
echo "rollback=$BACKUP/ROLLBACK.sh"
echo "index_sha_after=$(sha256sum "$DEST/index.html" | awk '{print $1}')"
