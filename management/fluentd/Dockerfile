FROM fluent/fluentd:latest

USER root

# Python + requests via APT (niente pip -> evita PEP 668)
RUN apt-get update && \
    apt-get install -y python3 python3-requests ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Plugin Splunk HEC
RUN gem install fluent-plugin-splunk-hec

# Dir utili e permessi
RUN mkdir -p /fluentd/etc /fluentd/buffer /scripts && \
    chown -R fluent:fluent /fluentd /scripts

USER fluent
# fluentd leggerà /fluentd/etc/fluent.conf di default
