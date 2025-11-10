// Proxy manuale: instrada tutto attraverso il PEP
user_pref("network.proxy.type", 1);
// HTTP → PEP porta HTTP (redir verso HTTPS)
user_pref("network.proxy.http", "pep-envoy");
user_pref("network.proxy.http_port", 10000);
// Usa le stesse impostazioni per tutti i protocolli
user_pref("network.proxy.share_proxy_settings", true);
// Esclusioni locali (adatta se necessario)
user_pref("network.proxy.no_proxies_on", "localhost, 127.0.0.1, *.local");
