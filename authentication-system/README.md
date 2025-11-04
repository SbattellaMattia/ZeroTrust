
# Keycloak come Identity Provider

Keycloak è un sistema open-source di Identity and Access Management che consente di centralizzare la gestione dell'autenticazione e degli accessi in modo scalabile e sicuro. Nel contesto di questo progetto, Keycloak assume il ruolo di Identity Provider (IdP), fungendo da punto centrale di autenticazione all'interno di un'architettura Zero Trust.

> ⚠️ Sia il database H2 che la cartella con i secrets è stata esclusa da meccanismi di verisoning. Occorre generarle manualmente i segreti e impostare il reame.
## Introduzione ai Protocolli OAuth2 e OpenID Connect

Prima di analizzare l'implementazione specifica, è fondamentale comprendere i protocolli su cui si basa l'autenticazione del sistema.

### OAuth2: Delega dell'autorizzazione

OAuth2 è un framework di autorizzazione che consente alle applicazioni di ottenere accesso limitato alle risorse di un utente senza esporre le credenziali. Il protocollo si basa su quattro attori principali:

- **Resource Owner** (utente): il proprietario delle risorse protette
- **Client** (applicazione): l'applicazione che richiede accesso alle risorse (nel nostro caso, Envoy)
- **Authorization Server** (server di autorizzazione): il server che emette i token dopo aver autenticato l'utente (Keycloak)
- **Resource Server** (server delle risorse): il server che ospita le risorse protette

Il flusso **Authorization Code Grant** utilizzato in questo progetto è il più sicuro per applicazioni web e prevede questi passaggi :
1. L'applicazione reindirizza l'utente all'Authorization Server con una richiesta di autorizzazione
2. L'utente si autentica e autorizza l'applicazione
3. L'Authorization Server reindirizza l'utente all'applicazione con un codice autorizzativo temporaneo
4. L'applicazione scambia il codice con un access token contattando direttamente l'Authorization Server
5. L'applicazione usa l'access token per accedere alle risorse protette

### OpenID Connect: Autenticazione sopra OAuth2

OpenID Connect (OIDC) è un layer di identità costruito sopra OAuth2 che aggiunge funzionalità di autenticazione. Mentre OAuth2 gestisce l'autorizzazione ("cosa può fare l'applicazione"), OIDC gestisce l'autenticazione ("chi è l'utente").

Nel contesto di questo progetto, Keycloak agisce come **OpenID Provider**, emettendo sia access token OAuth2 che ID token OIDC. Quando un utente completa il login, Keycloak restituisce un ID Token firmato digitalmente che contiene i claim sull'identità dell'utente, permettendo a Envoy di verificarne l'autenticità senza dover ricontattare Keycloak per ogni richiesta.

## Architettura

L'implementazione adotta il principio della **separazione delle responsabilità** (Separation of Concerns), che rappresenta uno dei fondamenti dello sviluppo software moderno e delle architetture Zero Trust. In questo contesto, la logica di autenticazione e quella di autorizzazione sono state deliberatamente disaccoppiate per garantire maggiore modularità, sicurezza e manutenibilità del sistema.

### Componenti dell'Architettura

L'architettura Zero Trust implementata si compone di tre livelli distinti, ciascuno con responsabilità specifiche:

**1. Livello di Autenticazione - Keycloak (Identity Provider)**

Keycloak è responsabile esclusivamente della **fase di autenticazione**, occupandosi delle seguenti funzionalità:

- **Verifica delle credenziali**: gestione del processo di login mediante username e password degli utenti registrati nel sistema
- **Emissione dei token**: generazione di JSON Web Token (JWT) conformi allo standard OpenID Connect una volta completata con successo l'autenticazione
- **Gestione degli utenti**: creazione, modifica dei profili utente e operazioni di reset password
- **Registrazione degli eventi di sicurezza**: logging di tutti gli eventi rilevanti per la sicurezza, inclusi tentativi di login falliti, accessi riusciti e modifiche alle credenziali

> **Nota**: non è stata implementata una fase di SignUp o Logout esulando dallo scopo dimostrativo dei principi Zero Trust, ma si lavora esclusivamente con utenti già registrati dall'amministratore.

**2. Livello di Enforcement - Envoy PEP (Policy Enforcement Point)**

Envoy agisce come Policy Enforcement Point, intercettando tutte le richieste HTTP e garantendo che solo gli utenti autenticati e autorizzati possano accedere alle risorse protette. Le sue responsabilità includono:

- **Intercettazione delle richieste**: analisi di ogni richiesta HTTP in ingresso
- **Gestione del flusso OAuth2/OIDC**: reindirizzamento a Keycloak per utenti non autenticati e gestione dei callback
- **Validazione dei token**: verifica della validità e autenticità dei JWT ricevuti
- **Gestione delle sessioni**: creazione e validazione di cookie di sessione firmati con HMAC
- **Invocazione del PDP**: richiesta di decisioni di autorizzazione prima di inoltrare le richieste ai servizi backend

**3. Livello di Decisione - PDP e Trust Service (Policy Decision Point)**

Il Policy Decision Point rappresenta il cervello decisionale dell'architettura Zero Trust. La sua trattazione è lasciata alla rispettiva sezione.
Questa separazione garantisce che Keycloak si concentri unicamente sull'autenticazione e sulla registrazione degli eventi, mentre la logica decisionale complessa (autorizzazione, calcolo del trust score, valutazione del rischio) sia gestita da componenti specializzati.

## Configurazione di Keycloak

