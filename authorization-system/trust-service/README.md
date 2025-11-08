# Trust Service

Questo servizio **calcola un punteggio di fiducia dinamico** (Trust Score) per ogni utente, combinando:
1) una **baseline** (es. 80) e  
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

## Formula (riassunto)
Per ogni evento *i* con impatto `I_i` e “età” `t_i` (in minuti) si usa un peso
```
W(t_i) = exp(- t_i / T)
```
Il punteggio è:
```
TS(u) = TS0(u) + Σ [ I_i · W(t_i) ]
```
Dopo la somma, lo score è **clippato** a `[0, 100]`.

Parametri tipici (configurabili in `scoring.py`):
- `TS0` (baseline) utente (default es. 80)
- `T_SCALE_MINUTES` (es. 1440 = 1 giorno)
- `EARLIEST`, `LATEST` (finestra temporale Splunk, es. `-24h`/`now`)
- Mapping impatti (es. `login_failed=-10`, `login_success=+5`)

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

## Variabili d’ambiente (tipiche)
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

## Come estendere
- **Nuovi eventi**: aggiungi `event → impact` in `scoring.py`.  
- **Baselines per-ruolo/utente**: implementa lookup in `get_baseline_for(user)` (DB o mapping).  
- **Più fonti**: basta che i log arrivino in Splunk con campi `sourcetype`, `event`, `user`, `_time`.

---

## Integrazione con OPA/Envoy (a grandi linee)
1. Envoy effettua ext_authz → OPA.  
2. OPA (Rego) chiama `http.send` verso `http://trust-service:5000/score_dynamic/<user>`.  
3. Valuta `result.score` contro le policy (soglie/condizioni).  
4. Ritorna `allow/deny`, eventuali **obblighi** (es. “richiedi MFA”).

> La forma dell’endpoint e del JSON è **stabile** per non rompere le Rego.

---

## Requisiti
- Python 3.10+  
- Dipendenze in `requirements.txt` (Flask, requests, ecc.)  
- Accesso di rete a Splunk (porta management 8089 o quella configurata).

---

## Licenza
Uso accademico/didattico. Aggiungi la tua licenza se necessario.
