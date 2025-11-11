# Trust Service

Questo servizio **calcola un punteggio di fiducia dinamico** (Trust Score) per ogni utente, combinando:
1) una **baseline**  
2) gli **eventi recenti** osservati nei log (via Splunk), pesati nel tempo con un decadimento esponenziale.

Il Trust Score risultante (0–100) viene esposto via API REST ed è pensato per essere interrogato da **OPA** (Policy Decision Point) e **Envoy** (Policy Enforcement Point) per prendere decisioni **ALLOW/DENY** in tempo reale.

---

## A cosa serve, in breve
- **Raccoglie eventi utente** (login success/fail, ecc.) indicizzati in Splunk.
- **Applica un mapping “evento → impatto”** (positivo/negativo) definito lato `scoring.py`.
- **Pesa gli impatti** in base alla recenza tramite **decadimento esponenziale**.
- **Somma baseline + impatti pesati** → **Trust Score**.
- **Espone API** per restituire score e dettagli degli ultimi eventi “rilevanti”.

---

## Struttura del progetto

- `app.py` — **API Flask** che espone gli endpoint REST (es. `/score_dynamic/<username>`).  
  - Prepara la query Splunk (SPL) di base e aggiunge un filtro per l’utente.  
  - Itera sui risultati (streaming) ottenuti da `splunk_client.search_export(...)`.  
  - Calcola il **peso temporale** per ciascun evento (usando i parametri di `scoring.py`).  
  - Somma gli impatti pesati alla **baseline per utente** (presi da `scoring.py`).  
  - Rende una risposta JSON con: `score`, `baseline`, `details` (ultimi N eventi utilizzati) e meta (finestra temporale, T).  
  - Espone anche endpoint di **healthcheck** (es. `/healthz`) per readiness/liveness.

- `scoring.py` — **logica di scoring** e costanti di dominio.  
  - Definisce **baseline** (default o per-utent**e**) e il **mapping evento → impatto** (es. `login_failed → -10`, `login_success → +5`).  
  - Imposta i **parametri del decadimento** (es. `T_SCALE_MINUTES`) e l’**intervallo temporale** (es. `EARLIEST/LATEST` per Splunk).  
  - Fornisce le **utility** per: parsing del timestamp (`_to_epoch_seconds`), sanificazione numeri (`_safe_num`), calcolo del fattore di peso `W(t)=exp(-t/T)`.  
  - È il **punto unico** in cui si aggiornano i pesi/impatti senza toccare l’API.

- `splunk_client.py` — **integrazione con Splunk** (solo lettura ricerche).  
  - Gestisce **connessione e autenticazione** verso Splunk **REST Search API**.  
  - Implementa `search_export(SPL)` che **streamma i risultati** (JSON) di una query, così l’API può calcolare lo score “on the fly” senza caricare tutto in memoria.  
  - Isola i dettagli di rete/timeout/verify TLS ed **astrattezza** la dipendenza da Splunk (l’API non deve sapere come si esegue la ricerca).

> Nota: l’ingest dei log in Splunk (es. via **HEC** da Fluentd) è **fuori** da questo servizio. Qui **leggiamo** soltanto.

---

## Trust Score
Il **Trust Score** di un utente (TSu) è un indice dinamico che rappresenta il livello di fiducia corrente, calcolato sulla base degli eventi di sicurezza che lo riguardano. Questo approccio rende il sistema **Zero Trust** più adattivo, premiando comportamenti sicuri e penalizzando quelli sospetti.

$$TS_u = TS_0 + \sum_{i=1}^N I_i \cdot W(t_i)$$

**Significato dei termini:**
- **$TS_0$** : Trust Score iniziale 
- **$I_i$** : Impatto dell’evento *i-esimo*  
- **$t_i$** : Tempo trascorso dall’evento *i-esimo* fino ad ora (in minuti)
- **$W(t_i)$** : Funzione di decadimento temporale che pesa l’evento in base alla sua "vecchiaia".    
Dopo la somma, lo score è **clippato** a `[0, 100]`.


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


