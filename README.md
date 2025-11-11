# ZeroTrust

## Introduzione
Questo progetto universitario per il corso di laurea in Ing. Informatica ed Automazione Univpm (corso di Advanced Cyber Security for IT) è una simulazione di un'infrastruttura **Zero Trust** containerizzata con Docker. L'obiettivo è mostrare un'architettura semplice ma realistica che include: firewall (nftables), bastion host, keycloak (Identity Provider), PEP (Envoy), PDP (OPA), Trust Service per calcolo dinamico della fiducia, Squid (forward proxy), servizi interni (un web service, produzione, sviluppo), oltre a strumenti di monitoring/IDS (Snort) e raccolta log (Splunk).

<img width="1229" height="818" alt="image" src="https://github.com/user-attachments/assets/48818cd9-a5b0-4284-b176-95e05ae5064b" />


### Contesto

Il progetto adotta i principi di Zero Trust secondo NIST SP 800‑207, applicando in modo coerente i sette pilastri che guidano la progettazione, il disegno dei flussi e l’operatività quotidiana dell’ambiente di laboratorio. L’obiettivo non è proporre un’unica architettura “giusta”, ma mostrare come i principi Zero Trust possano essere tradotti in scelte concrete di segmentazione, identità, controllo degli accessi e osservabilità, come raccomandato dallo standard NIST.[^1][^2]

- 1) Resources
Tutti gli elementi dell’ambiente (dati, servizi applicativi, proxy, database, dispositivi/host) sono trattati come risorse da proteggere in modo uniforme, senza eccezioni o “isole fidate”. Anche gli endpoint che simulano postazioni utente sono considerati risorse enterprise ai fini delle policy.[^2][^3]
- 2) Communication
Ogni comunicazione è protetta e valutata a prescindere dalla posizione di rete, eliminando il concetto di “interno automaticamente fidato”; i flussi passano attraverso punti di controllo dedicati e sono soggetti alle stesse regole di verifica.[^4][^2]
- 3) Per‑session access
L’accesso alle risorse è concesso su base sessione: ogni richiesta instaura un contesto valutato puntualmente, senza ereditare fiducia da connessioni precedenti o da appartenenza alla rete.[^2][^4]
- 4) Dynamic policy
Le decisioni di accesso sono determinate da policy dinamiche che combinano identità, ruolo, risorsa/azione richiesta, contesto ambientale e un punteggio di fiducia aggiornato; ciò consente di applicare il principio del minimo privilegio in modo adattivo.[^3][^2]
- 5) Monitoring
Tutte le risorse e le azioni sono monitorate in modo continuo per garantire protezione dei dati, visibilità sugli eventi e capacità di risposta; i log e la telemetria alimentano analisi e auditing centralizzati.[^3][^2]
- 6) Authentication e authorization
Ogni accesso è preceduto da autenticazione e autorizzazione dinamiche e rigorose; non vengono riconosciute scorciatoie basate sull’ubicazione in rete o su privilegi impliciti.[^5][^2]
- 7) Continuous improvement
Lo stato degli asset, dell’infrastruttura e delle comunicazioni è raccolto e analizzato per migliorare progressivamente la postura di sicurezza; la telemetria guida l’aggiornamento delle policy e dei controlli.[^2][^3]

Nota importante: NIST sottolinea che Zero Trust è un insieme di principi guida, non una singola architettura prescrittiva; l’adozione può essere graduale, applicando per priorità i tenets più rilevanti per il contesto.[^6][^1]

Allineamento nel nostro laboratorio:

- Resources: tutte le componenti sono trattate come risorse protette e soggette a controllo.[^2]
- Communication: i flussi attraversano punti di controllo dedicati e non ereditano fiducia.[^2]
- Per‑session access: le connessioni verso i servizi sono gestite per sessione e rivalutate.[^2]
- Dynamic policy: le policy sono valutate dinamicamente in base a identità e rischio contestuale.[^2]
- Monitoring: telemetria e log centralizzati abilitano visibilità end‑to‑end.[^3]
- Authentication/Authorization: l’accesso è subordinato a verifica identità e permessi aggiornati.[^5]
- Continuous improvement: la raccolta di informazioni guida l’evoluzione delle difese.[^3]

