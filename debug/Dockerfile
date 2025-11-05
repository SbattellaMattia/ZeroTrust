FROM alpine:latest

# Installa tools di rete e debugging
RUN apk update && apk add --no-cache \
    nmap \
    nmap-scripts \
    curl \
    wget \
    netcat-openbsd \
    bind-tools \
    tcpdump \
    iputils \
    bash \
    && rm -rf /var/cache/apk/*

# Mantieni il container attivo
CMD ["/bin/bash"]
