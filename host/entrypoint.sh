#!/bin/bash
# default: se non è passata, usiamo pep:8080 come proxy (modifica se diverso)
: "${HTTP_PROXY:=http://pep:8080}"
: "${HTTPS_PROXY:=http://pep:8080}"
export HTTP_PROXY HTTPS_PROXY

echo "Container $(hostname) starting. USER_ID=${USER_ID:-unknown}, NETWORK=${NETWORK:-unknown}"
# esegui il comando dato
exec "$@"
