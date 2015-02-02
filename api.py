import urllib, requests

class CachedAPI():
  def __init__(self, endpoint, key):
    self.endpoint = endpoint
    self.key = key
    self.cache = {}

  def default_headers(self):
    return {'Accept': 'application/json'}

  def default_query_params(self):
    return {self.key[0]: self.key[1]}

  def make_request(self, service, **kwargs):
    query_params = self.default_query_params()
    query_params.update(kwargs)
    query_params = ['{}={}'.format(key, urllib.quote_plus(value)) for key,value in query_params.items() if value]
    url = "{}/{}?{}".format(self.endpoint, service, '&'.join(query_params))
    if url not in self.cache:
      try:
        self.cache[url] = requests.get(url, headers=self.default_headers()).json(strict=False)
      except:
        return {}
    return self.cache[url]

