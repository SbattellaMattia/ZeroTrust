# ZeroTrust

## Introduzione
Questo progetto universitario per il corso di laurea in Ing. Informatica ed Automazione Univpm (corso di Advanced Cyber Security for IT) è una simulazione di un'infrastruttura **Zero Trust** containerizzata con Docker. L'obiettivo è mostrare un'architettura semplice ma realistica che include: firewall (nftables), bastion host, keycloak (Identity Provider), PEP (Envoy), PDP (OPA), Trust Service per calcolo dinamico della fiducia, Squid (forward proxy), servizi interni (un web service, produzione, sviluppo), oltre a strumenti di monitoring/IDS (Snort) e raccolta log (Splunk).

<img width="1251" height="871" alt="image" src="https://github.com/user-attachments/assets/f899444d-41da-423d-8ab8-d2cafc2f4e7e" />



---

## Tabella componenti

| Componente                |Immagine| Funzionamento (ruolo)| Reti* | Note pratiche   |
| ------------------------- | ---|-------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------: | ------------------------------------------------------------------------------- |
|`Ext`                |-| Container esterno per la simulazione di Internet.  |`external_net` |Internamente è raggiungibile solo attraverso il Firewall. | 
|`Firewall`           |<img width="224" height="224" alt="4D5D7B84-C363-4368-A115-E3EB76503672" src="https://github.com/user-attachments/assets/f2df7df2-249a-4e1b-99e6-8e394b6b9db1" />| Firewall nftables; applica regole di filtraggio e limitazioni di percorso . |      `external_net`, `dmz_net`| Successore di iptables. Funge da unico punto di accesso e uscita dalla rete aziendale |
|`Bastion Host`       || Punto d'ingresso sicuro per amministrazione. |`dmz_net` | - |
|`Squid`              |<img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/e79ab872-24ab-4ce6-a433-3da3c19b23b1" />|Forward proxy per traffico in uscita.         |`dmz_net` | Unico container predisposto dal `Firewall` al traffico in uscita dalla rete.|
|`PEP` (Envoy)        |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/1380c555-96b0-4597-b6c2-97fdd8fd9239" />| Policy Enforcement Point: intercetta tutte le richieste, chiede decisione al PDP e applica le policy.  |  `internal_net`, `dmz_net`, `prod_net`, `dev_net` | Se non si è autenticati effettua il redirect verso `Keycloak` |
|`Keycloak`           |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/c70e1a39-b3da-4dc6-a00e-f83a95992356" />| Identity Provider (OIDC/OAuth2).  | `dmz_net` | Autentica e rilascia un token di accesso contenente le informazionli necessarie al pdp per prendere decisioni di autorizzazione |
|`PDP` (OPA)          |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/6ea139b3-e462-4ff4-bccf-2249f126b764" />| Policy Decision Point: valuta le policy basate su input (identità, risorsa, azione, trust score) e risponde ALLOW/DENY.    |  `internal_net` | Interroga il Trust Service per ottenere il trust score dinamico.                |
|`Trust Service`      |-| Calcola e ritorna il trust score dinamico.|`internal_net` | Fornisce input numerico/qualitativo al PDP basato sulla storia dell'utente registrata nel DB postgres. Aggiunto per separare le operazioni di calcolo e interazione con il db dal resto.|
|`Database`	          |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/997817dc-609c-418b-a3a9-2ea3696a866e" />| Contiene gli utenti con i relativi punteggi. Interrogati dal Trust Service.| `internal_net`| Immagine di Postgres.|
|`Internal Web Service`|-| Servizio esposto in DMZ.   |`dmz_net`   |Non direttamente esposto a Internet: accesso tramite keycloak+PEP.|
|`Prod-host`          |-| Host simulato in rete produzione.          |`prod_net`|- |
|`Dev-host`           |-| Host simulato in rete sviluppo.            |`dev_net` |-|
|`Snort`              |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/452991a6-1408-4db8-a75b-9a6304819c5e" />| IDS (o IDS/IPS se configurato): monitora il traffico su interfacce di rete multiple.|`dmz_net`, `internal_net`, `prod_net`, `dev_net` | Usato in modalità IDS (non IPS) per evitare blocchi accidentali e mantenere la rete semplice.|
|`Splunk`             |<img width="224" height="224" alt="image" src="https://github.com/user-attachments/assets/471aefb3-fe12-4151-8b74-4d87aa7f55e7" />| SIEM / collector di log centralizzato   | `management_net` | I container inviano i log su `management_net`; Splunk analizza e visualizza eventi.|
|`Fluentd`            |<img width="100" height="100" alt="image" src="https://github.com/user-attachments/assets/0804836e-e0d5-48b9-8935-fb40ef0fb05f" />| Raccoglitore dei logs   | `management_net` | Aggregazione e forwarding dei log verso Splunk.|

    
>Nelle reti è stata omessa quella di management, presente ovunque a meno del container `Ext`.
---