Riferimenti: NIST SP 800‑207 (Zero Trust Architecture) e progetto NCCoE “Implementing a Zero Trust Architecture”, che forniscono linee guida e un approccio pratico per scenari dimostrativi analoghi al nostro laboratorio.[^1][^6]


[^1]: https://nvlpubs.nist.gov/nistpubs/specialpublications/NIST.SP.800-207.pdf

[^2]: https://stratixsystems.com/seven-tenets-of-zero-trust-architecture/

[^3]: https://www.cisa.gov/sites/default/files/2023-04/CISA_Zero_Trust_Maturity_Model_Version_2_508c.pdf

[^4]: https://terrazone.io/nist-sp-800-207/

[^5]: https://csrc.nist.gov/pubs/sp/800/207/a/final

[^6]: https://www.nccoe.nist.gov/sites/default/files/legacy-files/zta-project-description-final.pdf


---

## Tabella componenti

| Componente                |Immagine| Funzionamento (ruolo)| Reti* | Note pratiche   |
| ------------------------- | ---|-------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------: | ------------------------------------------------------------------------------- |
|`Allowed-host`                |-| Container esterno, può raggiungere il sito azienda.  |`external_net` | Per raggiungere l'interno passa per il `pep-envoy`| 
|`Blocked-host`                |-| Container esterno, bloccato dal firewall in `pep-envoy`.  |`external_net` |-| 
|`Allowed-server`                |-| Simula un server raggiungibile dagli host interni.  |`external_net` | Per raggiungere l'esterno passa per il `pep-envoy`| 
|`Blocked-server`                |-| Simula un serverbloccato dal proxy di envoy  |`external_net` |-| 
|`PEP` (Envoy)        |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/1380c555-96b0-4597-b6c2-97fdd8fd9239" />| Policy Enforcement Point: intercetta tutte le richieste, chiede decisione al PDP e applica le policy.  |  `external_net`,`internal_net`, `dmz_net`, `prod_net`, `dev_net` | Se non si è autenticati effettua il redirect verso `Keycloak` |
|`Keycloak`           |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/c70e1a39-b3da-4dc6-a00e-f83a95992356" />| Identity Provider (OIDC/OAuth2).  | `external_net`,`internal_net`, `dmz_net`, `prod_net`, `dev_net` | Autentica e rilascia un token di accesso contenente le informazionli necessarie al pdp per prendere decisioni di autorizzazione |
|`PDP` (OPA)          |<img width="100" height="100" alt="image" src="https://github.com/user-attachments/assets/6ea139b3-e462-4ff4-bccf-2249f126b764" />| Policy Decision Point: valuta le policy basate su input (identità, risorsa, azione, trust score) e risponde ALLOW/DENY.    |  `internal_net` | Interroga il Trust Service per ottenere il trust score dinamico.                |
|`Trust Service`      |-| Calcola e ritorna il trust score dinamico.|`internal_net` | Fornisce input numerico/qualitativo al PDP basato sulla storia dell'utente registrata nel DB postgres. Aggiunto per separare le operazioni di calcolo e interazione con il db dal resto.|
|`Internal Web Service`|-| Servizio esposto in DMZ.   |`dmz_net`   |Non direttamente esposto a Internet: accesso tramite keycloak+PEP.|
|`Prod-host`          |-| Host simulato in rete produzione.          |`prod_net`|- |
|`Dev-host`           |-| Host simulato in rete sviluppo.            |`dev_net` |-|
|`Snort`              |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/452991a6-1408-4db8-a75b-9a6304819c5e" />| IDS (o IDS/IPS se configurato): monitora il traffico su interfacce di rete multiple.|`dmz_net`, `internal_net`, `prod_net`, `dev_net` | Usato in modalità IDS (non IPS) per evitare blocchi accidentali e mantenere la rete semplice.|
|`Splunk`             |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/471aefb3-fe12-4151-8b74-4d87aa7f55e7" />| SIEM / collector di log centralizzato   | `management_net`, `internal_net`| I container inviano i log su `management_net`; Splunk analizza e visualizza eventi.|
|`Fluentd`            |<img width="100" height="100" alt="image" src="https://github.com/user-attachments/assets/0804836e-e0d5-48b9-8935-fb40ef0fb05f" />| Normalizza e raccoglie logs per splunk  | `management_net` | Aggregazione e forwarding dei log verso Splunk.|

    
>Nelle reti è stata omessa quella di management, presente ovunque a meno del container `Ext`.
---

