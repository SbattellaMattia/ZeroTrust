# Auth System con Envoy + OPA + Trust Service + DB

L’architettura proposta si divide in  **PEP/PDP** (Policy Enforcement Point / Policy Decision Point) basata su **Envoy**, **OPA**, un **Trust Service** custom e un database **Postgres**.

---

## Architettura

- **Envoy Proxy (PEP)**  
  Punto di ingresso per tutte le richieste. Intercetta le chiamate e delega la decisione di autorizzazione a OPA tramite il filtro `ext_authz`.

- **OPA (PDP)**  
  Policy Decision Point scritto in **Rego**. Decide se permettere o negare la richiesta in base allo *score* dell’utente ottenuto dal Trust Service.

- **Trust Service**  
  Servizio Python/Flask che espone un endpoint REST per restituire lo *score* di un utente (salvato nel DB).

- **Postgres (DB)**  
  Database che contiene gli utenti e i loro trust score. L’init SQL viene montato al container per ricreare le tabelle all’avvio.

---

## Flusso di comunicazione

1. La richiesta HTTP arriva ad **Envoy**, momentaneamente non ci interessa sapere da dove proviene, l'importante è realizzare il flusso di comunicazione.
2. Envoy intercetta la richiesta e attiva il filtro **ext_authz**.
3. Il filtro comunica in **gRPC** con OPA.  
   - **gRPC** (Google Remote Procedure Call) è un protocollo basato su HTTP/2 che consente lo scambio efficiente di messaggi strutturati tra servizi (in questo caso Envoy ↔ OPA).
4. OPA analizza la richiesta e applica le policy Rego chiamando il **Trust Service**, che comunica con **Postgres** per il calcolo della fiducia.  
5. Envoy risponde con **allow=true** (inoltra la richiesta al servizio interno), altrimenti con **deny** (restituisce `403 Forbidden`).


---
##Esempio pratico
Nell'init.sql del database abbiamo predisposto due semplici utenti:
- `mrossi` con **score = 80**
- `mrhacker` con **score = 10**

Lanciando i container e testando per i due utenti 
```bash
docker compose up --build

curl -v localhost:10000/users/profile/{nome} bash
```

Testando con l'utente `mrossi` possiamo notare che ricevendo un TrustScore di 80 l'utente venga fatto passare
Poiché 80 >= 50, OPA risponde con allow=true → Envoy inoltra la richiesta a internal-service, che risponde:
hello from internal

Al contrario mrhacker che ha come punteggio 10 viene bloccato e envoy risponde con 403

> Nota: La policy proposta è unicamente a scopo di test e dimostrativo. Quelle sviluppate in seguito sono differenti e basate su calcoli e metriche più avanzate.



