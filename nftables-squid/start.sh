#!/bin/bash

set -e

echo "==================================="
echo "FIREWALL-PROXY STARTUP"
echo "==================================="

# Applica nftables
echo "Applying nftables rules..."
nft -f /etc/nftables.conf

echo "✓ nftables rules applied"
echo ""

# Verifica network interfaces
echo "Network Interfaces:"
ip addr show | grep -E "inet |eth"
echo ""

# Test connettività pep-envoy
echo "Testing connectivity to pep-envoy..."
if ping -c 2 10.21.0.100 > /dev/null 2>&1; then
    echo "✓ pep-envoy (10.21.0.100) reachable"
else
    echo "WARNING: pep-envoy not reachable!"
fi
echo ""

# Test porte pep-envoy
echo "Testing pep-envoy ports..."
if nc -zv 10.21.0.100 10000 2>&1 | grep -q succeeded; then
    echo "✓ pep-envoy:10000 open"
else
    echo "WARNING: pep-envoy:10000 not reachable"
fi

if nc -zv 10.21.0.100 10001 2>&1 | grep -q succeeded; then
    echo "✓ pep-envoy:10001 open"
else
    echo "WARNING: pep-envoy:10001 not reachable"
fi
echo ""

echo "==================================="
echo "   FIREWALL-PROXY READY"
echo "   HTTP Proxy:  10.20.0.20:8080"
echo "   HTTPS Proxy: 10.20.0.20:8443"
echo "==================================="
echo ""

# Avvia Squid in foreground
echo "Starting Squid..."
exec squid -N -d 1
