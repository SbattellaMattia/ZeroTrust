# Management - Snort, Fluentd e Splunk

La sezione *management* del progetto raccoglie i componenti dedicati al monitoraggio ed alla correlazione degli eventi di sicurezza.
<img width="863" height="174" alt="image" src="https://github.com/user-attachments/assets/a894d22a-de2d-40ed-ba71-7f597d5905b7" />

## **Snort**
Container che analizza il traffico di rete e genera alert quando rileva pattern sospetti o potenzialmente malevoli. Il container `snort-ids` gira in modalità IDS e ispeziona il traffico di rete secondo le regole definite in `snort.conf` e `custom.rules`. Quando una regola viene attivata, Snort scrive una riga di alert nel file `/var/log/snort/alert`. Questi file sono salvati in un volume condiviso (`snort-logs`), montato sia da Snort sia da Fluentd. 
## **Fluentd**
Raccoglie, normalizza e trasforma in eventi strutturati i log dei vari servizi secondo le regole definite nel  `fluent.conf`, per poi arricchirli con metadati. Questo avviene tramite il driver di logging configurato nel `docker-compose.yaml`. In questo modo i log applicativi confluiscono nello stesso punto di raccolta e, una volta normalizzati, Fluentd inoltra gli eventi verso il container `splunk` utilizzando l’**HTTP Event Collector (HEC)**.
## **Splunk**
Motore di indicizzazione e ricerca che memorizza gli eventi nell' indice creato per il nostro progetto (`zt`) e li rende consultabili tramite dashboard e query di analisi. Splunk rende disponibili query indicizzate per il calcolo del punteggio che richiede il `trust-service` e che successivamente passerà al `pdp` per la decisione.
