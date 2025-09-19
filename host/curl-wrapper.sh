#!/bin/bash
# curl wrapper dinamico: legge host_base/headers.map e aggiunge header automaticamente

REAL_CURL="/usr/bin/curl.real"
[ -x "$REAL_CURL" ] || REAL_CURL="/usr/bin/curl"

MAP_FILE="/etc/headers.map"

headers=()
proxy_headers=()
PROXY_ARG=()

# se c'è il proxy definito
if [ -n "${HTTP_PROXY:-}" ]; then
  PROXY_ARG=(--proxy "${HTTP_PROXY}")
fi

# leggi ogni riga del file headers.map
while IFS='=' read -r envvar headername; do
  # salta righe vuote o commenti
  [ -z "$envvar" ] && continue
  [[ "$envvar" =~ ^# ]] && continue
  val="$(printenv "$envvar" || true)"
  if [ -n "$val" ]; then
    headers+=("-H" "$headername: $val")
    proxy_headers+=(--proxy-header "$headername: $val")
  fi
done < "$MAP_FILE"

# esegui curl reale
exec "$REAL_CURL" "${PROXY_ARG[@]}" "${proxy_headers[@]}" "${headers[@]}" "$@"
