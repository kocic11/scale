import io
import json
from fdk import response

import base64
import email.utils
import hashlib
import time
import calendar
import httpsig_cffi.sign
import requests
import six


def handler(ctx, data: io.BytesIO = None):
  payload = """
  {
  "components": {
      "WLS": {
      "hosts": [],
      "shape": "",
      "ignoreManagedServerHeapError": true
      }
  }
  }
  """

  config = ctx.Config()
  user = config.get("user")
  password = config.get("password")
  tenancy = config.get("tenancy")
  hosts = config.get("hosts")
  shape_up = config.get("shape_up")
  shape_down = config.get("shape_down")
  jcsinstance = config.get("jcsinstance")
  scheduled_time = config.get("scheduled_time")
  scheduled_time_format = config.get("scheduled_time_format")
  time_interval = config.get("time_interval")

  auth = (user, password)
  headers = {
    "content-type": "application/json",
    "X-ID-TENANT-NAME": tenancy,
  }

  current_time = calendar.timegm(time.gmtime())
  scheduled_time = calendar.timegm(time.strptime(scheduled_time, scheduled_time_format))
  
  if abs(current_time - scheduled_time) < int(time_interval):
    # Get current JCS nstance shape
    uri = "https://jaas.oraclecloud.com/paas/api/v1.1/instancemgmt/idcs-829b09c9d34b49be834b77b362810001/services/jaas/instances/testjcs"
    http_response = requests.get(uri, auth=auth, headers=headers)
    host = hosts.split(",")[0]
    shape = (http_response.json())["components"]["WLS"]["vmInstances"][host]["shapeId"]

    if shape_down == shape:
      shape = shape_up
    else:
      shape = shape_down
    
    # Scale up/down
    uri = "https://jaas.oraclecloud.com/paas/api/v1.1/instancemgmt/" + tenancy + "/services/jaas/instances/" + jcsinstance + "/hosts/scale"
    
    data = json.loads(payload)
    data["components"]["WLS"]["hosts"] = hosts.split(",")
    data["components"]["WLS"]["shape"] = shape
    
    http_response = requests.post(uri, auth=auth, headers=headers, data=json.dumps(data))
    return response.Response(ctx, response_data=http_response.json(), headers={"Content-Type": "application/json"})
