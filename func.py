# pylint: disable=W0614
# pylint: disable=no-member

import base64
import calendar
import email.utils
import hashlib
import io
import json
import time
from datetime import *
import logging

import httpsig_cffi.sign
import requests
import six
from dateutil.relativedelta import *
from fdk import response
from fdk.response import Response

log_level = "DEBUG"

def __fireFn(scheduled_time, time_interval):
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.debug("__fireFn started.")
    scheduled_time_split = scheduled_time.split(":")
    hour = int(scheduled_time_split[0])

    days = 0
    if(hour == 0):
        days = 1

    minute = int(scheduled_time_split[1])
    second = int(scheduled_time_split[2])

    NOW = datetime.utcnow()
    logger.debug("NOW: \t\t%s", NOW.strftime("%Y-%m-%d %H:%M:%S"))
    TODAY = date.fromtimestamp(NOW.timestamp())

    SCHEDULED = TODAY + \
        relativedelta(days=+days, hour=hour, minute=minute, second=second)
    logger.debug("SCHEDULED: \t%s", SCHEDULED)
    if NOW < SCHEDULED:
        difference = relativedelta(SCHEDULED, NOW)
        logger.debug("Scheduled to run in %s hour(s), %s minute(s), and %s second(s)",
                     difference.hours, difference.minutes, difference.seconds)
    else:
        SCHEDULED = SCHEDULED + relativedelta(days=+1)
        difference = relativedelta(SCHEDULED, NOW)
        logger.debug("Scheduled to run in %s hour(s), %s minute(s), and %s second(s)",
                     difference.hours, difference.minutes, difference.seconds)

    seconds = abs(difference.seconds + difference.minutes *
                  60 + difference.hours*3600)
    logger.debug("__fireFn ended.")
    return abs(seconds) < int(time_interval)


def scale(ctx):
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.debug("Scale started.")
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
    time_interval = config.get("time_interval")

    auth = (user, password)
    headers = {
        "content-type": "application/json",
        "X-ID-TENANT-NAME": tenancy
    }
    response = Response(ctx, response_data="Noop")
    if __fireFn(scheduled_time, time_interval):
        # Get current JCS nstance shape
        uri = "https://jaas.oraclecloud.com/paas/api/v1.1/instancemgmt/" + \
            tenancy + "/services/jaas/instances/" + jcsinstance
        http_response = requests.get(uri, auth=auth, headers=headers)
        logger.debug("Response status: %i", http_response.status_code)
        host = hosts.split(",")[0]
        if http_response.status_code == requests.codes.OK:
            shape = (http_response.json())[
                "components"]["WLS"]["vmInstances"][host]["shapeId"]

            if shape_down == shape:
                shape = shape_up
            else:
                shape = shape_down

            # Scale up/down
            uri = "https://jaas.oraclecloud.com/paas/api/v1.1/instancemgmt/" + \
                tenancy + "/services/jaas/instances/" + jcsinstance + "/hosts/scale"

            data = json.loads(payload)
            data["components"]["WLS"]["hosts"] = hosts.split(",")
            data["components"]["WLS"]["shape"] = shape

            result = requests.post(
                uri, auth=auth, headers=headers, data=json.dumps(data))
            logger.debug("Response status: %s", result.status_code)
            response = Response(ctx, response_data=result.json(), headers={
                                "Content-Type": "application/json"}, status_code=result.status_code)
    logger.debug("Scale ended.")
    return response


def handler(ctx, data: io.BytesIO = None):
    global log_level
    config = ctx.Config()
    log_level = config.get("log_level")
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.debug("Function started")
    response = scale(ctx)
    logger.debug("Response status code is %s", response.status())
    logger.debug("Response is %s", response.body())
    logger.debug("Function ended.")
    return response
