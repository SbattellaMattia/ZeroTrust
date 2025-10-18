# Host interni

<img width="712" height="491" alt="Immagine 2025-09-19 023041" src="https://github.com/user-attachments/assets/e53f35e1-4ed0-4bb4-ac4f-d3848a375ce8" />

Nella simulazione dell’azienda sono stati considerati due host a **modello didattico**, rappresentanti rispettivamente un PC del reparto **sviluppo** e uno del reparto **produzione**. Ogni host appartiene a una rete separata, denominata `dev_net`: e `prod_net`, per simulare la segmentazione tipica delle reti aziendali.

Essendo un modello didattico, si è semplificato il processo di autenticazione: si assume che ogni PC sia già associato a un **utente autenticato**, e che contenga tutte le informazioni rilevanti (identità, ruolo, rete, device, ecc.) necessarie al **PDP** per applicare le proprie policy di sicurezza. In altre parole, il computer stesso funge da “proxy” dell’utente, senza dover simulare il software di login reale.

Seguendo i principi della **security policy Zero Trust**, ogni richiesta (anche se proviene dall’interno della rete aziendale) deve essere considerata potenzialmente non sicura e quindi **verificata dal PEP (Policy Enforcement Point)**. Per questo motivo, i due host devono comunicare **esclusivamente con il PEP Envoy**, che applica le regole di controllo, legge i metadati forniti dagli host e decide se consentire o bloccare la richiesta.

## Struttura del progetto

- **headers.map**: contiene la lista dei parametri/variabili da aggiungere alle richieste (es. utente, rete, ruolo, device). Permette di **aggiungere o rimuovere parametri facilmente**, senza modificare lo script del wrapper.  
- **curl-wrapper.sh**: legge le variabili dal file e le trasforma in header HTTP inviati a ogni richiesta.  
- **entrypoint.sh**: inizializza le variabili proxy e avvia il container.  

---

## Funzionamento

1. Gli host (`host_sviluppo` e `host_produzione`) inviano tutte le richieste HTTP/HTTPS **attraverso il PEP**.  
   - Questo è simulato usando le variabili d’ambiente `HTTP_PROXY` e `HTTPS_PROXY`.  
   - In una rete reale, il filtraggio sarebbe fatto da un **router o firewall aziendale**; qui, per semplicità, il proxy è nel container.

2. Le richieste includono automaticamente header importanti, come:  
   - `X-User-Id`, `X-Network`, `X-Role`, `X-Device-Id`  
   - Il PEP può leggere questi header e passarli al PDP per prendere decisioni di autorizzazione.

3. Il file **headers.map** rende il sistema **modulare**: basta aggiungere nuove righe per aggiungere parametri alle richieste.

---

## Test rapido

<img width="648" height="467" alt="image" src="https://github.com/user-attachments/assets/90d2ad77-76fd-4972-bbb6-7b1c216bc7cc" />


- Avvio dei container: `docker-compose up --build -d`  
- Accesso al container sviluppo: `docker exec -it host_sviluppo bash`  
- Esecuzione di una richiesta verso il servizio interno: `curl -v http://localhost:8080`   
- Il wrapper aggiunge automaticamente tutti gli header definiti in **headers.map**, e anche se non interroghiamo il pep e non il servizio, ci risponde `envoy`. 

> Nota: Come possiamo notare, pur interrogando il servizio interno, ci risponde envoy (negandoci momentaneamente l'accesso a causa della configurazione momentanea dei punteggi nel db)
---

## Note di progetto
- **Scopo didattico**: l’architettura serve a simulare scenari di sicurezza e policy enforcement in un contesto controllato, senza riprodurre la complessità del software reale di autenticazione e filtraggio.  
- **Proxy nel container**: in una rete aziendale reale, le regole sarebbero applicate a livello di **router o firewall**, non direttamente nei PC. Nella simulazione, il proxy è dentro il container per semplicità. 
- **Passare dati sensibili tramite gli header HTTP non è sicuro**: in una rete reale potrebbero essere facilmente falsificati o intercettati.  

