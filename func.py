import base64
import calendar
import email.utils
import hashlib
import io
import json
import time
from datetime import *

import httpsig_cffi.sign
import requests
import six
from dateutil.relativedelta import *
from fdk import response

def fireFn(scheduled_time, time_interval):
  scheduled_time_split = scheduled_time.split(":")
  hour=int(scheduled_time_split[0])

  days = 0
  if(hour == 0):
    days = 1

  minute=int(scheduled_time_split[1])
  second=int(scheduled_time_split[2])

  NOW = datetime.utcnow()
  print("NOW: ", NOW)
  TODAY = date.fromtimestamp(NOW.timestamp())

  SCHEDULED = TODAY + relativedelta(days=+days, hour=hour, minute=minute, second=second)
  print("SCHEDULED: ", SCHEDULED)
  
  difference = relativedelta(NOW, SCHEDULED)
  print(difference.hours, difference.minutes, difference.seconds)
  seconds = abs(difference.seconds + difference.minutes*60 + difference.hours*3600)
  
  return abs(seconds) < int(time_interval)

def scale(ctx):
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
    "X-ID-TENANT-NAME": tenancy
  }
  
  if fireFn(scheduled_time, time_interval):
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
    
    result = requests.post(uri, auth=auth, headers=headers, data=json.dumps(data)).json()
    return response.Response(ctx, response_data=result, headers={"Content-Type": "application/json"})
  
  return response.Response(ctx, response_data=None, headers={"Content-Type": "application/json"}) 

def handler(ctx, data: io.BytesIO = None):
  return scale(ctx)