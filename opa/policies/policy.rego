package envoy.authz

import future.keywords

default allow := {"decision": "deny"}

# Entry point chiamato da Envoy
allow := response if {
    input.attributes.request.http != null

    # Recupero username dall’header (es. "x-user")
    username := input.attributes.request.http.headers["x-user"]

    # Chiamata al trust-service
    resp := http.send({
        "method": "GET",
        "url": sprintf("http://trust-service:5000/score/%s", [username]),
        "timeout": "3s"
    })

    resp.status_code == 200
    score := resp.body.score

    decision := decide_access[score]

    response := {"decision": decision}
}

# Decisione in base al punteggio
decide_access[decision] if {
    input_score := input
    input_score >= 70
    decision := "full"
}

decide_access[decision] if {
    input_score := input
    input_score >= 40
    input_score < 70
    decision := "read-only"
}

decide_access[decision] if {
    input_score := input
    input_score < 40
    decision := "deny"
}
