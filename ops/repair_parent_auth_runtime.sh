#!/usr/bin/env bash
set -euo pipefail

APP="/home/mike/mikamike"
cd "$APP"

FILES=(
  "docker-compose.yml"
  "docker-compose.integ.yml"
  "docker-compose.r54f.yml"
  "releases/mikepilot_bridge.override.yml"
)

for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "[STOP] overlay manquant: $f"
    exit 2
  fi
done

COMPOSE=(docker compose)
for f in "${FILES[@]}"; do COMPOSE+=(-f "$f"); done

if ! "${COMPOSE[@]}" config --services | grep -qx "backend"; then
  echo "[STOP] service backend introuvable dans la pile compose"
  exit 3
fi

echo "[1/5] Etat actuel — valeurs secrètes masquées"
docker exec mikamike-backend-1 python - <<'PY' 2>/dev/null || true
import os
for name in ("MIKA_JWT_SECRET","MIKA_PSEUDO_SECRET","MIKA_AUTH_MODE","MIKA_ENV"):
    value = os.getenv(name)
    if name.endswith("_SECRET"):
        state = "PRESENT" if value and len(value.strip()) >= 16 else "MISSING_OR_INVALID"
        print(f"{name}={state}")
    else:
        print(f"{name}={'PRESENT' if value else 'MISSING'}")
PY

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$APP/ops-backups"
docker inspect mikamike-backend-1 > "$APP/ops-backups/backend-inspect-$stamp.json" 2>/dev/null || true
chmod 600 "$APP/ops-backups/backend-inspect-$stamp.json" 2>/dev/null || true

echo "[2/5] Recréation du seul service backend avec la pile complète d'overlays"
"${COMPOSE[@]}" up -d --no-deps --force-recreate backend

echo "[3/5] Vérification de la présence des secrets, sans afficher leur valeur"
docker exec mikamike-backend-1 python - <<'PY'
import os, sys
bad = False
for name in ("MIKA_JWT_SECRET","MIKA_PSEUDO_SECRET"):
    value = (os.getenv(name) or "").strip()
    ok = len(value) >= 16
    print(f"{name}={'OK' if ok else 'MISSING_OR_INVALID'}")
    bad |= not ok
for name in ("MIKA_AUTH_MODE","MIKA_ENV"):
    print(f"{name}={'PRESENT' if os.getenv(name) else 'MISSING'}")
if bad:
    sys.exit(12)
PY

echo "[4/5] Santé locale"
for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
    echo "healthz=OK"
    break
  fi
  sleep 2
done
curl -fsS http://127.0.0.1:8000/healthz >/dev/null

echo "[5/5] Contrôle public auth parent"
tmp="$(mktemp)"
code="$(curl -sS -o "$tmp" -w '%{http_code}' https://app.mikamike.fr/api/v1/comptes/moi || true)"
detail="$(python3 - "$tmp" <<'PY'
import json,sys
try:
    obj=json.load(open(sys.argv[1], encoding="utf-8"))
    print(obj.get("detail",""))
except Exception:
    print("")
PY
)"
rm -f "$tmp"

echo "HTTP=$code DETAIL=$detail"
if [[ "$code" != "401" || "$detail" != "token_absent" ]]; then
  echo "[STOP] auth parent non rétablie; attendu HTTP 401 token_absent"
  exit 13
fi

echo "[OK] AUTH_PARENT_RUNTIME_RESTORED"
