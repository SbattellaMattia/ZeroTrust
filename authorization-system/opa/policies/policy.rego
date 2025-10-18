# This example allows users to read their own profiles. This example shows how to:
#
# 	* Perform pattern matching on JSON values in Rego.
#	* Use Rego built-in functions to parse base64 encoded strings.
#	* Use parsed inputs provided by the OPA-Istio/Envoy integration.
#
# For more information see:
#
#	* Rego Built-in Functions: https://www.openpolicyagent.org/docs/latest/policy-reference/
#	* Equality: Assignment, Comparison, and Unification:
#     https://www.openpolicyagent.org/docs/latest/policy-language/#equality-assignment-comparison-and-unification
#	* OPA-Istio/Envoy Integration: https://github.com/open-policy-agent/opa-envoy-plugin

package envoy.authz
import future.keywords
import input.attributes.request.http as http_req

default allow := false

allow if {
	auth.score >= 50
}


auth := {"score": score, "username": username} if {
	authz := http_req.headers.authorization
  	authz != ""

  	token := trim_prefix(authz, "Bearer ")
  	claims := io.jwt.decode(token)[1]

  	# preferred_username o sub come fallback
  	username := claims.preferred_username
	
	# Chiama il Trust Service per ottenere il trust score
  	response := http.send({
    	"method": "GET",
    	"url": sprintf("http://trust-service:5000/score_dynamic/%s", [username]),
    	"timeout": "2s",
    	"force_json_decode": true
  	})

	score := response.body.score
}

# Calcola access level
access_level := "full" if {
    allow
    auth.score >= 70
} else := "limited" if {
    allow
}

# Response per allow - usa OBJECT non ARRAY
response := {
    "allowed": true,
    "headers": {
        "x-user": auth.username,
		"x-score": sprintf("%.2f", [auth.score]),
        "x-access-level": access_level,
    }
} if {
    allow
}

# Response per deny
response := {
    "allowed": false,
    "http_status": 403,
    "body": "{\"message\":\"Too low score\"}"
} if {
    not allow
}