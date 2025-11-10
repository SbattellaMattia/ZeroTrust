package envoy.authz
import future.keywords
import input.attributes.request.http as http_req

default allow := false

# =============================
# REGOLA PRINCIPALE DI ACCESSO
# =============================
allow if {
    final_score >= 50
}

# =============================
# AUTENTICAZIONE, RUOLI E SCORE BASE
# =============================
auth := {
    "score": score,
    "username": username,
    "roles": roles
} if {
    # Prendi token Bearer da header
    authz := http_req.headers.authorization
    authz != ""
    token := trim_prefix(authz, "Bearer ")
    claims := io.jwt.decode(token)[1]

    username := claims.preferred_username
    roles := claims.realm_access.roles

    # Chiama il Trust Service (senza latest_ts)
    response := http.send({
        "method": "GET",
        "url": sprintf("http://trust-service:5000/score_dynamic/%s", [username]),
        "timeout": "2s",
        "force_json_decode": true
    })

    score := response.body.score
}

# =============================
# BONUS/MALUS IN BASE ALLA RETE
# =============================
net_adjust = 1.2 if {
    src := input.attributes.source.address.socketAddress.address
    net.cidr_contains("10.22.0.0/24", src)  # internal_net
}
else = 1.2 if {
    src := input.attributes.source.address.socketAddress.address
    net.cidr_contains("10.23.0.0/24", src)  # prod_net
}
else = 1.2 if {
    src := input.attributes.source.address.socketAddress.address
    net.cidr_contains("10.24.0.0/24", src)  # dev_net
}
else = 0.9 if {
    src := input.attributes.source.address.socketAddress.address
    net.cidr_contains("10.20.0.0/24", src)  # external_net
}

# =============================
# BONUS/MALUS IN BASE AL RUOLO
# =============================
role_adjust = 10 if { "admin" in auth.roles }
else = 5 if { "prod" in auth.roles }
else = 5 if { "dev" in auth.roles }
else = -5 if { "guest" in auth.roles }

# =============================
# SCORE FINALE (rete + ruolo)
# =============================
final_score := (auth.score + role_adjust) * net_adjust

# =============================
# LIVELLO DI ACCESSO
# =============================
access_level := "full" if {
    allow
    final_score >= 70
} else := "limited" if {
    allow
}

# =============================
# RESPONSE PER ACCESSO CONSENTITO
# =============================
response := {
    "allowed": true,
    "headers": {
        "x-user": auth.username,
        "x-roles": concat(",", auth.roles),
        "x-score": sprintf("%.2f", [auth.score]),
        "x-src-ip": input.attributes.source.address.socketAddress.address,
        "x-score-base": sprintf("%.2f", [auth.score]),
        "x-net-adjust": sprintf("%.1f", [net_adjust]),
        "x-role-adjust": sprintf("%d", [role_adjust]),
        "x-score-final": sprintf("%.2f", [final_score]),
        "x-access-level": access_level
    }
} if {
    allow
}

# =============================
# RESPONSE PER ACCESSO NEGATO
# =============================
response := {
    "allowed": false,
    "http_status": 403,
    "body": "{\"message\":\"Too low score\"}"
} if {
    not allow
}