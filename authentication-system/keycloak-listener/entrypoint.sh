#!/bin/sh
set -e

echo " Attesa Keycloak "

# Attesa che Keycloak risponda sulla porta 8081
until curl -s http://keycloak:8081/realms/master > /dev/null; do
  echo " Keycloak non pronto "
  sleep 5
done

echo " Avvio Keycloak listener "
exec python -u /app/listener.py