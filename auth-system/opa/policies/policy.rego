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

default allow := false

allow if {
	basic_auth.score >= 50
}

basic_auth := {"score": score} if {
	authz := input.attributes.request.http.headers.authorization
  	authz != ""

  	token := trim_prefix(authz, "Bearer ")
  	claims := io.jwt.decode(token)[1]

  	username := claims.preferred_username

	# Chiama il Trust Service per ottenere il trust score
  	response := http.send({
    	"method": "GET",
    	"url": sprintf("http://trust-service:5000/score/%s", [username]),
    	"timeout": "2s",
    	"force_json_decode": true
  	})

	score := response.body.score
}
