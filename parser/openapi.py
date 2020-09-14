from prance import ResolvingParser


class OpenAPIParser:
    _api_parser = None
    _requests = []
    _host = None
    _scheme = None
    _base_path = None

    def parse_file(self, file_name):
        self._api_parser = ResolvingParser(file_name)

        openapi_version = self._api_parser.specification.get("openapi")

        if not openapi_version or not openapi_version.startswith("3.0."):
            raise TypeError("The provided file is not OpenAPI v3.0.x.")

        for path, methods in self._api_parser.specification["paths"].items():
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

                if "requestBody" in self._api_parser.specification["paths"][path][method]:
                    body = self._api_parser.specification["paths"][path][method]["requestBody"]

                    if "content" not in body:
                        raise ValueError("No \"content\" for \"requestBody\" in %s %s" % (method, path))

                    if "application/json" not in body["content"]:
                        raise ValueError("Currently only \"applications/json\" is supported in %s %s" % (method, path))

                    request["body"] = self._parse_schema(path, method, body["content"]["application/json"])

                if "parameters" in self._api_parser.specification["paths"][path][method]:
                    for parameter in self._api_parser.specification["paths"][path][method]["parameters"]:
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

    def get_parsed_requests(self):
        if len(self._requests) <= 0:
            raise ValueError("Either no file at all or an empty file was parsed.")

        return self._requests

    def get_base_url(self):
        if not self._host or not self._scheme or not self._base_path:
            raise ValueError(
                "Base URL config is wrong: host, scheme or basePath is missing. Use --override-base-url.")
        return "%s%s%s" % (self._scheme, self._host, self._base_path)

    @staticmethod
    def _parse_schema(path, method, schema):
        try:
            primitive_parameter = OpenAPIParser._parse_primitive(schema)

            if primitive_parameter:
                return primitive_parameter

            array_parameter = OpenAPIParser._parse_array(schema)

            if array_parameter:
                return array_parameter

            object_parameter = OpenAPIParser._parse_object(schema)

            if object_parameter:
                return object_parameter

        except ValueError as ex:
            raise ValueError("Invalid \"schema\" was provided in %s %s: %s" % (
                path,
                method,
                str(ex)
            ))

    @staticmethod
    def _parse_array(parameter):
        if "schema" in parameter:
            parameter = parameter["schema"]
        if parameter.get("type") == "array":
            value = OpenAPIParser._parse_schema(None, None, parameter.get("items"))

            return value
        return None

    @staticmethod
    def _parse_object(parameter):
        if "schema" in parameter:
            parameter = parameter["schema"]

        if parameter.get("type") == "object":
            parsed_parameters = {}
            for property_name, content in parameter.get("properties").items():
                value = OpenAPIParser._parse_schema(None, None, content)
                parsed_parameters[property_name] = value

            return parsed_parameters
        return None

    @staticmethod
    def _parse_primitive(parameter):
        if "schema" in parameter:
            parameter = parameter["schema"]

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
