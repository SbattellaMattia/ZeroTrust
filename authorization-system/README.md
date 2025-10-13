# Auth System con Envoy + OPA + Trust Service + DB

L’architettura proposta si divide in  **PEP/PDP** (Policy Enforcement Point / Policy Decision Point) basata su **Envoy**, **OPA**, un **Trust Service** custom e un database **Postgres**.

---

## Architettura
<img width="993" height="165" alt="image" src="https://github.com/user-attachments/assets/07f2cd36-be9c-4e8f-9252-3ec979ce6a35" />


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
3. Il filtro comunica in **gRPC** con OPA. **gRPC** (Google Remote Procedure Call) è un protocollo basato su HTTP/2 che consente lo scambio efficiente di messaggi strutturati tra servizi (in questo caso Envoy ↔ OPA).
4. OPA analizza la richiesta e applica le policy Rego chiamando il **Trust Service**, che comunica con **Postgres** per il calcolo della fiducia.  
5. Envoy risponde con **allow=true** (inoltra la richiesta al servizio interno), altrimenti con **deny** (restituisce `403 Forbidden`).


---

## Esempio pratico
Nell'init.sql del database abbiamo predisposto due semplici utenti:
- `mrossi` con **score = 80**
- `mrhacker` con **score = 10**

Per prima cosa startiamo i container con:
```bash
docker compose up --build
```
Procediamo poi con i test, la sintassi simula una richiesta http, con la seguente sintassi:
```bash
curl -v localhost:10000/users/profile/{nome}
```
Testando con l’utente `mrossi`, il **Trust Service** restituisce uno score pari a **80**.  
Poiché `80 >= 50`, OPA risponde con `allow=true` → Envoy inoltra la richiesta al servizio interno, che risponde:
```bash
hello from internal
```
<img width="1775" height="800" alt="Immagine 2025-09-17 161305" src="https://github.com/user-attachments/assets/7bd67f37-7d88-4bf7-8a98-806c1a2f91f4" />


---

Al contrario, per l’utente `mrhacker`, il **Trust Service** restituisce uno score pari a **10**.  
Poiché `10 < 50`, OPA risponde con `allow=false` → Envoy blocca la richiesta e restituisce un:
```bash
 403 Forbidden
```
<img width="1843" height="814" alt="Immagine 2025-09-17 160939" src="https://github.com/user-attachments/assets/342ea026-92fd-48ef-9e53-4504255ce7d1" />


---

> **Nota**: La policy mostrata è puramente a scopo di test e dimostrativo.  
> Le policy sviluppate in seguito sono molto più articolate e basate su calcoli e metriche avanzate.

## Accorgimenti  
  ⚠️ **Attenzione**: l’interpolazione delle variabili d'ambiente `${SERVICE_NAME}` e  `${SERVICE_PORT}` in `envoy.yaml` non sempre funziona. Nonostante ciò, essendo passate correttamente nel compose, non da alcun tipo di errore, ma scaturisce in una mancata comunicazione tra pep e pdp. È consigliato utilizzare direttamente il nome del container come host (es. `internal-service:8080`).
  
## Fonti e riferimenti

Questa configurazione è stata realizzata prendendo spunto da:

- [Envoy Getting Started Guide](https://github.com/helpfulBadger/envoy_getting_started)  
- [Open Policy Agent Documentation](https://www.openpolicyagent.org/)  
- [Envoy Proxy Official Docs](https://www.envoyproxy.io/docs/envoy/latest/)  



