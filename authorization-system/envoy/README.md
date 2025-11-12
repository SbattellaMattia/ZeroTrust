# <img width="200" height="235" alt="image" src="https://github.com/user-attachments/assets/d4fc9db9-29ab-40c0-810e-9bd20a91d2d8" />

Nel nostro progetto, il PEP Envoy è il cuore dell’architettura: concentra autenticazione, autorizzazione, osservabilità e policy enforcement su ogni richiesta in ingresso ed in uscita, integrando i container IdP, PDP e controlli di rete a più livelli. Questo approccio massimizza la visibilità e la consistenza delle decisioni di accesso in linea con il modello zero trust, ma richiede particolare attenzione a disponibilità, scalabilità e resilienza per evitare che il PEP diventi un single point of failure o un limite prestazionale. Infatti, se da un lato il PEP agisce come enforcement point centralizzato e bastion host, facendo da unico punto di controllo attraverso cui passa ogni richiesta, dall'altro introduce anche un potenziale collo di bottiglia architetturale da mitigare con ridondanza e scaling orizzontale.

Scelta architetturale
Dopo un’analisi approfondita, la decisione progettuale è stata di collocare Envoy come controllo perimetrale e di accettare i difetti di questa configurazione. In favore della scelta troviamo linee guida direttamente dal [NIST](https://pages.nist.gov/zero-trust-architecture/VolumeB/ZeroTrustTakeaways.html).

> “Once an organization has inventories of the resources it needs to protect and the security capabilities it already has, the organization is ready to begin planning its access protection topology, in terms of whether and where its infrastructure will be segmented and at what level of granularity each resource will be protected. The access topology should be designed using a risk-based approach, isolating critical resources in their own trust zones protected by a PEP but permitting multiple lower-value resources to share a trust zone. In designing its access protection topology, the organization will identify which PEP is responsible for protecting each resource as well as what supporting technologies will be involved in providing input to resource access decisions. Initially, the organization’s network may not be well segmented. In fact, before zero trust is implemented, when the organization is still relying on perimeter-based protections, such a topology can be thought of as the organization protecting all of its resources behind a single PEP, i.e., the perimeter firewall. As the organization implements ZTA, it should segment its infrastructure into smaller parts. Such segmentation will enable it to limit the potential impact of a breach or attack and make it easier to monitor network traffic. In designing its access protection topology, the organization should apply access control enforcement at multiple levels: application, host, and network.”

Nel progetto, Envoy ha sostituito sia nftables sia Squid perché copre nativamente le funzioni che servivano: come reverse/forward proxy con routing avanzato, TLS termination, HTTP/1.1–HTTP/2, supporto CONNECT, dynamic forward proxy e policy di autorizzazione a livello L7, oltre a filtri per autenticazione e integrazione con IdP/PDP. Introdurre nftables per DNAT/TProxy e Squid per il forward proxy avrebbe solo aumentato la complessità operativa, duplicato punti di policy e reso il troubleshooting più difficile, senza benefici sostanziali rispetto a un PEP unico basato su Envoy.

---

## 1. Funzionamento

- **Ingress**: proteggere l’accesso a `internal-service` con **TLS**, **autenticazione OIDC (Keycloak)** e **autorizzazione tramite OPA (ExtAuthz)**.  
- **Egress**: fornire un **forward proxy controllato** con verifica domini a **livello 7** (RBAC su `x-target-host`) dietro autenticazione.

---

## 2. Porte e ruoli

### 2.1 Envoy (downstream)

| Porta | TLS | Ruolo | Descrizione sintetica |
|---:|:--:|---|---|
| **10000** | No | Redirect | Forza HTTP → HTTPS (redirect a 10001). |
| **10001** | Sì | Ingress | RBAC IP → OAuth2 (Keycloak) → ExtAuthz (OPA) → inoltro a `internal-service`. |
| **10003** | No | Proxy (ingresso egress) **+ Redirect** | Intercetta richieste proxy e **redirige** a 10004 aggiungendo `?_dest=host:port` (Lua). |
| **10004** | Sì | Egress | Lua → OAuth2 → RBAC L7 (su `x-target-host`) → routing per dominio. |
| **10002** | No | Admin | Endpoint di management (config/stats/ready/clusters) **solo per rete interna**. |

### 2.2 Servizi upstream collegati

| Servizio | Porta | Utilizzo |
|---|---:|---|
| **Keycloak** | **8443** | Authorization/Token endpoint per OAuth2/OIDC (ingress/egress) e route `/oauth2/*` su egress. |
| **OPA (pdp-opa)** | **9191** | Decisioni di autorizzazione per ExtAuthz (gRPC*). |
| **internal-service** | **8080** | Backend applicativo protetto (target dell’ingress). |
| **allowed-server** | **80** | Destinazione egress consentita (esempio). |
| **blocked-server** | **80** | Destinazione egress vietata (esempio/test). |

> gRPC è un framework open source di Google per Remote Procedure Call: un programma invoca funzioni su un servizio remoto come fossero locali, con trasparenza dei dettagli di rete. Usa HTTP/2 e messaggi binari Protocol Buffers definiti in file .proto, da cui si genera automaticamente il codice client e server in più linguaggi per chiamate tipizzate e veloci. È pensato per microservizi e comunicazioni interne a bassa latenza, dove efficienza e streaming bidirezionale contano più della compatibilità umana di JSON.

---

## 3. Prerequisiti

1. **Certificati TLS (downstream)** per 10001 e 10004:
   - `/etc/envoy/certs/server.crt`
   - `/etc/envoy/certs/server.key`
2. **Segreti OAuth2**:
   - `/etc/envoy/oauth-token-secret.yaml` (client secret Keycloak)
   - `/etc/envoy/oauth-hmac-secret.yaml` (HMAC per firma cookie sessione Envoy)
3. **Keycloak**:
   - Realm: `zerotrust`
   - Client: `envoy-proxy` con redirect URI:
     - `https://pep-envoy:10001/oauth2/callback`
     - `https://pep-envoy:10004/oauth2/callback`
4. **OPA** raggiungibile su `pdp-opa:9191` con policy valida.
5. **DNS Docker** correttamente funzionante (risoluzione dei nomi dei cluster).

> **Nota produzione**: configurare la validazione CA nel cluster `keycloak` (SNI e `validation_context`).

---

## 4. Flussi

### 4.1 Ingress (10000 → 10001 → internal-service)

1. L’accesso in chiaro su **10000** viene reindirizzato (301) a **10001** in HTTPS.  
2. Su **10001** vengono applicati in sequenza:
   - **RBAC L3/L4**: blocco IP in blacklist (fail-fast).  
   - **OAuth2/OIDC** (Keycloak 8443): se assente sessione valida, redirect a Keycloak; al rientro Envoy scambia il code, valida i token e genera un **cookie di sessione firmato HMAC**.  
   - **ExtAuthz** (OPA 9191): decisione di autorizzazione in base a contesto richiesta e claim.  
   - **Routing**: inoltro a `internal-service:8080` (HTTP sulla rete interna).

### 4.2 Egress (10003 → 10004 → destinazione)

1. I servizi interni configurano il **proxy**:
   
```
HTTP_PROXY=https://pep-envoy:10003
HTTPS_PROXY=https://pep-envoy:10003
```

2. Su **10003**, un filtro **Lua** estrae l’host di destinazione dalla richiesta proxy e risponde con **redirect** verso **10004** aggiungendo `?_dest=host:port`.  
3. Su **10004**:
   - **Lua** copia `?_dest` nell’header **`x-target-host`** (senza modificare `:authority` e path).  
   - **OAuth2/OIDC**: autenticazione come per l’ingress; lo **state** preserva l’URL con `?_dest`.  
   - **RBAC L7**: applica la policy su `x-target-host` (blacklist/whitelist).  
   - **Routing**: seleziona il cluster coerente con `x-target-host` (es. `allowed-server:80`).  

---

## 5. Sicurezza e policy

- **Separazione dei compiti**:
  - **OAuth2/OIDC** (Keycloak): *autenticazione* (identità).  
  - **ExtAuthz (OPA)**: *autorizzazione* (permesso).
- **Fail-secure**: indisponibilità di OPA → **deny**.  
- **RBAC L3/L4 ingress**: blocco IP noto (riduce il carico a valle).  
- **RBAC L7 egress**: controllo per dominio su `x-target-host`.  
  - Configurazione attuale: **blacklist** (nega ciò che matcha).  
  - Alternativa consigliata in contesti restrittivi: **whitelist** (ALLOW solo match espliciti, deny per default).  
- **Gestione certificati**:
  - Downstream (10001/10004): certificato server di Envoy.  
  - Upstream Keycloak: in produzione **validare** la CA e usare SNI corretto.  