### Realm e Client OAuth2

La configurazione di Keycloak per il progetto prevede l'utilizzo di un **realm dedicato** denominato `zerotrust`, che rappresenta un contenitore isolato per la gestione di utenti, client e policy di sicurezza.

È stato configurato un client OAuth2 con identificativo `envoy-proxy`, che rappresenta il Policy Enforcement Point (PEP) basato su Envoy. Questo client è registrato in Keycloak con le seguenti caratteristiche:

- **Client ID**: `envoy-proxy`
- **Protocollo**: OpenID Connect (OIDC) su OAuth2
- **Flusso di autenticazione**: Authorization Code Grant con PKCE (Proof Key for Code Exchange)
- **Redirect URI**: configurato per gestire i callback OAuth2 dopo l'autenticazione dell'utente:
 `https://pep-envoy:10001/callback` per flussi ingress  
 `https://pep-envoy:10004/callback` per flussi egress


### Persistenza dei Dati e Audit Trail

Per garantire la continuità operativa e la tracciabilità degli eventi, è stato configurato un sistema di persistenza basato su database H2 integrato in Keycloak. La configurazione prevede:

- **Volume Docker persistente**: montato per salvare i dati del database, assicurando che utenti, configurazioni e eventi vengano mantenuti anche dopo riavvii del container o esecuzioni di `docker-compose down`
- **Event logging**: Keycloak registra in modo strutturato tutti gli eventi utente, negativi come tentativi di login falliti consecutivi (es. 3 o più tentativi) e orario dell'accesso, oppure positivi come accessi riusciti
- **Integrazione con il PDP**: gli eventi salvati nel database vengono successivamente interrogati dal Policy Decision Point (PDP) per il calcolo dinamico del **trust score** dell'utente, elemento fondamentale nell'architettura Zero Trust

Questo approccio implementa un **audit trail completo**, essenziale per analisi di sicurezza, compliance e valutazione comportamentale continua degli utenti.



## Sicurezza della Comunicazione

### Necessità del Protocollo HTTPS

L'implementazione di un canale di comunicazione sicuro è un requisito imprescindibile per il corretto funzionamento del flusso OAuth2/OIDC e per garantire la confidenzialità e l'integrità dei token scambiati.

L'utilizzo di HTTPS è obbligatorio per diversi motivi tecnici e di sicurezza :

- **Requisito OAuth2**: lo standard OAuth2 RFC 6749 prescrive che i token di accesso debbano essere trasmessi esclusivamente su connessioni TLS
- **Protezione dei cookie di sessione**: i cookie generati da Envoy (`BearerToken`, `OauthHMAC`, `OauthExpires`) sono marcati con il flag `Secure`, che impedisce la loro trasmissione su connessioni HTTP non cifrate
- **Prevenzione di attacchi man-in-the-middle**: TLS garantisce che le credenziali, i token JWT e i codici autorizzativi non possano essere intercettati o manomessi durante la trasmissione
- **Requisito di Envoy Gateway per OIDC**: la documentazione di Envoy specifica esplicitamente che il filtro OAuth2 richiede HTTPS per funzionare correttamente, poiché i provider di identità respingono redirect URI non sicuri


### Certificati TLS Self-Signed

Per consentire la comunicazione HTTPS in ambiente di sviluppo e testing, sono stati generati certificati TLS self-signed utilizzando OpenSSL. Il processo di generazione ha incluso:

1. **Creazione della chiave privata**: generazione del file `server.key` con algoritmo RSA a 2048 bit
2. **Generazione del certificato**: creazione del file `server.crt` con Subject Alternative Names (SAN) che includono i nomi simbolici utilizzati dall'infrastruttura (`pep-envoy`) per garantire la validazione corretta del certificato
3. **Montaggio nel container Envoy**: i file `server.crt` e `server.key` sono stati montati come volumi Docker all'interno del container Envoy e referenziati nella configurazione `envoy.yaml` tramite la sezione `transport_socket` di tipo `tls`

### Gestione dei Segreti OAuth2

La sicurezza del flusso OAuth2 si basa sulla corretta gestione di informazioni sensibili che devono essere protette da accessi non autorizzati.



Il file `oauth-secret.yaml` contiene il **client secret** associato al client `envoy-proxy` registrato in Keycloak. Questo segreto svolge le seguenti funzioni:

- **Autenticazione del client**: permette a Envoy di autenticarsi presso Keycloak quando effettua richieste al `token_endpoint` per scambiare l'authorization code con un access token
- **Prevenzione di attacchi di impersonation**: garantisce che solo client legittimi possano ottenere token per conto degli utenti
- **Conformità allo standard OAuth2**: implementa il meccanismo di autenticazione dei confidential client previsto da RFC 6749


Il file `oauth-hmac-secret.yaml` contiene la **chiave HMAC** utilizzata da Envoy per firmare crittograficamente i cookie di sessione OAuth2. Questa chiave è essenziale per:

- **Integrità dei cookie**: firma digitale dei cookie (`OauthHMAC`) per impedire la manomissione da parte di utenti malintenzionati
- **Validazione dello stato di sessione**: verifica che i cookie presentati dal browser siano stati effettivamente generati da Envoy e non siano stati contraffatti
- **Protezione contro CSRF**: quando combinato con meccanismi anti-CSRF, impedisce attacchi di tipo Cross-Site Request Forgery
- **Encoding delle URL nei callback**: Envoy utilizza questa chiave anche per codificare parametri nelle URL di redirect durante il flusso OAuth2
