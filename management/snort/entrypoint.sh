#!/bin/bash

/usr/sbin/snort -c /etc/snort/snort.conf -i eth0 -A fast -u root -g root -D -l /var/log/snort

sleep 1

# Tail sul file alert (ora formato fast = 1 riga per evento)
tail -f /var/log/snort/alert 2>/dev/null | while read line; do
  if echo "$line" | grep -iE "NMAP|ICMP"; then
    echo "[ALERT] $(date): $line" >> /var/log/snort/high-priority.log
  fi
done
