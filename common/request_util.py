import json
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from common.auth import get_jwt_token
from common.crypto_util import encrypt_sensitive_fields
from utils.jsonpath_util import extract_json_path
from utils.template_util import TemplateResolver


class LocalResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body, ensure_ascii=False)

    def json(self):
        return self._body


class RequestUtil:
    def __init__(self, config, variable_store, logger):
        self.config = config
        self.variable_store = variable_store
        self.logger = logger
        self.session = requests.Session()
        self.resolver = TemplateResolver(config, variable_store)

    def send_request(self, case_data):
        method_name = case_data["request_method"].upper()
        request_headers_template = case_data.get("request_headers") or {}
        request_data_template = case_data.get("request_data") or {}

        if method_name == "WAIT":
            request_data = self.resolver.resolve(request_data_template)
            return self._wait(request_data, request_headers_template, request_data_template)

        jwt_token = get_jwt_token(self.config)
        self.variable_store.put("jwt_token", jwt_token)

        headers = self.resolver.resolve(request_headers_template)
        request_data = self.resolver.resolve(request_data_template)
        api_path = self.resolver.resolve(case_data["api_path"])
        is_absolute_api_path = self._is_absolute_url(str(api_path))
        url = self._build_url(api_path)
        if not is_absolute_api_path:
            request_data = self._encrypt_request_data(request_data)
            headers["Authorization"] = f"Bearer {jwt_token}"

        request_kwargs = self._build_request_kwargs(method_name, headers, request_data)
        real_method = method_name.replace("2", "")
        self.logger.info("Executing %s %s", real_method, url)
        response = self.session.request(method=real_method, url=url, **request_kwargs)

        try:
            response_json = response.json()
        except ValueError:
            response_json = None

        return {
            "response": response,
            "response_json": response_json,
            "request_info": {
                "method": real_method,
                "url": url,
                "headers_template": request_headers_template,
                "headers": headers,
                "payload_template": request_data_template,
                "payload": request_data,
                "request_kwargs": self._sanitize_request_kwargs(request_kwargs),
            },
        }

    def _wait(self, request_data, request_headers_template, request_data_template):
        seconds = float(request_data.get("seconds", 1))
        self.logger.info("Waiting %.1f seconds", seconds)
        time.sleep(seconds)
        response = LocalResponse(
            200,
            {
                "code": 0,
                "msg": "waited",
                "result": {
                    "seconds": seconds,
                },
            },
        )
        return {
            "response": response,
            "response_json": response.json(),
            "request_info": {
                "method": "WAIT",
                "url": "local://wait",
                "headers_template": request_headers_template,
                "headers": {},
                "payload_template": request_data_template,
                "payload": request_data,
                "request_kwargs": {},
            },
        }

    def extract_variables(self, extract_rule, response_json):
        if not extract_rule:
            return {}

        extracted = {}
        for variable_name, expression in extract_rule.items():
            value = extract_json_path(response_json, expression)
            self.variable_store.put(variable_name, value)
            extracted[variable_name] = {
                "expression": expression,
                "value": value,
            }
            self.logger.info("Extracted variable %s=%s", variable_name, value)
        return extracted

    def _encrypt_request_data(self, request_data):
        app_key = self.config.get("auth", "app_key", fallback="")
        app_secret = self.config.get("auth", "app_secret", fallback="")
        return encrypt_sensitive_fields(request_data, app_key, app_secret)

    @staticmethod
    def _sanitize_request_kwargs(request_kwargs):
        sanitized = dict(request_kwargs)
        return sanitized

    def _build_url(self, api_path):
        if self._is_absolute_url(str(api_path)):
            return str(api_path)
        return f"{self.config.get_base_url()}/{str(api_path).lstrip('/')}"

    @staticmethod
    def _is_absolute_url(value):
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def _build_request_kwargs(method_name, headers, request_data):
        kwargs = {"headers": headers, "timeout": 20}
        body_type = None
        if isinstance(request_data, dict):
            body_type = request_data.get("_body_type")

        if body_type == "binary_file":
            file_path = Path(request_data["file_path"])
            kwargs["data"] = file_path.read_bytes()
            headers.setdefault("Content-Type", request_data.get("content_type", "application/octet-stream"))
            return kwargs

        if method_name in {"GET", "GET2", "OPTIONS"}:
            kwargs["params"] = request_data or None
        elif method_name == "POST":
            kwargs["json"] = request_data or None
        elif method_name == "POST2":
            kwargs["data"] = json.dumps(request_data, ensure_ascii=False) if request_data else None
            headers.setdefault("Content-Type", "application/json")
        elif method_name == "PUT":
            kwargs["json"] = request_data or None
        elif method_name == "PATCH":
            kwargs["json"] = request_data or None
        elif method_name == "DELETE":
            if isinstance(request_data, dict) and request_data.pop("_param_type", None) == "query":
                kwargs["params"] = request_data or None
            else:
                kwargs["json"] = request_data or None
        else:
            raise ValueError(f"Unsupported request method: {method_name}")
        return kwargs
