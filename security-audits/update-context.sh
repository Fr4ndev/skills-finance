#!/bin/bash
# Staff AI Engineer Context Updater
# Genera un snapshot ultra-avanzado del estado actual del repositorio.

OUT_FILE=".agent/context_snapshot.json"
mkdir -p .agent

echo "{" > $OUT_FILE
echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"," >> $OUT_FILE
echo "  \"git_status\": \"$(git status --short | tr '\n' ',' | sed 's/,$//')\"," >> $OUT_FILE
echo "  \"last_commit\": \"$(git rev-parse HEAD 2>/dev/null || echo "none")\"," >> $OUT_FILE

# Detected Actions (Sema4AI)
if [ -f "package.yaml" ]; then
    echo "  \"actions_detected\": \"sema4ai\"," >> $OUT_FILE
else
    echo "  \"actions_detected\": \"none\"," >> $OUT_FILE
fi

# Service Health (Mock check)
echo "  \"services_health\": {" >> $OUT_FILE
echo "    \"ccxt\": \"$(python3 -c "import ccxt; print('ok')" 2>/dev/null || echo "error")\"," >> $OUT_FILE
echo "    \"arkham_api\": \"$(curl -s -o /dev/null -w "%{http_code}" https://api.arkhamintelligence.com/health 2>/dev/null || echo "unknown")\"" >> $OUT_FILE
echo "  }," >> $OUT_FILE

# Known Issues count
ISSUES_COUNT=$(grep -c "🚨" .agent/KnownIssues.md 2>/dev/null || echo 0)
echo "  \"known_issues_count\": $ISSUES_COUNT" >> $OUT_FILE

echo "}" >> $OUT_FILE

echo "[+] Context snapshot updated in $OUT_FILE"
