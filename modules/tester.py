from modules import knockerconfig
import logging
import re
import sys

logger = logging.getLogger('apiknock')


class Tester:
    def __init__(self, requests, knockerconf, requester, user_auth_table):
        self._requests = requests
        self._knockerconf = knockerconf
        self._requester = requester
        self._user_auth_table = user_auth_table

        self._errors = []
        self._success = []
        self._failed = []
        self._actual_requests = 0

        self._checker_dict = {
            'http_code': self._check_http_code,
            'http_body': self._check_http_body,
        }

    @staticmethod
    def _check_http_code(response, value):
        """
        Checks if the response has a correct HTTP status code
        :param response: The response object produced by Python requests module
        :param value: The status code, which has to be >= 100 and <= 599
        :return: True if the status code matches, False otherwise
        """
        try:
            # triggers if value is a string
            value = int(value)
            if value < 100 or value > 599:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Provided value %s is not a valid HTTP status code (>=100 and <= 599)." % value)

        logger.debug("Using http status code check: SHOULD: %s / IS: %s" % (value, response.status_code))

        return {
            "success": True if response.status_code == value else False,
            "message": "EXPECTED: %s / IS %s" % (value, response.status_code)
        }

    @staticmethod
    def _check_http_body(response, value):
        """
        Checks if the response body contains a specified string.
        :param response: The response object produced by Python requests module
        :param value: A regular expression which identifies the string.
        :return: True if the body matches, False otherwise
        """
        try:
            logger.debug("Using http body check with reg exp %s" % value)
            return {
                "success": True if re.search(value, response.text, re.MULTILINE) else False,
                "message": "Regular Expression: %s" % value,
            }
        except (AttributeError, re.error) as ex:
            raise ValueError("Could not parse %s as a valid regular expression: %s" % (value, ex))

    def get_failed(self):
        return self._failed

    def get_successful(self):
        return self._success

    def get_errors(self):
        return self._errors

    def get_total_requests(self):
        return self._actual_requests

    def test_all_requests(self):
        auth_matrix = self._knockerconf.get(knockerconfig.AUTH_MATRIX)
        self._actual_requests = 0
        for request in self._requests:
            logger.debug("Processing request: %s" % request)
            if "path" not in request:
                msg = "The parsed request does not have the required attribute \"path\". " \
                      "This should not happen and indicates a massive internal error. Exiting..."
                logger.critical(msg)
                sys.stderr.write("%s\n" % msg)
                sys.exit(1)

            if request["path"] not in auth_matrix:
                self._errors.append("Path %s is in API file but not in AuthMatrix of KnockerConf." % request["path"])
                continue

            if request["method"] not in auth_matrix[request["path"]]:
                self._errors.append("Method %s for path %s, is in API file but not in AuthMatrix of KnockerConf." % (
                    request["method"],
                    request["path"]
                ))
                continue

            current_matrix = auth_matrix[request["path"]][request["method"]]

            logger.debug("Auth Matrix found for request %s (%s): %s" % (
                request["path"],
                request["method"],
                current_matrix
            ))

            if "success" not in current_matrix:
                self._errors.append("For path %s (%s) there is no definition of \"success\" checks in the config." % (
                    request["path"],
                    request["method"]
                ))
                continue

            if "blocked" not in current_matrix:
                self._errors.append("For path %s (%s) there is no definition of \"blocked\" checks in the config." % (
                    request["path"],
                    request["method"]
                ))
                continue

            if current_matrix["blocked"][0] not in self._checker_dict:
                self._errors.append("For path %s (%s) there was an invalid check method %s for blocked." % (
                    request["path"],
                    request["method"],
                    current_matrix["blocked"][0]
                ))
                continue

            if current_matrix["success"][0] not in self._checker_dict:
                self._errors.append("For path %s (%s) there was an invalid check method %s for success." % (
                    request["path"],
                    request["method"],
                    current_matrix["success"][0]
                ))
                continue

            for key, value in current_matrix["matrix"].items():
                if key.startswith("user_"):
                    if key not in self._user_auth_table:
                        self._errors.append("For path %s (%s) there was a user provided (%s) who had no auth info." % (
                            request["path"],
                            request["method"],
                            key
                        ))
                        continue

                response = self._requester.process_request(request, self._user_auth_table[key])
                self._actual_requests += 1

                check = "success" if value else "blocked"

                print("%s %s (%s): " % (
                    request["method"].upper(),
                    request["path"],
                    key
                ), end='')

                try:
                    result = self._checker_dict[current_matrix[check][0]](response, current_matrix[check][1])
                    if result["success"]:
                        msg = "For request %s (%s) and user %s the check succeeded. Check Output: %s" % (
                            request["path"],
                            request["method"],
                            key,
                            result["message"]
                        )
                        self._success.append((request["path"], request["method"], key, msg))
                        print("\033[92mSuccess\033[0m (%s)" % result["message"])
                        logger.info(msg)
                    else:
                        msg = "For request %s (%s) and user %s the check failed. Check Output: %s" % (
                            request["path"],
                            request["method"],
                            key,
                            result["message"]
                        )
                        self._failed.append((request["path"], request["method"], key, msg))
                        print("\033[91mFailed\033[0m (%s)" % result["message"])
                        logger.info(msg)
                except ValueError as ex:
                    msg = "The check function raised an exception for path %s (%s) and user %s: %s" % (
                        request["path"],
                        request["method"],
                        key,
                        ex
                    )
                    print("Error (%s)" % ex)
                    logger.error(msg)
                    self._errors.append((request["path"], request["method"], key, msg))
