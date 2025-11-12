# Fluentd                    <img width="50" height="50" alt="image" src="https://github.com/user-attachments/assets/726fdf33-6c40-47f0-ac38-c9c281a1a33a" />


Fluentd è il componente centrale di log management del progetto.  
Si occupa di raccogliere i log dai vari servizi (in particolare Snort, Envoy e Keycloak), normalizzarli in un formato coerente e inoltrarli a **Splunk** tramite HTTP Event Collector (HEC) per l’indicizzazione nell’indice `zt`.

La configurazione principale è definita in:
- `management/fluentd/conf/fluent.conf`- file principale di configurazione di Fluentd che definisce le **sorgenti** di log, i **filtri** di trasformazione/arricchimento e gli **output** verso Splunk.
- `management/fluentd/buffer/` – directory usata per i file di buffer e i file di posizione (`*.pos`). Utilizzato come volume condiviso con Snort.

## Sorgenti di log

In `fluent.conf` Fluentd riceve log da tre canali principali:

- **Driver di logging di Docker**: Una sorgente `@type forward` in ascolto sulla porta `24224` riceve i log dei container inviati tramite il logging driver Fluentd, posti in ogni container (vedi compose).

- **Alert di Snort**: Una sorgente `@type tail` legge il file `/var/log/snort/alert` (montato in volume condiviso con il container Snort) e lo tagga come `snort.alert`.  
  Il parser regexp estrae campi come timestamp, IP sorgente/destinazione, porte e priorità dell’evento.

- **Monitoraggio interno di Fluentd**: Una sorgente `@type monitor_agent` espone informazioni sullo stato di Fluentd (utilizzata solo per diagnostica).

## Filtri e normalizzazione

Prima di inviare gli eventi a Splunk, Fluentd applica una serie di filtri che arricchiscono e uniformano i log:
  
- **Snort (`snort.alert` e `snort.syslog`)**  
I log con tag `snort.alert` vengono trasformati da un filtro `record_transformer` che:
  - imposta `index = zt` e `sourcetype = snort:alert`;
  - calcola il campo `severity` (high / medium / low) a partire dalla priorità di Snort;
  - rimuove campi tecnici non necessari (`gid`, `rev`).

  Un filtro analogo riallinea eventuali log Snort arrivati in formato syslog al medesimo `sourcetype` e schema.

- **Envoy (`pep-envoy.**`)**  
Un filtro `grep` seleziona solo le righe che contengono `[INGRESS]` o `[EGRESS]` nel campo `log`, cioè i log strutturati del PEP.  
Successivamente un filtro `parser` con `@type multi_format` analizza queste righe e ne estrae campi come:
  - direzione (INGRESS / EGRESS),
  - timestamp,
  - informazioni sulla richiesta e sulla risposta (upstream, status code, ecc.).

  In questo modo i log di Envoy diventano eventi strutturati, adatti alle ricerche e alle dashboard in Splunk.

- **Keycloak (`**.keycloak.**`)**  
Due filtri in cascata gestiscono i log degli eventi di autenticazione:
  - un `parser` regexp estrae tipo di evento, utente e IP sorgente dai log Keycloak;
  - un `record_transformer` imposta:
     - `index = zt`,
     - `sourcetype = keycloak:login`,
     - un campo `event` normalizzato (es. login_success / login_failed),
     - i campi `user` e `src_ip` consolidati dalle varie forme con cui Keycloak scrive queste informazioni.

## Output verso Splunk

La sezione finale di `fluent.conf` definisce un `<match **>` con uscita `@type copy`:

- un primo `store` invia gli eventi su `stdout` (utile per debug);
- un secondo `store` usa il plugin `@type splunk_hec` per spedire tutti gli eventi a **Splunk**

Il buffer è di tipo file (`/fluentd/buffer/hec.*.buffer`), con flush periodico e retry infinito, così da non perdere eventi in caso di temporanee indisponibilità di Splunk.





