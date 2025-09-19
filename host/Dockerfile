FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# rinomina curl reale
RUN if [ -x /usr/bin/curl ]; then mv /usr/bin/curl /usr/bin/curl.real; fi

# copia wrapper e mapping
COPY curl-wrapper.sh /usr/local/bin/curl
COPY headers.map /etc/headers.map
RUN chmod +x /usr/local/bin/curl && ln -sf /usr/local/bin/curl /usr/bin/curl

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
