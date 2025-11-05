FROM frapsoft/snort
# Copy configuration e rules
COPY snort.conf /etc/snort/snort.conf
COPY custom.rules /etc/snort/rules/custom.rules

# Create log directories
RUN mkdir -p /var/log/snort/logs && \
    chown -R root:root /var/log/snort && \
    chmod 777 /var/log/snort

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD test -f /var/log/snort/alerts.log || exit 1

ENTRYPOINT ["snort", "-c", "/etc/snort/snort.conf"]
CMD ["-i", "any", "-A", "full", "-u", "root", "-g", "root"]
