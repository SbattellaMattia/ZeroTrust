<img width="300" height="182" alt="image" src="https://github.com/user-attachments/assets/a770c3ac-c014-4324-859f-47a9f4b7a32b" />



## Introduzione
Splunk svolge il ruolo di **SIEM** e piattaforma di **log management** nel progetto ZeroTrust. Riceve eventi tramite **HTTP Event Collector (HEC)**, li indicizza nell’archivio dedicato `zt`, mette a disposizione la **Web UI** per ricerche (SPL), dashboard e alerting, e fornisce **API di management** per interrogazioni e operazioni operative. Nel contesto del progetto, Splunk è la sorgente autorevole per l’osservabilità applicativa e di sicurezza.

---

## Configurazione

L’app `zt_base` definisce l’indice `zt` nel file `./splunk-apps/zt_base/default/indexes.conf`. La stanza `[zt]` è il contenitore logico dove Splunk scrive e legge gli eventi del progetto. I percorsi `homePath`, `coldPath` e `thawedPath` indicano rispettivamente dove finiscono i bucket **hot/warm** (scrittura e dati recenti), dove vengono spostati i bucket **cold** (dati meno recenti) e dove si **ripristinano** eventuali archivi congelati (**thawed**). In pratica: gli eventi inviati al progetto arrivano in `index=zt` e ruotano automaticamente tra questi percorsi secondo il ciclo di vita standard di Splunk.

---

## Query di esempi (UI)

- Esempio di eventi di login `Keycloak` con sourcetype `keycloak:login` per l’utente `mrossi`, vengono registrati sia `login_success` che `login_failed`, con campi di dettaglio come `com.docker.compose.service=keycloak`, `container_name=/keycloak` e `src_ip=10.24.0.2`, che permettono di collegare ogni tentativo di autenticazione al container ed all’IP sorgente che lo ha generato.

<img width="1167" height="662" alt="splunk-login" src="https://github.com/user-attachments/assets/90a20488-05aa-4470-84fa-073360c0f2b5" />


---

- Esempio di un evento di log del servizio `pep-envoy` con sourcetype `httpevent`. Nei dettagli compaiono campi utili per l’analisi del traffico in uscita, come `direction=EGRESS`, `method=GET`, `response_code=302`, `src_ip=10.24.0.2` e `upstream_cluster=internal-service`.

<img width="1593" height="803" alt="splunk-pep" src="https://github.com/user-attachments/assets/bfa3c5b8-cdd2-4bb2-ab8f-c412135a2db1" />


---
  
- Esempio di evento di allarme `Snort` con sourcetype `snort:alert`: la firma `[ALERT] TCP SYN Scan` segnala uno scan TCP a bassa severità, mostrando in chiaro indirizzi e porte coinvolte (`src_ip=10.21.0.2`, `src_port=50959`, `dest_ip=10.21.0.3`, `dest_port=8080`) insieme a `timestamp`, che consentono di ricostruire in modo puntuale il tentativo di scansione.

<img width="1134" height="380" alt="splunk-snort" src="https://github.com/user-attachments/assets/f5ad6ff5-3d19-4e02-bf87-9cc88ff3b724" />







