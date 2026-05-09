#!/bin/bash
# Staff AI Engineer Health Check
# Realiza diagnósticos profundos sobre el sistema y las integraciones.

echo "🔍 Iniciando Health Check de Nivel Staff..."

# 1. Dependencias de Trading
echo -n "[Trading] CCXT Check: "
python3 -c "import ccxt; print('✅ OK')" || echo "❌ FAIL"

# 2. Dependencias de Seguridad
echo -n "[Security] Certipy Check: "
command -v certipy-ad >/dev/null 2>&1 && echo "✅ OK" || echo "❌ MISSING"

# 3. API Keys Presence
echo -n "[Env] ARKHAM_API_KEY: "
[ -z "$ARKHAM_API_KEY" ] && echo "⚠️ MISSING" || echo "✅ SET"

# 4. Git Hygiene
echo -n "[Git] Uncommitted Changes: "
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ CLEAN"
else
    echo "⚠️ DIRTY (Review required)"
fi

echo "-----------------------------------"
echo "Diagnóstico completado."
