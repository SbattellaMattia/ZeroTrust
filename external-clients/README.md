# External Clients

Questa sezione include i **client esterni** utilizzati per testare il comportamento dell’architettura **Zero Trust** durante le connessioni provenienti da reti non fidate.
<img width="1304" height="654" alt="image" src="https://github.com/user-attachments/assets/2da15f21-a1a6-4d36-a036-b72259653d69" />


---

## Componenti principali

### Allowed Host (client esterno principale)
È un browser containerizzato che rappresenta l’**utente esterno** che tenta di accedere ai servizi interni.  
Tutto il traffico del browser è instradato attraverso il **PEP Envoy** grazie a una configurazione proxy manuale:

- Le richieste HTTP/HTTPS vengono inviate a **pep-envoy:10000**
- Envoy reindirizza automaticamente verso la connessione sicura HTTPS
- Da qui parte il flusso di autenticazione e autorizzazione con **Keycloak** e **OPA**

In pratica, il browser simula l’accesso di un utente esterno che deve autenticarsi e superare i controlli del modello **Zero Trust** prima di poter raggiungere **l'internal service**.

---

### Blocked Host
È un secondo client configurato nella stessa rete esterna (`external_net`), ma con un **indirizzo IP specificamente bloccato** da Envoy nelle regole RBAC.

- IP assegnato: `10.20.0.60`  
- È incluso nella **blacklist** del PEP Envoy  
- Tutte le sue richieste vengono immediatamente **rifiutate (403 Forbidden)**, indipendentemente dalle credenziali o dal token.

Questo client serve a **verificare il corretto funzionamento del firewall L3/L4** di Envoy, dimostrando che gli accessi vengono bloccati già al livello di rete, prima ancora dell’autenticazione.

---

## Scopo didattico

Questi due client permettono di visualizzare chiaramente la differenza tra:

| Client | Stato di accesso | Descrizione |
|--------|------------------|-------------|
| **Allowed Host** | Consentito | Passa attraverso autenticazione Keycloack e PDP |
| **Blocked Host** | Negato | IP bloccato dal firewall di Envoy |

Contenuto mostrato per il **blocked host**:   

<img width="235" height="59" alt="blocked_server" src="https://github.com/user-attachments/assets/e3edc232-9843-46b3-92f6-56fd1a04e079" />