## Reti Docker

* `external_net` — simula Internet (client esterni).
* `dmz_net` — DMZ / network di perimeter.
* `internal_net` — rete dei servizi di controllo.
* `prod_net` — rete produzione (host produzione).
* `dev_net` — rete sviluppo (host sviluppo).
* `management_net` — rete per la raccolta log / management (Splunk).

> Nota: La gestione delle reti è interamente demandata a Docker, che, una volta definite, configurate e associate ai rispettivi container, provvederà a crearle e a gestire le comunicazioni tra di essi.

---

## Possibili scenari

### 1) ESTERNO → INTERNO
**Percorso logico:**

<img width="1410" height="672" alt="image" src="https://github.com/user-attachments/assets/659c049e-4a27-4aaf-a8ce-0e3ca6f904be" />


**Step:**

1. Il client apre connessione verso l'indirizzo pubblico; il pacchetto arriva al container `Firewall`.
2. `Firewall` applica le regole espresse come ad esempio: *consenti solo connessioni verso l'IP\:porta del `Bastion Host`*.
3. `Bastion Host` richiede autenticazione. Se l'autenticazione fallisce -> drop/401; se ok -> normalizzazione e inserimento di header di identità (es. JWT o `X-Forwarded-User`).
4. `Bastion Host` inoltra la richiesta al `PEP` (Envoy). Envoy estrae attributi della richiesta (utente, risorsa, azione, indirizzo sorgente).
5. Envoy chiama `PDP` (OPA) che delega il calcolo del `trust score` al `Trust Service`. Questo comunica con il `DB Postgres` per ricevere lo storico delle azioni e aggiornarlo con i nuovi punteggi.
6. OPA valuta la policy e restituisce ALLOW/DENY.
7. Se ALLOW, Envoy inoltra la richiesta al `webservice` in DMZ; se DENY, Envoy risponde con 403.
8. La risposta del `Web Service` risale il percorso inverso: `Web Service → Envoy → Bastion Host → Firewall → client esterno`.

---

### 2) INTERNO → ESTERNO
**Percorso logico:**

<img width="1399" height="655" alt="image" src="https://github.com/user-attachments/assets/720fbdc1-c7da-4c91-b399-77de89b99d87" />


**Step:**

1. L'host interno innesca la richiesta (es. chiamata HTTPS verso un'API esterna). La rete forza l'host a passare per `PEP`.
2. `PEP` (Envoy) intercetta la richiesta e invia un input al `PDP` (OPA) con `user/service`, `destinazione`, `azione`, `source_network`, `device_info`.
3. `PDP` chiede il `trust score` al `Trust Service` e valuta le policy come ad esempio delle restrizioni di orario.
4. Se `DENY` → Envoy blocca e ritorna errore al client interno. Se `ALLOW` → Envoy inoltra la richiesta a `Squid`.
5. `Squid` apre la connessione verso Internet. `Firewall` è configurato per permettere l'uscita verso Internet **solo** dall'IP di `Squid`.
6. La risposta ritorna: Internet → Firewall → squid → Envoy (opzionale) → host interno.


---

### 3) INTERNO → INTERNO
**Percorso logico:**

<img width="1418" height="663" alt="image" src="https://github.com/user-attachments/assets/fed94779-9e6d-4591-a8fb-40e9b57aa9f7" />


**Step dettagliati:**

1. Un `host` effettua la chiamata verso una risorsa interna; le regole di rete obbligano il traffico a passare per `PEP`.
2. Envoy intercetta la richiesta e invia a OPA gli attributi rilevanti.
3. OPA verifica il `trust score` dal `Trust Service` e valuta le policy: es. `ops-host` può eseguire POST se trust >= 0.8; `dev-host` solo GET e su endpoint limitati.
4. Ancora una volta se ALLOW, Envoy inoltra al `webservice`. Se DENY → 403.


---

## Logging

**Logging / monitoring:** Tutti i passaggi devono essere loggati in modo da poter essere monitorati da `Snort` e `Splunk`. 
> Nota: La `management-net` serve unicamente per permettere a Splunk di accedere ai file di log.

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

