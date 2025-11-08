# PDP-OPA — Policy Decision Point

## Descrizione generale e Regole

Il **PDP (Policy Decision Point)**, basato su **Open Policy Agent (OPA)**, è il componente che prende le decisioni di accesso all’interno dell’architettura **Zero Trust**.  
Riceve le richieste dal **PEP (Envoy Proxy)** e valuta in tempo reale se autorizzare o negare l’accesso a una risorsa, applicando un insieme di politiche definite centralmente.  

Le decisioni del PDP si basano su quattro categorie principali di **regole**:

1. **Identità e Ruoli**  
   Determinano chi è l’utente e quale ruolo ricopre nel sistema, come definito da **Keycloak**.

2. **Punteggio di Fiducia**  
   Si basa sul punteggio calcolato dal **Trust Service**, che varia in funzione degli eventi generati dal suo comportamento.

3. **Contesto di Rete**  
   Tiene conto della provenienza della richiesta (es. internal_net, prod_net, dev_net, external_net) per applicare pesi differenti.

4. **Politiche di Accesso**  
   Stabilisce le soglie di punteggio e i livelli di accesso (ad esempio *full*, *limited* o *denied*) in base ai parametri complessivi.



In questo modo, il PDP combina **identità**, **comportamento** e **contesto operativo** per garantire che ogni accesso sia verificato e giustificato, secondo i principi del modello **Zero Trust**.

## Funzionamento preliminare

1. **Ricezione richiesta**  
   Envoy invia a OPA un input JSON che include:
   - IP sorgente:
      - utilizzato per aggironare il punteggio in funzione della rete sorgente,
   - IP destinazione, 
   - header HTTP (incluso `Authorization: Bearer <token>`),  
   - path e metodo della richiesta.

2. **Decodifica token JWT**  
   OPA estrae dal token:
   - `preferred_username`
      - l'username dell'utente che ha eseguito il login in Keycloack,  
   - `realm_access.roles`
      - il ruolo assegnato all'utente che ha eseguito il login in Keycloak.  

3. **Chiamata al Trust Service**  
   OPA interroga `http://trust-service:5000/score_dynamic/<username>`  
   per ottenere il **punteggio di fiducia**, influenzato da alcune tipologie di eventi come:
   - login fuori orario (`login_off_hours`),  
   - 3 login falliti consecutivamente (`login_fail`),  
   - login eseguito con successo (`login_success`).

## **Calcolo del punteggio finale**

Il calcolo eseguito dal **PDP-OPA** è descritto dalla seguente **Formula**:  
       
              `final_score = ( auth.score + role_adjust ) × net_adjust`

Ogni parametro rappresenta un contributo distinto alla valutazione complessiva dell’utente:

- **auth.score** → rappresenta il punteggio di fiducia fornito dal **Trust Service**.  
  Questo valore è dinamico e varia in base agli **eventi registrati** per l’utente, come:
  - login riusciti,
  - tentativi di accesso falliti,
  - autenticazioni effettuate fuori orario lavorativo.

- **role_adjust** → indica il bonus o malus applicato in funzione del **ruolo** associato all’utente.  
  I ruoli vengono letti direttamente dal token JWT rilasciato da **Keycloak**.  
  Ogni ruolo contribuisce a modificare il punteggio base come segue:

  | Ruolo  | Effetto sul punteggio | Valore |
  |:--------|:-----------------------|:--------:|
  | `admin` | Incremento massimo     | +10 |
  | `prod`  | Incremento medio       | +5 |
  | `dev`   | Incremento medio       | +5 |
  | `guest` | Penalità               | -5 |

 - **net_adjust** → è il **fattore moltiplicativo** che tiene conto della **rete di provenienza** della richiesta. Il **PDP** individua automaticamente la rete di origine analizzando l’**indirizzo IP sorgente (source IP)** della richiesta.  
  In questo modo vengono valorizzati gli accessi provenienti da reti affidabili e penalizzati quelli provenienti da reti esterne.  

  L’applicazione dei pesi avviene come segue:

  | Rete di provenienza | Descrizione | Moltiplicatore |
  |:--------------------|:-------------|:---------------:|
  | `internal_net` | Rete interna aziendale | ×1.2 |
  | `prod_net` | Rete di produzione | ×1.2 |
  | `dev_net` | Rete di sviluppo | ×1.2 |
  | `external_net` | Rete esterna (meno affidabile) | ×0.9 |

Il risultato finale (**final_score**) rappresenta quindi una **valutazione complessiva di fiducia** dell’utente. 

## **Determinazione del livello di accesso e gestione del rifiuto**

Una volta calcolato il **final_score**, il **PDP-OPA** confronta il valore ottenuto con soglie predefinite per determinare il livello di accesso concesso all’utente.  
Questa fase rappresenta il momento decisionale finale, in cui il sistema valuta se un utente può accedere completamente, parzialmente o essere bloccato.

### Livelli di accesso

| Livello di accesso | Condizione | Descrizione |
|:-------------------|:------------|:-------------|
| **Full Access** | `final_score ≥ 70` | L’utente dispone di accesso completo alle risorse richieste. Il suo livello di fiducia è considerato elevato (*full*). |
| **Limited Access** | `50 ≤ final_score < 70` | L’utente ottiene un accesso limitato o con restrizioni, a causa di un livello di fiducia intermedio. |
| **Denied Access** | `final_score < 50` | L’utente non è autorizzato all’accesso. Il suo punteggio di fiducia è inferiore alla soglia minima di sicurezza. |

Grazie a questa logica, il **PDP** è in grado di **applicare decisioni dinamiche e contestuali**.

---

### Gestione dell'accesso negato (HTTP 403)

Se il **final_score** non raggiunge la soglia minima di **50**, il **PDP-OPA** nega la richiesta restituendo una risposta con **HTTP status 403 — Forbidden**.  
In questo caso, il messaggio inviato al **PEP (Envoy Proxy)** ha la seguente forma:

```json
{
  "allowed": false,
  "http_status": 403,
  "body": "{\"message\":\"Too low score\"}"
}

```
