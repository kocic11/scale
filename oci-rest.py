import base64
import email.utils
import hashlib
import json
import time
import calendar

# pip install httpsig_cffi requests six
import httpsig_cffi.sign
import requests
import six
from datetime import *; from dateutil.relativedelta import *

# Version 1.0.1


class SignedRequestAuth(requests.auth.AuthBase):
    """A requests auth instance that can be reused across requests"""
    generic_headers = [
        "date",
        "(request-target)",
        "host"
    ]
    body_headers = [
        "content-length",
        "content-type",
        "x-content-sha256",
    ]
    required_headers = {
        "get": generic_headers,
        "head": generic_headers,
        "delete": generic_headers,
        "put": generic_headers + body_headers,
        "post": generic_headers + body_headers
    }

    def __init__(self, key_id, private_key):
        # Build a httpsig_cffi.requests_auth.HTTPSignatureAuth for each
        # HTTP method's required headers
        self.signers = {}
        for method, headers in six.iteritems(self.required_headers):
            signer = httpsig_cffi.sign.HeaderSigner(
                key_id=key_id, secret=private_key,
                algorithm="rsa-sha256", headers=headers[:])
            use_host = "host" in headers
            self.signers[method] = (signer, use_host)

    def inject_missing_headers(self, request, sign_body):
        # Inject date, content-type, and host if missing
        request.headers.setdefault(
            "date", email.utils.formatdate(usegmt=True))
        request.headers.setdefault("content-type", "application/json")
        request.headers.setdefault(
            "host", six.moves.urllib.parse.urlparse(request.url).netloc)

        # Requests with a body need to send content-type,
        # content-length, and x-content-sha256
        if sign_body:
            body = request.body or ""
            if "x-content-sha256" not in request.headers:
                m = hashlib.sha256(body.encode("utf-8"))
                base64digest = base64.b64encode(m.digest())
                base64string = base64digest.decode("utf-8")
                request.headers["x-content-sha256"] = base64string
            request.headers.setdefault("content-length", len(body))

    def __call__(self, request):
        verb = request.method.lower()
        # nothing to sign for options
        if verb == "options":
            return request
        signer, use_host = self.signers.get(verb, (None, None))
        if signer is None:
            raise ValueError(
                "Don't know how to sign request verb {}".format(verb))

        # Inject body headers for put/post requests, date for all requests
        sign_body = verb in ["put", "post"]
        self.inject_missing_headers(request, sign_body=sign_body)

        if use_host:
            host = six.moves.urllib.parse.urlparse(request.url).netloc
        else:
            host = None

        signed_headers = signer.sign(
            request.headers, host=host,
            method=request.method, path=request.path_url)
        request.headers.update(signed_headers)
        return request

with open("./env.json") as f:
    env = json.load(f)
# -----BEGIN RSA PRIVATE KEY-----
# ...
# -----END RSA PRIVATE KEY-----
with open(env["api_key"]) as f:
    private_key = f.read().strip()

# This is the keyId for a key uploaded through the console
api_key = "/".join([
    env["tenancy"],
    env["oci_user"],
    env["fingerprint"]
])

auth = SignedRequestAuth(api_key, private_key)

headers = {
    "content-type": "application/json",
    "date": email.utils.formatdate(usegmt=True),
    # Uncomment to use a fixed date
    # "date": "Thu, 05 Jan 2014 21:31:40 GMT"
}


# # GET with query parameters
# uri = "https://iaas.us-ashburn-1.oraclecloud.com/20160918/instances?compartmentId={compartment_id}"
# uri = uri.format(
#     # availability_domain="Pjwf%3A%20PHX-AD-1",
#     # Older ocid formats included ":" which must be escaped
#     compartment_id="ocid1.compartment.oc1..".replace(":", "%3A"),
#     # display_name="TeamXInstances",
#     # volume_id="ocid1.volume.oc1.phx.".replace(":", "%3A")
# )
# response = requests.get(uri, auth=auth, headers=headers)
# # print(uri)
# print(response.text)

# # GET with query parameters
# uri = "https://iaas.us-ashburn-1.oraclecloud.com/20160918/instances/ocid1.instance.oc1.iad."
# response = requests.get(uri, auth=auth, headers=headers)
# # print(uri)
# print(response.text)

# GET
# uri = "https://functions.us-ashburn-1.oci.oraclecloud.com/20181201/functions/ocid1.fnfunc.oc1.iad."
# response = requests.get(uri, auth=auth, headers=headers)
# print(response.text)


# uri = "https://.apigateway.us-ashburn-1.oci.customer-oci.com/v1/hello"
# response = requests.get(uri, auth=auth, headers=headers)
# print(response.text)

# # POST with body
# uri = "https://iaas.us-ashburn-1.oraclecloud.com/20160918/volumeAttachments"
# body = """{
#     "compartmentId": "ocid1.compartment.oc1..",
#     "instanceId": "ocid1.instance.oc1.phx.",
#     "volumeId": "ocid1.volume.oc1.phx."
# }"""
# response = requests.post(uri, auth=auth, headers=headers, data=body)
# print("\n" + uri)
# print(response.request.headers["Authorization"])

# Invoke Fn
uri = env["fn_uri"]

response = requests.post(uri, auth=auth, headers=headers)
print(response.text)

# Get Job Status
# auth = (env["user"], env["password"])
# headers = {
#     "content-type": "application/json",
#     "X-ID-TENANT-NAME": "idcs-",
# }

# uri = "https://jaas.oraclecloud.com//paas/api/v1.1/activitylog/idcs-/job/185255292"
# http_response = requests.get(uri, auth=auth, headers=headers)
# print(http_response.text)