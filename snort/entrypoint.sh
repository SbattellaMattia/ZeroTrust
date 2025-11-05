#!/bin/bash

# avvia Snort in background
/usr/sbin/snort -c /etc/snort/snort.conf -i eth0 -A full -u root -g root -D -l /var/log/snort

# Monitor logs per alert in real-time
tail -f /var/log/snort/alerts.log | while read line; do
  if echo "$line" | grep -i "NMAP\|ICMP"; then
    echo "[ALERT] $(date): $line" >> /var/log/snort/high-priority.log
  fi
done
