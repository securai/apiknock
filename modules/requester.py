from urllib3.exceptions import InsecureRequestWarning
import requests
import logging

logger = logging.getLogger('apiknock')


class Requester:
    def __init__(self, scheme, host, base_path, auth_type=None, auth_name=None, request_list=None, proxy=None,
                 verify_certs=True):
        self._scheme = scheme
        self._host = host
        self._base_path = base_path
        self._proxy = proxy
        self._requests = [] if not request_list else request_list
        self._verify = verify_certs
        self._auth_type = auth_type
        self._auth_name = auth_name

    @staticmethod
    def _prettify_http_request(req):
        return '{}\r\n{}\r\n\r\n{}\n---'.format(
            req.method + ' ' + req.url,
            '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body if req.body else "",
        )

    @staticmethod
    def _prettify_http_response(res):
        return 'HTTP/1.1 {}\r\n{}\r\n\r\n{}\n---'.format(
            str(res.status_code) + ' ' + res.reason,
            '\r\n'.join('{}: {}'.format(k, v) for k, v in res.headers.items()),
            res.content if res.content else "",
        )

    def set_requests(self, request_list):
        self._requests = request_list

    def get_requests(self):
        return self._requests

    def send_request(self, method, url, query_string=None, headers=None, body=None, cookies=None,
                     content_type=None, auth_value=None):

        request_kwargs = {}

        if not self._verify:
            request_kwargs["verify"] = False
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

        if self._proxy:
            request_kwargs["proxies"] = {
                'http': self._proxy,
                'https': self._proxy,
            }

        if headers:
            request_kwargs["headers"] = headers

        if body and len(body) >= 1:
            if content_type == "json":
                request_kwargs["json"] = body
            else:
                request_kwargs["data"] = body

        if query_string:
            request_kwargs["params"] = query_string

        if cookies:
            request_kwargs["cookies"] = cookies

        if auth_value:
            logger.debug("Using authentication type %s with name %s" % (self._auth_type, self._auth_name))
            if self._auth_type == "header":
                if "headers" not in request_kwargs:
                    request_kwargs["headers"] = {}

                request_kwargs["headers"][self._auth_name] = auth_value
            elif self._auth_type == "bearer":
                if "headers" not in request_kwargs:
                    request_kwargs["headers"] = {}

                request_kwargs["headers"]["Authorization"] = "Bearer %s" % auth_value
            elif self._auth_type == "cookie":
                if "cookies" not in request_kwargs:
                    request_kwargs["cookies"] = {}

                request_kwargs["cookies"][self._auth_name] = auth_value
            elif self._auth_type == "query":
                if "params" not in request_kwargs:
                    request_kwargs["params"] = {}

                request_kwargs["params"][self._auth_name] = auth_value
            else:
                raise ValueError("Authentication type %s is not supported." % self._auth_type)

        if method.lower() not in ["get", "post", "put", "delete", "options"]:
            raise ValueError("Invalid HTTP Verb provided: %s" % method)

        logger.info("Sending request %s %s" % (method.upper(), url))
        logger.debug("Using kwargs for request: %s" % request_kwargs)

        response = requests.request(method, url=url, **request_kwargs)

        logger.debug("Actual request: \n%s" % self._prettify_http_request(response.request))
        logger.debug("Response: \n%s\n---" % self._prettify_http_response(response))

        return response

    def process_all_requests(self):
        for request in self._requests:
            self.process_request(request)

    def process_request(self, request, auth_value=None):
        base_url = "%s%s%s" % (self._scheme, self._host, self._base_path)

        path = request["path"]

        if path.startswith('/') and base_url.endswith('/'):
            path = path[1:]

        for path_param, value in request["parameters"]["path"].items():
            path = path.replace("{%s}" % path_param, str(value))

        try:
            return self.send_request(
                request["method"],
                base_url + path,
                query_string=request["parameters"]["query"],
                headers=request["parameters"]["header"],
                cookies=request["parameters"]["cookie"],
                body=request["body"] if "body" in request else None,
                content_type="json",
                auth_value=auth_value
            )
        except (ConnectionError, ConnectionRefusedError, OSError) as ex:
            msg = "[E] Error connecting to %s%s: %s" % (
                base_url,
                path,
                ex
            )
            logger.critical(msg)
            print(msg)
            import sys
            sys.exit(1)
