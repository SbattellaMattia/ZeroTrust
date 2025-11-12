# External Services

Questa sezione del progetto contiene i **servizi esterni** utilizzati per testare il comportamento dell’architettura **Zero Trust** durante il traffico **interno → esterno**.

---

## Obiettivo

Simulare lo scenario tipico interno -> esterno ossia **accesso da reti interne (dev, prod) verso risorse esterne**

Questo flusso passa obbligatoriamente attraverso il **PEP Envoy**, che agisce come un **proxy intelligente**, simile a **Squid**, attraverso l'utilizzo di un **filtro Lua personalizzato**, che intercetta le richieste HTTP e si occupa di:

- Estrae il nome del server richiesto (es. `allowed-server` o `blocked-server`)  
- Reindirizza la richiesta verso **pep-envoy:10004**, aggiungendo un parametro come:  
 `https://pep-envoy:10004/?_dest=blocked-server`  
- Envoy legge `_dest`, lo salva come `x-target-host` e controlla se è permesso dalle regole


---

## Servizi Esterni

### Allowed Server
Un piccolo web server accessibile dagli utenti interni autenticati.  
Rappresenta una **destinazione esterna autorizzata**: le richieste verso questo server vengono permesse dopo il passaggio attraverso la pipeline Zero Trust.

Contenuto mostrato:
<img width="1468" height="550" alt="allowed_server" src="https://github.com/user-attachments/assets/6a82830a-2abe-4230-b842-2e514536556d" />



---

### Blocked Server
Server di test utilizzato per verificare il corretto funzionamento del **firewall applicativo (L7)** configurato su Envoy.  
Le richieste verso questa destinazione vengono **bloccate** dal PEP. 

Contenuto mostrato:

<img width="1600" height="568" alt="image" src="https://github.com/user-attachments/assets/eb1dd5fe-1ef1-4204-a732-cb2684718077" /> 

> Nota: il pep blocca la richiesta, gli host intrni non possono vedere in alcun modo questo server poichè i due container sono su reti diverse e comunicano solo ed esclusivamente tramite `pep-envoy`.

---
