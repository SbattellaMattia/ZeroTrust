FROM ubuntu/squid:latest

# Installa nftables e tools
RUN apt-get update && \
    apt-get install -y \
        nftables \
        iproute2 \
        iputils-ping \
        curl \
        procps \
        netcat-openbsd \
        tcpdump && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copia configurazioni
COPY squid.conf /etc/squid/squid.conf
COPY nftables.conf /etc/nftables.conf
COPY start.sh /start.sh

RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