## Tabella componenti rimossi

| Componente                |Immagine| Funzionamento (ruolo)| Reti* | Note pratiche   |
| ------------------------- | ---|-------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------: | ------------------------------------------------------------------------------- |
|`Database`	          |<img width="100" height="100" alt="image" src="https://github.com/user-attachments/assets/997817dc-609c-418b-a3a9-2ea3696a866e" />| Contiene gli utenti con i relativi punteggi. Interrogati dal Trust Service.| `internal_net`| Immagine di Postgres.|
|`Firewall`           |<img width="100" height="100" alt="4D5D7B84-C363-4368-A115-E3EB76503672" src="https://github.com/user-attachments/assets/f2df7df2-249a-4e1b-99e6-8e394b6b9db1" />| Firewall nftables; applica regole di filtraggio e limitazioni di percorso . |      `external_net`, `dmz_net`| Successore di iptables. Funge da unico punto di accesso e uscita dalla rete aziendale |
|`Bastion-Host`       || Punto d'ingresso sicuro per amministrazione. |`dmz_net` | - |
|`Squid`              |<img width="100" height="100" alt="image" src="https://github.com/user-attachments/assets/e79ab872-24ab-4ce6-a433-3da3c19b23b1" />|Forward proxy per traffico in uscita.         |`dmz_net` | Unico container predisposto dal `Firewall` al traffico in uscita dalla rete.|

Abbiamo rimosso alcuni container per semplificare l’architettura e ottimizzare il flusso operativo. `pep-envoy` copre sia il firewalling di livello 3 sia quello di livello 7, rendendo superflui componenti dedicati. Il bastion host, per ora, resta fuori e potrà essere reintrodotto in sviluppi futuri. La persistenza degli eventi su database è stata sostituita con Splunk, piattaforma nativa per raccolta, indicizzazione e analisi degli eventi.
## Reti Docker

* `external_net` — simula Internet (client esterni).
* `dmz_net` — DMZ / network di perimeter.
* `internal_net` — rete dei servizi di controllo.
* `prod_net` — rete produzione (host produzione).
* `dev_net` — rete sviluppo (host sviluppo).
* `management_net` — rete per la raccolta log / management (Splunk).

> Nota: La gestione delle reti è interamente demandata a Docker, che, una volta definite, configurate e associate ai rispettivi container, provvederà a crearle e a gestire le comunicazioni tra di essi. Solo alcuni container hanno ip statici per i test di firewall e proxy.

---

## Possibili scenari
### Legenda
🔴 Rosso: richiesta applicativa dall’esterno verso il servizio interno.  
🟢 Verde: ciclo di autenticazione tra PEP e Keycloak (redirect/login/ritorno).  
🔵 Blu: valutazione autorizzativa tra PEP, PDP, Trust Service e DB.


### 1) External → Internal
**Percorso logico:**

<img width="1473" height="800" alt="image" src="https://github.com/user-attachments/assets/b2e11386-df01-486e-a0c7-f595641995e2" />

**Step:**

1) Ingresso dalla rete esterna

