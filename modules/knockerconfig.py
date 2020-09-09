import json
import logging
import sys

AUTH_MATRIX = "auth_matrix"
CONTENT_TYPE = "content_type"
USER_COUNT = "user_count"
PARAMETER_OVERRIDE = "parameter_override"


class KnockerConfig:
    _valid_fields = [
        AUTH_MATRIX,
        CONTENT_TYPE,
        USER_COUNT,
        PARAMETER_OVERRIDE,
    ]
    _config = {
        CONTENT_TYPE: "json",
        USER_COUNT: 2,
    }

    def set(self, config_name, value):
        if config_name in self._valid_fields:
            logging.debug("Parameter %s set to %s", config_name, value)
            self._config[config_name] = value
        else:
            raise ValueError("Invalid configuration directive \"%s\"." % config_name)

    def get(self, config_name):
        if config_name in self._valid_fields:
            return self._config.get(config_name, None)
        else:
            raise ValueError("Invalid configuration directive \"%s\"." % config_name)

    def is_valid(self):
        if AUTH_MATRIX not in self._config \
                or not isinstance(self._config[AUTH_MATRIX], dict) \
                or len(self._config[AUTH_MATRIX]) >= 1:
            logging.error("Configuration parameter %s is missing or invalid." % AUTH_MATRIX)
            raise ValueError("No \"%s\" configured." % AUTH_MATRIX)

        if USER_COUNT not in self._config or 2 <= self._config[USER_COUNT] >= 10:
            logging.error("Configuration parameter %s is either not provided or not between 2 and 10." % USER_COUNT)
            raise ValueError("No \"%s\" provided or not between 2 and 10" % USER_COUNT)

        if "content_type" not in self._config or self._config["content_type"] != "json":
            logging.error("Configuration parameter %s is missing or invalid (currently only \"json\" is)" % CONTENT_TYPE)
            raise ValueError("\"content_type\" not provided or not supported. Currently only \"json\" works.")

    def generate_config_file(self, requests, path="knockerconf.json"):
        auth_matrix = {}
        for request in requests:
            if request["path"] not in auth_matrix:
                auth_matrix[request["path"]] = {}

            auth_matrix[request["path"]][request["method"]] = {
                "matrix" : {
                    "user_1": True,
                    "user_2": False,
                },
                "success": [
                    "http_code", 200
                ],
                "blocked": [
                    "http_code", 403
                ],
            }

        self.set(AUTH_MATRIX, auth_matrix)

        with open(path, "w") as config_file:
            logging.info("Trying to write ApiKnock configuration to %s" % path)
            json.dump(self._config, config_file)

    def load_config_file(self, path):
        try:
            with open(path, "r") as config_file:
                logging.info("Trying to load config file from path %s." % path)
                self._config = json.load(config_file)
        except (IOError, json.JSONDecodeError) as ex:
            msg = "Could not load config file %s: %s" % (path, ex)
            logging.critical(msg)
            sys.stderr.write("%s\n" % msg)
            sys.exit(1)
