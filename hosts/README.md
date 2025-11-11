# Host interni

Nella simulazione sono stati considerati due host a modello didattico, rappresentanti rispettivamente un PC del reparto sviluppo (**HOST DEV**) e uno del reparto produzione (**HOST PROD**). I due host appartengono a reti distinte, `dev_net` e `prod_net`, per riprodurre la separazione tra ambienti di test/sviluppo ed ambienti di produzione tipica delle reti aziendali.

<img width="1020" height="769" alt="host-interni" src="https://github.com/user-attachments/assets/49c2e9e8-c30c-4e96-aab0-5301dabc1a4e" />

>Nota: nell'immagine è stato omesso il flusso di autenticazione. Questo viene effettuato indistintamente dalla rete dalla quale ha origine la richiesta, ogni qual volta il pep non trova dei cookie di sessione validi. 

Seguendo i principi della security policy Zero Trust, anche il traffico proveniente da queste reti interne non viene considerato automaticamente affidabile: le richieste generate dagli host devono sempre passare attraverso il **PEP (Policy Enforcement Point)** collocato nella **Dmz Net**, che è l’unico punto autorizzato a dialogare sia con l’**INTERNAL WEB SERVICE** sia con i server esterni (distinti in **ALLOWED SERVER** e **BLOCKED SERVER** nella **External Net**). In particolare il **BLOCKED SERVER** è stato pensato come server non raggiungibile dall'interno della rete aziendale per evidenziare le funzionalità del `pep-envoy` di operare come un firewall L7.


## Funzionamento

Gli host (HOST DEV e HOST PROD) inviano tutte le richieste HTTP/HTTPS attraversando il PEP Envoy. Dal punto di vista del progetto, questo comportamento è ottenuto configurando il browser in modo che utilizzi sempre il PEP come proxy per le connessioni web.

Questa configurazione è gestita a livello di profilo del browser tramite un file **`user.js`** incluso nel pacchetto degli host. Il `user.js` imposta un proxy manuale puntato al PEP per tutto il traffico HTTP/HTTPS: quando l’utente utilizza il browser dagli host DEV o PROD, le connessioni non raggiungono direttamente il servizio interno o i server esterni, ma vengono automaticamente inviate al PEP, che applica le policy e decide se consentire, inoltrare o bloccare la richiesta.