- Il client EXT invia una richiesta verso il servizio pubblicato; il traffico entra in DMZ e passa dal Firewall secondo regole restrittive.
- Colore: rosso.

2) Intercetto al PEP

- La richiesta raggiunge il PEP (Envoy), che è l’unico front‑end verso il servizio interno.
- Colore: rosso.

3) Verifica sessione e autenticazione

- Se non esiste una sessione valida, il PEP avvia il ciclo OIDC reindirizzando l’utente a Keycloak per il login; al termine dell’autenticazione, l’utente ritorna al PEP con prova d’identità.
- Colore: verde (PEP ↔ Keycloak ↔ PEP).

4) Preparazione della decisione

- Con identità e contesto disponibili, il PEP costruisce la richiesta di autorizzazione e la invia al PDP (OPA) per la valutazione.
- Colore: blu (PEP → PDP).

5) Calcolo del trust score

- Il PDP interroga il Trust Service per ottenere il trust score dell’utente; il Trust Service consulta/aggiorna il DB (Postgres) con lo storico degli eventi.
- Colore: blu (PDP ↔ Trust Service ↔ DB).

6) Decisione di policy

- Il PDP applica le regole (identità, ruolo, risorsa richiesta, azione, rete/ambiente, trust score) e restituisce al PEP un verdetto ALLOW o DENY.
- Colore: blu (PDP → PEP).

7) Inoltro o blocco verso il servizio

- Se ALLOW, il PEP inoltra la richiesta all’Internal Web Service e restituisce la risposta al client attraverso lo stesso percorso di ritorno; se DENY, risponde con codice di errore (es. 403).
- Colori: rosso per l’inoltro verso il servizio; risposta sul percorso inverso.

---

### 2) Internal → External
**Percorso logico:**

<img width="1467" height="799" alt="image" src="https://github.com/user-attachments/assets/a1ff7bd3-c993-455e-b373-c8b39a4bc8e4" />



**Step:**

1) Origine della richiesta

- Un host interno (Prod o Dev) avvia una connessione verso una destinazione esterna; il traffico è instradato verso il PEP, eliminando fiducia implicita tra segmenti.

2) Intercetto e preparazione

- Il PEP riceve la richiesta e raccoglie il contesto minimo necessario: identità/ruolo del chiamante, rete/ambiente di provenienza, destinazione e tipo di operazione.
- Colore: inizio Rosso fino al PEP.

3) Decisione di policy

- Il PEP chiede una valutazione al PDP (OPA), fornendo gli attributi della richiesta.
- Colore: Blu (PEP → PDP).

4) Trust score

- Il PDP ottiene dal Trust Service il punteggio di fiducia aggiornato; il Trust Service consulta/aggiorna il DB con lo storico rilevante.
- Colore: Blu (PDP ↔ Trust Service ↔ DB).

5) Verdetto

- Il PDP applica le regole (least‑privilege, categorie di destinazione, orari, contesto) e restituisce ALLOW/DENY al PEP.
- Colore: Blu (PDP → PEP).

6) Uscita controllata

- Se ALLOW, il PEP inoltra la richiesta verso Squid nella DMZ; il firewall consente l’uscita in Internet solo dal proxy. In caso di DENY, il PEP blocca e notifica l’errore al chiamante.
- Colore: Rosso (PEP → Squid → Firewall → EXT).

---

### 3) Internal → Internal
**Percorso logico:**

<img width="1486" height="797" alt="image" src="https://github.com/user-attachments/assets/bf3a66c9-6f7b-4891-ac62-1671c1e9868c" />

> In questo scenario si assume che l’utente, operando da una macchina aziendale, abbia già effettuato l’autenticazione tramite il software preinstallato; di conseguenza, l’accesso al servizio avviene sfruttando la sessione aziendale esistente, senza eseguire nuovamente il login né passare dal flusso interattivo di Keycloak.

**Step**

1) Origine della richiesta

