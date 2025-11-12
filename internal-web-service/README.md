# Internal Web Service

Questo componente rappresenta l'**internal service** dell’architettura **Zero Trust** del progetto.  
Ha il compito di mostrare all’utente un’interfaccia diversa in base al **punteggio di fiducia** calcolato dal **Trust Service** e verificato dal **PDP-OPA**.

---

## Obiettivo

Simulare il comportamento di un’applicazione aziendale che **adatta il livello di accesso** in base alla **fiducia** dell’utente.  
Ogni richiesta viene verificata tramite i componenti del sistema Zero Trust (**Envoy**, **OPA** e **Trust Service**), e solo in seguito l’interfaccia viene aggiornata in modo coerente con il risultato della valutazione.

---

## Logica di funzionamento

L’utente accede all’applicazione e, in base al punteggio restituito dal **Trust Service**, l’interfaccia mostra uno dei tre scenari:

| **Punteggio utente** | **Livello di accesso** | **Descrizione** |
|----------------------|------------------------|------------------|
| `< 50` | **Accesso bloccato** | L’utente non supera la soglia minima di fiducia. |
| `≥ 50` e `< 70` | **Accesso limitato** | L’utente può visualizzare solo alcune informazioni. |
| `≥ 70` | **Accesso completo** | L’utente ha pieno accesso alle funzionalità. |

---

## Interfacce utente

### Accesso completo (`score ≥ 70`)
<img width="546" height="711" alt="accesso_completo" src="https://github.com/user-attachments/assets/2876057f-b16b-45e6-8439-715c5ce52699" />

### Accesso limitato (`50 ≤ score < 70`)
<img width="555" height="542" alt="accesso_limitato" src="https://github.com/user-attachments/assets/79698e79-d04f-49fe-878c-357ea1b38695" />

### Accesso bloccato (`score < 50`)
<img width="439" height="42" alt="accesso_bloccato" src="https://github.com/user-attachments/assets/ea8525c1-fae8-4af1-a079-c5cd1cc1bd76" />




---
