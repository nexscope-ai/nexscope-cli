# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Run a bundled script with authenticated redirects disabled."""
import os
import runpy
import sys
from urllib.parse import urlsplit
import urllib.request


def main():
    base = urlsplit(os.environ['NEXSCOPE_PROXY_BASE'])
    def check(url, headers):
        target = urlsplit(url)
        if any(k.lower() == 'authorization' for k in headers) and (target.scheme, target.netloc) != (base.scheme, base.netloc):
            raise RuntimeError('Authenticated request to another origin refused')
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if req.has_header('Authorization'):
                raise RuntimeError('Authenticated redirect refused')
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    class SafeRequest(urllib.request.BaseHandler):
        def http_request(self, req):
            check(req.full_url, dict(req.header_items()))
            return req
        https_request = http_request
    urllib.request.install_opener(urllib.request.build_opener(SafeRequest(), SafeRedirect()))
    import requests
    original = requests.sessions.Session.send
    def send(self, request, **kwargs):
        check(request.url, request.headers)
        if 'Authorization' in request.headers:
            kwargs['allow_redirects'] = False
        return original(self, request, **kwargs)
    requests.sessions.Session.send = send
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    sys.path.insert(0, os.path.dirname(script))
    runpy.run_path(script, run_name='__main__')


if __name__ == '__main__':
    main()
