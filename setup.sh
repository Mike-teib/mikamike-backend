#!/usr/bin/env bash
# setup.sh — Environnement de développement/test MikaMike reproductible.
#
# - crée un virtualenv isolé (.venv) : n'utilise PAS les paquets système
#   (certains environnements ont un `cryptography` système cassé) ;
# - installe les dépendances (runtime + dev) ;
# - pose des secrets de TEST factices (jamais de clé réelle, jamais de prod) ;
# - lance la suite de tests hors ligne (aucune API payante, aucun réseau requis).
#
# Usage :
#   ./setup.sh            # installe + lance les tests
#   ./setup.sh --no-tests # installe seulement
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
VENV="${VENV:-.venv}"

if [ ! -x "$VENV/bin/python" ]; then
  "$PYTHON" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r requirements.txt -r requirements-dev.txt

# Secrets de TEST uniquement (>= 16 caractères, non génériques). Jamais en prod.
export MIKA_JWT_SECRET="${MIKA_JWT_SECRET:-test-jwt-secret-not-for-prod-0123456789}"
export MIKA_PSEUDO_SECRET="${MIKA_PSEUDO_SECRET:-test-pseudo-secret-not-for-prod-0123456789}"
# Bases SQLite jetables (répertoire temporaire), jamais une base réelle.
TMPD="$(mktemp -d)"
export MIKA_DB_URL="${MIKA_DB_URL:-sqlite:///$TMPD/mika_test.db}"
export BILLING_DB_URL="${BILLING_DB_URL:-sqlite:///$TMPD/billing_test.db}"
# Stripe volontairement NON configuré : les gardes renvoient une erreur explicite.
unset STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET STRIPE_PRICE_ID || true

if [ "${1:-}" != "--no-tests" ]; then
  "$VENV/bin/python" -m ruff check .
  "$VENV/bin/python" -m pytest -q
fi

echo "OK — environnement prêt. Activer : source $VENV/bin/activate"
