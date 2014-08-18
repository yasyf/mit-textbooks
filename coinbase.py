import os
import hashlib
import hmac
import urllib2
import time
import json

#This code sample demonstrates a GET and a POST call to the Coinbase API
#Before implementation, set environmental variables with the names API_KEY and API_SECRET.

def make_coinbase_request(url, body=None):
  opener = urllib2.build_opener()
  nonce = int(time.time() * 1e6)
  message = str(nonce) + url + ('' if body is None else body)
  signature = hmac.new(os.environ['COINBASE_API_SECRET'], message, hashlib.sha256).hexdigest()


  headers = {'ACCESS_KEY' : os.environ['COINBASE_API_KEY'],
             'ACCESS_SIGNATURE': signature,
             'ACCESS_NONCE': nonce,
             'Accept': 'application/json'}

  # If we are passing data, a POST request is made. Note that content_type is specified as json.
  if body:
    headers.update({'Content-Type': 'application/json'})
    req = urllib2.Request(url, data=body, headers=headers)

  # If body is nil, a GET request is made.
  else:
    req = urllib2.Request(url, headers=headers)

  try:
    resp = opener.open(req)
    if 'error' in json.loads(resp):
      return make_coinbase_request(url, body)
    else:
      return resp
  except urllib2.HTTPError as e:
    print e
    return e
