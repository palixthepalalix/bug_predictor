import urllib2
import json
from urllib import urlencode

#base64 encoded eq-jira creds

class JiraAPI:
    def __init__(self, auth_token, base_api_url):
        # has to be b64 encoded auth_token, will fix later
        self.auth_token = auth_token
        self.base_api_url = base_api_url

    def get_request(self, endpoint, qs=None):
        url = self.base_api_url + endpoint
        if qs is not None:
            url += ('?' + urlencode(qs))
        req = urllib2.Request(url)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', ('Basic ' + self.auth_token))
        return req

    def get_json(self, endpoint, qs):
        req = get_request(endpoint, qs)
        resp = urllib2.urlopen(req, timeout=60)
        return json.loads(resp.read())

    def get_issue(self, issue, fields='key'):
        return get_json('issue/' + issue, {'fields': fields})