- Un host interno (Prod o Dev) richiede una risorsa esposta dall’Internal Web Service; il traffico è instradato verso il PEP, evitando fiducia implicita tra segmenti.

2) Intercetto al PEP

- Il PEP riceve la richiesta e verifica l’esistenza di una sessione/identità valida (leggere nota sotto l'immagine);
- Ottenuti identità e contesto (ruolo, rete/ambiente di provenienza, endpoint e metodo), il PEP chiede al PDP la valutazione della richiesta.
- Colore: Blu (PEP → PDP).

3) Calcolo del trust score

- Il PDP acquisisce dal Trust Service il punteggio di fiducia aggiornato, con consultazione/aggiornamento del DB per lo storico.
- Colore: Blu (PDP ↔ Trust Service ↔ DB).

5) Applicazione delle policy

- Il PDP applica regole che differenziano ambienti e ruoli.
- Colore: Blu (PDP → PEP).

6) Esito ed inoltro

- Se ALLOW, il PEP inoltra la richiesta all’Internal Web Service e instrada la risposta di ritorno verso l’host sorgente; se DENY, risponde con errore.
- Colore: Rosso (PEP ↔ Internal Web Service ↔ host interno).


---
## Esempio pratico
https://github.com/user-attachments/assets/12df6e4d-154c-47d0-b5bb-280de828da09
## Logging

**Logging / monitoring:** Tutti i passaggi devono essere loggati in modo da poter essere monitorati da `Snort`, `Fluentd` e `Splunk`. 
> Nota: La `management-net` serve unicamente per permettere a Fluentd e Splunk di accedere ai file di log.

> Nota: Snort è configurato solo in modalità IDS. Ha accesso a tutte le reti (`internal_net`, `dmz_net`, `prod_net`, `dev_net`) in modo da poter analizzare il traffico entrante ed uscente.

 
## Trust Score
Il **Trust Score** di un utente (TSu) è un indice dinamico che rappresenta il livello di fiducia corrente, calcolato sulla base degli eventi di sicurezza che lo riguardano. Questo approccio rende il sistema **Zero Trust** più adattivo, premiando comportamenti sicuri e penalizzando quelli sospetti.

$$TS_u = TS_0 + \sum_{i=1}^N I_i \cdot W(t_i)$$

**Significato dei termini:**
- **$TS_0$** : Trust Score iniziale (es. 80)
- **$I_i$** : Impatto dell’evento *i-esimo*  
  *(esempi: -10 per login da IP sconosciuto, +5 per autenticazione MFA riuscita)*
- **$t_i$** : Tempo trascorso dall’evento *i-esimo* fino ad ora (in minuti)
- **$W(t_i)$** : Funzione di decadimento temporale che pesa l’evento in base alla sua "vecchiaia"

---

### Funzione di decadimento temporale $W(t)$

Per dare meno peso agli eventi più vecchi si utilizza una funzione **esponenziale decrescente**:

$$W(t) = e^{-\frac{t}{T}}$$

Gli eventi sospetti o positivi perdono influenza col tempo, riducendo falsi positivi dovuti a vecchie anomalie. Il sistema “perdona” un utente se nel tempo non ripete comportamenti rischiosi.  

- **$t$** : tempo trascorso dall’evento (in minuti)
- **$T$** : costante di scala temporale  
  *(es. T = 1440 equivale a 1 giorno)*

**Comportamento:**
- Eventi recenti → $W(t) \approx 1$ → hanno **maggiore peso**
- Eventi vecchi → $W(t) \to 0$ → hanno **minore influenza**

---

## Eventi che influenzano il Trust Score

*(Sezione da completare — qui verranno elencati e classificati gli eventi che aumentano o diminuiscono il Trust Score, con il loro impatto numerico `Iᵢ`.)*

Esempi preliminari:
- Login da IP sconosciuto → -10
- Autenticazione MFA riuscita → +5
- Tentativo di accesso fallito multiplo → -15
- Accesso da dispositivo registrato → +8