## Eventi

Gli eventi pensati sono i seguenti (possibile aggiunta)
- Login_success → +5
- Login_failed  → -4
- Login_off_hour → -2
- Login_failed_strick3  → -30

Parametri tipici (configurabili in `scoring.py`):
- `TS0` (baseline) utente (default es. 70)
- `T_SCALE_MINUTES` (es. 1440 = 1 giorno)
- `EARLIEST`, `LATEST` (finestra temporale Splunk, es. `-24h`/`now` ma idealmente `null`/`now` )
- Mapping impatti

---

## Flusso end-to-end
1. **Fluentd → HEC**: i log applicativi (Keycloak, Envoy, Snort, Squid) arrivano su Splunk con campi normalizzati (`sourcetype`, `event`, `user`, `src_ip`, …).
2. **Trust Service → Splunk**: l’API lancia una ricerca SPL filtrata sull’utente (`user="mrossi"`).
3. **Calcolo**: per ogni evento, calcolo di `minutes_ago`, `W(t)`, somma degli impatti pesati + baseline.
4. **OPA/Envoy** interroga il Trust Service (es. `GET /score_dynamic/mrossi`) per decidere in tempo reale.

---

## Endpoint principali

### `GET /healthz`
- **200 OK** se il processo è vivo (eventualmente include check basilari).

### `GET /score_dynamic/<username>`
- Calcola lo score dinamico per `<username>`.  
- Filtra in Splunk per `(user="<username>" OR preferred_username="<username>")`.  
- Ritorna JSON del tipo:
```json
{
  "user": "mrossi",
  "baseline": 80,
  "score": 74.3,
  "T_scale_minutes": 1440,
  "window": {"earliest": "-24h", "latest": "now"},
  "events_total": 12,
  "events_used": 5,
  "details": [
    {
      "sourcetype": "keycloak:login",
      "event": "login_failed",
      "impact": -10,
      "minutes_ago": 3.5,
      "weight": 0.9976,
      "weighted_impact": -9.98
    }
  ]
}
```
- **Uso tipico in OPA**: la Rego legge `score` e applica soglie/policy (es. deny se `< 60` oppure richiedi MFA).

---

## Variabili d’ambiente
Metti in `.env` o nel `docker-compose.yml` del servizio (valori di esempio):
```
SPLUNK_HOST=splunk
SPLUNK_PORT=8089
SPLUNK_SCHEME=https
SPLUNK_VERIFY_TLS=false
SPLUNK_USER=admin
SPLUNK_PASS=changeme

# Parametri finestra/decadimento se non cablati in scoring.py
T_SCALE_MINUTES=1440
EARLIEST=-24h
LATEST=now
```
> Se usi self-signed cert in Splunk, imposta `SPLUNK_VERIFY_TLS=false` oppure monta il CA.

---

## Esempi veloci
```bash
# Healthcheck
curl -fsS http://trust-service:5000/healthz

# Score dinamico
curl -fsS http://trust-service:5000/score_dynamic/mrossi | jq .
```

---

## Errori comuni & diagnostica
- **Nessun evento in Splunk**: controlla che Fluentd stia inviando su HEC e che i campi chiave (`sourcetype`, `event`, `user`) siano popolati.  
- **Utente non risolto**: la query filtra su `user` e `preferred_username`; verifica che i log Keycloak espongano `username` → `user` (normalizzazione lato Fluentd).  
- **Lag/Search timeout**: aumenta timeout in `splunk_client.py` o restringi `EARLIEST/LATEST`.  
- **Score “strano”**: rivedi mapping impatti / baseline (file `scoring.py`).

---

## Integrazione con OPA/Envoy
1. Envoy effettua ext_authz → OPA.  
2. OPA (Rego) chiama `http.send` verso `http://trust-service:5000/score_dynamic/<user>`.  
3. Valuta `result.score` contro le policy (soglie/condizioni).  
4. Ritorna `allow/deny` e il `livello di accesso`

> La forma dell’endpoint e del JSON è **stabile** per non rompere le Rego.
