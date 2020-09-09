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

        if not openapi_version or openapi_version != "3.0.0":
            raise TypeError("The provided file is not OpenAPI v3.0.0.")

        for path, methods in self._api_parser.specification["paths"].items():
            for method in methods:
                request = {
                    "path": path,
                    "parameters": {
                        "query": [],
                        "path": [],
                        "header": [],
                        "cookie": [],
                    },
                    "method": method,
                    "headers": [],
                    "body": [],
                }

                if "parameters" in self._api_parser.specification["paths"][path][method]:
                    for parameter in self._api_parser.specification["paths"][path][method]["parameters"]:
                        if parameter.get("required"):
                            name = parameter.get("name")

                            if not name:
                                raise ValueError("A required parameter without a name was defined in %s %s." % (
                                    method,
                                    path
                                ))

                            try:
                                example_value = OpenAPIParser._get_example_for_parameter(path, method, parameter)
                            except ValueError:
                                example_value = None

                            if parameter.get("in") in request["parameters"]:
                                request["parameters"][parameter.get("in")].append((name, example_value))
                            else:
                                raise ValueError("The parameter type %s is not supported. Sorry!" % parameter.get("in"))

                self._requests.append(request)

    @staticmethod
    def _get_example_for_parameter(path, method, parameter):
        schema = parameter.get("schema")
        example = None
        examples = None

        if schema:
            example = schema.get("example")
            examples = schema.get("example")

        x_example = parameter.get("x-example")

        if not example and not examples and not x_example:
            raise ValueError("There are no example(s) in the schema and no x-example for "
                             "parameter %s in %s %s." % (
                                 parameter.get("name"),
                                 method,
                                 path
                             ))
        if example:
            return example

        if examples:
            for key, val in examples.items():
                example_value = val.get("value")

                if not example_value:
                    raise ValueError("There are examples without values defined for parameter %s in %s %s" % (
                        parameter.get("name"),
                        path,
                        method
                    ))

                return example_value

        return x_example

