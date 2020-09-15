from prance import ResolvingParser
import logging

logger = logging.getLogger('apiknock')

class SwaggerParser:
    _api_parser = None
    _requests = []
    _host = None
    _scheme = None
    _base_path = None

    def parse_file(self, file_name):
        self._api_parser = ResolvingParser(file_name, strict=False)

        swagger_version = self._api_parser.specification.get("swagger")

        if not swagger_version or swagger_version != "2.0":
            raise TypeError("The provided file is not Swagger v2.0")

        if "host" in self._api_parser.specification and \
            "basePath" in self._api_parser.specification and \
            "schemes" in self._api_parser.specification:
                self._host = self._api_parser.specification["host"]
                self._base_path = self._api_parser.specification["basePath"]
                if "https" in self._api_parser.specification["schemes"]:
                    self._scheme = "https://"
                elif "http" in self._api_parser.specification["schemes"]:
                    self._scheme = "http://"
                else:
                    raise ValueError("Sorry the only supported schemes are https and http at the moment.")
        else:
            logger.warning("There is either no host, basePath or schemes defined in the Swagger file.")

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

                        if parameter_in == "body":
                            # body-parameters are defined by using a schema
                            schema = parameter.get("schema")

                            if not schema:
                                raise ValueError("\"schema\" is required for \"body\" parameter %s in %s %s." % (
                                    name,
                                    method,
                                    path
                                ))

                            request["body"] = SwaggerParser._parse_schema(path, method, schema)
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
            raise ValueError("Base URL config is wrong: host, scheme or basePath is missing.")
        return "%s%s%s" % (self._scheme, self._host, self._base_path)

    @staticmethod
    def _parse_schema(path, method, schema):
        try:
            primitive_parameter = SwaggerParser._parse_primitive(schema)

            if primitive_parameter:
                return primitive_parameter

            array_parameter = SwaggerParser._parse_array(schema)

            if array_parameter:
                return array_parameter

            object_parameter = SwaggerParser._parse_object(schema)

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
        if parameter.get("type") == "array":
            value = SwaggerParser._parse_schema(None, None, parameter.get("items"))

            return value
        else:
            return None

    @staticmethod
    def _parse_object(parameter):
        if parameter.get("type") == "object":
            parsed_parameters = {}
            for property_name, content in parameter.get("properties").items():
                value = SwaggerParser._parse_schema(None, None, content)
                parsed_parameters[property_name] = value

            return parsed_parameters

    @staticmethod
    def _parse_primitive(parameter):
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
