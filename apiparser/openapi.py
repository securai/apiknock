import yaml
import json
import logging

logger = logging.getLogger('apiknock')


class OpenAPIParser:
    _api_version = None
    _api_spec = None
    _requests = []
    _host = None
    _scheme = None
    _base_path = None

    def parse_file(self, file_name):
        with open(file_name, "r") as api_file:
            try:
                # First try to load as YAML
                self._api_spec = yaml.safe_load(api_file)
            except yaml.YAMLError:
                # If it is not a YAML, try to load as JSON
                try:
                    self._api_spec = json.load(api_file)
                except json.JSONDecodeError:
                    raise TypeError("Invalid file provided, as it can neither be parsed as YAML nor JSON.")

        openapi_version = self._api_spec.get("openapi", None)

        if not openapi_version:
            openapi_version = self._api_spec.get("swagger", None)

            if not openapi_version:
                raise TypeError("The provided file is not OpenAPI file.")

        if openapi_version.startswith("3"):
            logger.info("Processing this file as OpenAPI v3.x")
            self._api_version = 3
            self._process_openapi3()
        elif openapi_version.startswith("2"):
            logger.info("Processing this file as OpenAPI v2.x (\"Swagger\")")
            self._api_version = 2
            self._process_openapi2()
        else:
            raise TypeError("Currently only OpenAPI v2 and v3 are supported.")

    def _process_openapi3(self):
        # Handles the processing of OpenAPI files with version 3.
        for path, methods in self._api_spec["paths"].items():
            for method in methods:
                request = {
                    "path": path,
                    "parameters": {
                        "query": {},
                        "path": {},
                        "header": {},
                        "cookie": {},
                    },
                    "method": method,
                }

                if "requestBody" in self._api_spec["paths"][path][method]:
                    body = self._api_spec["paths"][path][method]["requestBody"]
                    if "$ref" in body:
                        body = self._parse_reference(body)

                    if "content" in body:
                        if "application/json" not in body["content"]:
                            raise ValueError("Currently only \"applications/json\" is supported in %s %s" % (
                                method, path))

                        request["body"] = self._parse_schema(path, method, body["content"]["application/json"])
                    else:
                        print("[W] No content for requestBody provided for %s %s. This request might be useless." % (
                            method, path))
                        request["body"] = {"not-provided-in-api-sec": "sorry-for-this"}

                if "parameters" in self._api_spec["paths"][path][method]:
                    for parameter in self._api_spec["paths"][path][method]["parameters"]:
                        if "$ref" in parameter:
                            parameter = self._parse_reference(parameter)

                        name = parameter.get("name")
                        parameter_in = parameter.get("in")

                        if not name:
                            raise ValueError("A required parameter without a name was defined in %s %s." % (
                                method,
                                path
                            ))

                        if not parameter_in:
                            raise ValueError("The \"in\" parameter is required for %s in %s %s." % (
                                name,
                                method,
                                path,
                            ))

                        example_value = self._parse_schema(path, method, parameter)

                        if parameter.get("in") in request["parameters"]:
                            request["parameters"][parameter.get("in")][name] = example_value
                        else:
                            raise ValueError("The parameter type %s is not supported. Sorry!" % parameter.get("in"))

                self._requests.append(request)

    def _process_openapi2(self):
        # Processes OpenAPI version 2 ("Swagger files")
        if "host" in self._api_spec and "basePath" in self._api_spec and "schemes" in self._api_spec:
            self._host = self._api_spec["host"]
            self._base_path = self._api_spec["basePath"]
            if "https" in self._api_spec["schemes"]:
                self._scheme = "https://"
            elif "http" in self._api_spec["schemes"]:
                self._scheme = "http://"
            else:
                raise ValueError("Sorry the only supported schemes are https and http at the moment.")
        else:
            logger.warning("There is either no host, basePath or schemes defined in the Swagger file.")

        for path, methods in self._api_spec["paths"].items():
            for method in methods:
                request = {
                    "path": path,
                    "parameters": {
                        "query": {},
                        "path": {},
                        "header": {},
                        "cookie": {},
                    },
                    "method": method,
                }

                if "parameters" in self._api_spec["paths"][path][method]:
                    for parameter in self._api_spec["paths"][path][method]["parameters"]:
                        if "$ref" in parameter:
                            parameter = self._parse_reference(parameter)

                        name = parameter.get("name")
                        parameter_in = parameter.get("in")

                        if not name:
                            raise ValueError("A required parameter without a name was defined in %s %s." % (
                                method,
                                path
                            ))

                        if not parameter_in:
                            raise ValueError("The \"in\" parameter is required for %s in %s %s." % (
                                name,
                                method,
                                path,
                            ))

                        if parameter_in == "body":
                            # body-parameters are defined by using a schema
                            schema = parameter.get("schema")

                            if not schema:
                                raise ValueError("\"schema\" is required for \"body\" parameter %s in %s %s." % (
                                    name,
                                    method,
                                    path
                                ))

                            request["body"] = self._parse_schema(path, method, schema)
                        else:
                            # if it is not a body-parameter, a type must be defined
                            parameter_type = parameter.get("type")

                            if not parameter_type:
                                raise ValueError("\"type\" is required for parameters %s in %s %s" % (
                                    name,
                                    method,
                                    path
                                ))

                            example_value = self._parse_schema(path, method, parameter)

                            if parameter.get("in") in request["parameters"]:
                                request["parameters"][parameter.get("in")][name] = example_value
                            else:
                                raise ValueError("The parameter type %s is not supported. Sorry!" % parameter.get("in"))

                self._requests.append(request)

    def get_parsed_requests(self):
        if len(self._requests) <= 0:
            raise ValueError("Either no file at all or an empty file was parsed.")

        return self._requests

    def get_base_url(self):
        if not self._host or not self._scheme or not self._base_path:
            raise ValueError(
                "Base URL config is wrong: host, scheme or basePath is missing. Use --override-base-url.")
        return "%s%s%s" % (self._scheme, self._host, self._base_path)

    def _parse_reference(self, reference):
        reference = reference.get("$ref")
        logger.debug("Looking for reference: %s" % reference)

        if not reference.startswith("#/"):
            raise ValueError(
                "A reference was defined, however only local references are supported at the moment.")

        reference_paths = reference.split("/")
        del reference_paths[0]  # Remove the "#" element
        current_item = self._api_spec

        for reference_path in reference_paths:
            current_item = current_item.get(reference_path, None)
            if not current_item:
                raise ValueError("Could not find reference path %s" % reference_path)

        return current_item

    def _parse_schema(self, path, method, schema):
        try:
            primitive_parameter = self._parse_primitive(schema)

            if primitive_parameter:
                return primitive_parameter

            array_parameter = self._parse_array(schema)

            if array_parameter:
                return array_parameter

            object_parameter = self._parse_object(schema)

            if object_parameter:
                return object_parameter

        except ValueError as ex:
            raise ValueError("Invalid \"schema\" was provided in %s %s: %s" % (
                path,
                method,
                str(ex)
            ))

    def _parse_array(self, parameter):
        if "schema" in parameter:
            parameter = parameter["schema"]
        if parameter.get("type") == "array":
            value = self._parse_schema(None, None, parameter.get("items"))

            return value
        return None

    def _parse_object(self, parameter):
        if "schema" in parameter:
            parameter = parameter["schema"]

        if parameter.get("type") == "object":
            parsed_parameters = {}
            if "properties" not in parameter:
                return "secanium-object"
            for property_name, content in parameter.get("properties").items():
                value = self._parse_schema(None, None, content)
                parsed_parameters[property_name] = value

            return parsed_parameters
        return None

    def _parse_primitive(self, parameter):
        if "schema" in parameter:
            parameter = parameter["schema"]

        if "$ref" in parameter:
            parameter = self._parse_reference(parameter)

        if "type" not in parameter:
            raise ValueError("Neither type nor schema defined for parameter.")

        parameter_type = parameter.get("type")
        parameter_format = parameter.get("format")
        default = parameter.get("default", None)
        example = parameter.get("example", None)
        x_example = parameter.get("x-example", None)

        if default:
            return default
        if example:
            return example
        if x_example:
            return x_example

        if not parameter_type:
            raise ValueError("No \"type\" provided.")

        if "enum" in parameter:
            return parameter["enum"][0]

        if parameter_type == "string":
            if parameter_format == "email":
                return "info@secanium.de"
            elif parameter_format == "uuid":
                return "00000000-1111-2222-3333-445566778899"
            elif parameter_format == "byte":
                return "U2VjYW5pdW0K"
            elif parameter_format == "binary":
                return "001122334455"
            elif parameter_format == "date":
                return "2020-06-08"
            elif parameter_format == "date-time":
                return "2020-06-08T19:22:00+02:00"
            else:
                return "secanium"
        elif parameter_type == "integer":
            if parameter.get("minimum", None):
                return parameter.get("minimum")
            if parameter.get("maximum", None):
                return parameter.get("maximum")
            return 1234
        elif parameter_type == "number":
            return 12.3
        elif parameter_type == "boolean":
            return True
        else:
            return None
