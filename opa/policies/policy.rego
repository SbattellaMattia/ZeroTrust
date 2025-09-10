package envoy.authz

# default deny
default allow := false

# Allow only requests whose path is "/public"
allow if {
  input.attributes.request.http.path == "/public"
}

