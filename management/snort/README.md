#  Snort — Intrusion Detection System (IDS) <img width="120" height="350" alt="image" src="https://github.com/user-attachments/assets/8b4226f2-7689-4067-8e03-f08b046f018b" />


##  Descrizione generale

Snort è un sistema di Intrusion Detection System (IDS) integrato nell’architettura Zero Trust con lo scopo di rilevare tentativi di **scansione delle porte** e **ping** tra le varie reti interne (come internal_net, prod_net, dev_net, etc).

Funziona come un sensore passivo che monitora il traffico e genera alert quando identifica pattern tipici di strumenti come **Nmap** o comportamenti **ICMP** anomali.

## Funzionamento generale

Il modulo Snort si basa su due componenti principali:

- **Configurazione**  
  Definisce i parametri di rete, le interfacce monitorate, i percorsi delle regole e le modalità di logging.  
  Le reti interne vengono identificate come *HOME_NET* , mentre la rete esterna è definita come *EXTERNAL_NET*.

- **Regole personalizzate**  
  Contiene le regole create per rilevare comportamenti malevoli o scansioni di rete.  
  Le regole sono suddivise in due categorie principali:
  - **ICMP Detection** → intercetta tentativi di *ping*, *echo request/reply* o *timestamp request* tra le reti interne.  
  - **Port Scanning Detection (Nmap)** → identifica pattern tipici di *SYN scan*, *FIN scan*, *NULL scan* e *Xmas scan* eseguiti da strumenti di ricognizione come *Nmap*.

---

## Log e comportamento

Snort produce due flussi principali di log:

| File | Descrizione |
|------|--------------|
| `alerts.log` | Log completo di tutti gli eventi rilevati. |
| `high-priority.log` | Log filtrato, contenente solo eventi di alta criticità (ICMP e scansioni Nmap). |

Ogni alert registrato contiene:
- Timestamp dell’evento  
- Tipo di protocollo e pacchetto rilevato  
- IP sorgente e destinazione  
- Messaggio di allerta.

## Esempio pratico Nmap

Durante una simulazione di attacco condotta con **Nmap**, il sistema **Snort IDS** ha rilevato in tempo reale una serie di pacchetti caratteristici di una **scansione di tipo TCP Xmas**.

In questo scenario:
- l’attaccante (Nmap su Kali) tenta di analizzare le porte del container pep-envoy tramite pacchetti “Xmas”;
- Snort, monitorando la rete dmz_net, genera diversi alert istantanei, riportando l’evento nei log di sistema (alerts.log e high-priority.log).
---

### 1. Output Nmap (macchina sorgente)

La seguente immagine mostra l’esecuzione del comando:
```bash
sudo docker exec debug nmap -sX pep-envoy
```


<img width="1154" height="405" alt="nmap" src="https://github.com/user-attachments/assets/f29aa461-8c7c-4bcd-aba1-a99c6a1898a2" />


Il risultato mostra diverse porte TCP aperte o filtrate — un comportamento tipico dei sistemi che rispondono parzialmente ai pacchetti “Xmas”, utilizzati per individuare porte attive senza completare il classico handshake TCP.


### 2. Log Snort

La seconda immagine mostra il contenuto del log generato da **Snort IDS** in tempo reale.  


<img width="1121" height="754" alt="nmap_alert" src="https://github.com/user-attachments/assets/629d9f22-b91a-412f-9dc1-aef57d5848e1" />



L’analizzatore, intercetta e registra più pacchetti di tipo **TCP Xmas Scan**, generando avvisi con priorità elevata.

Ogni evento contiene:

- **Timestamp dell’analisi**  
- **Indirizzo IP sorgente:** `10.21.0.3` *(container debug)* 
- **Indirizzo IP destinazione:** `10.21.0.100` *(pep-envoy)*  
- **Flag TCP:** `FPU` *(FIN, PUSH, URG)*  
- **Descrizione:** `[ALERT] TCP Xmas Scan`

Questo dimostra che **Snort** è in grado di identificare i pacchetti manipolati tipici delle **scansioni furtive**, generando un *alert* specifico per ogni pacchetto rilevato.


## Esempio pratico ICMP

Durante un test di connettività interno tra container, il sistema Snort IDS ha intercettato in tempo reale i pacchetti **ICMP** Echo Request / Echo Reply generati da un comando **ping**.
Questo esempio dimostra la capacità di Snort di rilevare attività di rete apparentemente innocue ma potenzialmente utili a fini di ricognizione.

### 1. Output Ping (macchina sorgente)
In modo analogo a quanto fatto prima:
```bash
docker exec -it debug sh
ping pep-envoy
```
Il risultato mostra l'invio di pacchetti ICMP Echo Request verso pep-envoy.

### 2. Log Snort

Snort intercetta i pacchetti **Echo Reply** egenera automaticamente un alert nel file.
Ogni evento contiene:

- **Timestamp dell’analisi**  
- **Indirizzo IP sorgente:** `10.21.0.3` *(container debug)*  
- **Indirizzo IP destinazione:** `10.21.0.100` *(pep-envoy)*  
- **Tipo ICMP:** `Type:0 (Echo Reply)`
- **Descrizione:** `[ALERT] TCP Xmas Scan`

Questo comportamento conferma che **Snort** è in grado di rilevare in modo preciso anche **pacchetti ICMP** standard.

## Snort e Splunk
Gli eventi generati da Snort sono raccolti e normalizzati da Fluentd, ed infine visualizzati in Splunk.
<img width="1134" height="380" alt="splunk-snort" src="https://github.com/user-attachments/assets/5c092496-5fef-4fc0-b8f8-b053e22e19b4" />
> Per maggiori dettagli visualizzare la sezione dedicata.

