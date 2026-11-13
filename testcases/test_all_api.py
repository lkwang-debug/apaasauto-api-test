import json
import time
import traceback
from contextlib import nullcontext

import pytest

try:
    import allure
except ImportError:
    allure = None

from common.runtime_context import get_runtime_context
from utils.jsonpath_util import JsonPathNotFound
from utils.logger_util import get_logger_logs


def _dump_content(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _attach(name, content, attachment_type=None):
    if not allure:
        return
    if attachment_type is None:
        attachment_type = allure.attachment_type.TEXT
    allure.attach(content, name, attachment_type)


def _step(title):
    if not allure:
        return nullcontext()
    return allure.step(title)


def _format_request_attachment(request_info):
    return (
        f"method: {request_info['method']}\n"
        f"url: {request_info['url']}\n\n"
        f"headers_template:\n{json.dumps(request_info['headers_template'], ensure_ascii=False, indent=2, default=str)}\n\n"
        f"headers:\n{json.dumps(request_info['headers'], ensure_ascii=False, indent=2, default=str)}\n\n"
        f"payload_template:\n{json.dumps(request_info['payload_template'], ensure_ascii=False, indent=2, default=str)}\n\n"
        f"payload:\n{json.dumps(request_info['payload'], ensure_ascii=False, indent=2, default=str)}"
    )


def _format_response_attachment(response, response_json):
    body = response_json if response_json is not None else response.text
    if not isinstance(body, str):
        body = json.dumps(body, ensure_ascii=False, indent=2, default=str)
    return f"status: {response.status_code}\n\nbody:\n{body}"


def _format_assertion_step(item):
    operator_map = {
        'equals': 'equals',
        'not_equals': 'not_equals',
        'contains': 'contains',
        'contains_any': 'contains_any',
    }
    operator = operator_map.get(item['operator'], item['operator'])
    return f"{item['field']} {operator} expected:{item['expected']} actual:{item['actual']}"


def _get_retry_config(case_data, resolver):
    assertion = case_data.get('response_assert') or {}
    retry = assertion.get('retry') or {}
    retry = resolver.resolve(retry)
    attempts = int(retry.get('attempts', 1))
    interval_seconds = float(retry.get('interval_seconds', 0))
    attempts = max(attempts, 1)
    interval_seconds = max(interval_seconds, 0)
    return attempts, interval_seconds


@pytest.mark.api
class TestAllAPI:
    def test_all_api(self, case_data):
        runtime = get_runtime_context()
        logger = runtime.logger
        request_util = runtime.request_util
        assert_util = runtime.assert_util

        display_title = f"{case_data['case_id']} {case_data['title']}"
        if allure:
            allure.dynamic.title(display_title)
            if hasattr(allure, 'parameter_mode'):
                allure.dynamic.parameter('case_data', '', mode=allure.parameter_mode.HIDDEN)

        attempts, interval_seconds = _get_retry_config(case_data, assert_util.resolver)
        last_error = None
        result = None
        response = None
        response_json = None
        request_info = None

        for attempt in range(1, attempts + 1):
            try:
                result = request_util.send_request(case_data)
            except KeyError as exc:
                pytest.skip(f'dependency variable missing: {exc}')
            except Exception:
                with _step('log'):
                    _attach('log', get_logger_logs(logger) or traceback.format_exc())
                raise

            response = result['response']
            response_json = result['response_json']
            request_info = result['request_info']

            with _step(f"request attempt {attempt}: {request_info['method']} {case_data['api_path']}"):
                _attach(f"{request_info['method']}_request", _format_request_attachment(request_info))
                _attach('response', _format_response_attachment(response, response_json))

            try:
                response_assertions = assert_util.prepare_response_assertions(
                    response,
                    response_json,
                    case_data.get('response_assert'),
                )
                db_assertions = assert_util.prepare_database_assertions(case_data.get('db_assert'))

                with _step('response assertions'):
                    for item in response_assertions:
                        with _step(_format_assertion_step(item)):
                            assert_util.assert_item(item)
                    for item in db_assertions:
                        with _step(_format_assertion_step(item)):
                            assert_util.assert_item(item)

                extracted = request_util.extract_variables(case_data.get('extract_rule'), response_json)
                if extracted:
                    with _step('extract'):
                        _attach('extract_variables', _dump_content(extracted), allure.attachment_type.JSON if allure else None)
                last_error = None
                break
            except (AssertionError, JsonPathNotFound) as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                logger.info("Retrying case %s after failure on attempt %s/%s: %s", case_data['case_id'], attempt, attempts, exc)
                time.sleep(interval_seconds)
            except Exception:
                with _step('log'):
                    log_payload = {
                        'log': get_logger_logs(logger),
                        'traceback': traceback.format_exc(),
                    }
                    _attach('log', _dump_content(log_payload), allure.attachment_type.JSON if allure else None)
                raise

        if last_error is not None:
            with _step('log'):
                log_payload = {
                    'log': get_logger_logs(logger),
                    'traceback': ''.join(traceback.format_exception_only(type(last_error), last_error)),
                }
                _attach('log', _dump_content(log_payload), allure.attachment_type.JSON if allure else None)
            raise last_error

        logs = get_logger_logs(logger)
        if logs:
            with _step('log'):
                _attach('log', logs)
