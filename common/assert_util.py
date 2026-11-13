import re

try:
    import pymysql
except ImportError:
    pymysql = None

from utils.jsonpath_util import JsonPathNotFound, extract_json_path
from utils.template_util import TemplateResolver


class AssertUtil:
    def __init__(self, config, variable_store, logger):
        self.config = config
        self.variable_store = variable_store
        self.logger = logger
        self.resolver = TemplateResolver(config, variable_store)

    def prepare_response_assertions(self, response, response_json, assertion):
        assertion = assertion or {}
        resolved_assertion = self.resolver.resolve(assertion)
        items = []

        expected_status = resolved_assertion.get('status_code')
        if expected_status is not None:
            actual_status = response.status_code
            items.append(self._build_item('status_code', 'equals', expected_status, actual_status))

        items.extend(self._prepare_skip_if_items(response_json, resolved_assertion.get('skip_if', {})))
        items.extend(self._prepare_equals_items(response_json, resolved_assertion.get('equals', {})))
        items.extend(self._prepare_not_equals_items(response_json, resolved_assertion.get('not_equals', {})))
        items.extend(self._prepare_contains_items(response_json, resolved_assertion.get('contains', {})))
        items.extend(self._prepare_contains_any_items(response_json, resolved_assertion.get('contains_any', {})))
        items.extend(self._prepare_not_contains_items(response_json, resolved_assertion.get('not_contains', {})))
        items.extend(self._prepare_not_empty_items(response_json, resolved_assertion.get('not_empty', {})))
        items.extend(self._prepare_regex_items(response_json, resolved_assertion.get('regex', {})))
        items.extend(self._prepare_gt_items(response_json, resolved_assertion.get('gt', {})))
        items.extend(self._prepare_lt_items(response_json, resolved_assertion.get('lt', {})))
        return items

    def prepare_database_assertions(self, db_assertion):
        db_assertion = db_assertion or {}
        if not db_assertion or not db_assertion.get('sql'):
            return []

        db_config = self.config.get_db_config()
        if not db_config.get('host'):
            self.logger.info('DB assertion skipped because db host is not configured.')
            return []
        if pymysql is None:
            self.logger.info('DB assertion skipped because pymysql is not installed.')
            return []

        resolved_assertion = self.resolver.resolve(db_assertion)
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset=db_config['charset'],
            cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(resolved_assertion['sql'])
                row = cursor.fetchone() or {}
        finally:
            connection.close()

        items = []
        for key, expected in resolved_assertion.get('equals', {}).items():
            actual = row.get(key)
            items.append(self._build_item(key, 'equals', expected, actual, source='db'))
        return items

    @staticmethod
    def assert_item(item):
        if item['operator'] == 'skip_if':
            if item['matched']:
                import pytest

                pytest.skip(item['message'])
            return
        assert item['matched'], item['message']

    def _prepare_skip_if_items(self, response_json, rules):
        items = []
        for expression, expected in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            matched = error is None and actual == expected
            items.append(self._build_item(expression, 'skip_if', expected, actual, matched=matched, error=error))
        return items

    def _prepare_equals_items(self, response_json, rules):
        items = []
        for expression, expected in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            items.append(self._build_item(expression, 'equals', expected, actual, error=error))
        return items

    def _prepare_not_equals_items(self, response_json, rules):
        items = []
        for expression, expected in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            matched = error is None and not self._values_equal(actual, expected)
            items.append(self._build_item(expression, 'not_equals', expected, actual, matched=matched, error=error))
        return items

    def _prepare_contains_items(self, response_json, rules):
        items = []
        for expression, expected in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            matched = error is None and str(expected) in str(actual)
            items.append(self._build_item(expression, 'contains', expected, actual, matched=matched, error=error))
        return items

    def _prepare_contains_any_items(self, response_json, rules):
        items = []
        for expression, candidates in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            matched = error is None and any(str(candidate) in str(actual) for candidate in candidates)
            items.append(self._build_item(expression, 'contains_any', candidates, actual, matched=matched, error=error))
        return items

    def _prepare_not_contains_items(self, response_json, rules):
        items = []
        for expression, expected in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            matched = error is None and str(expected) not in str(actual)
            items.append(self._build_item(expression, 'not_contains', expected, actual, matched=matched, error=error))
        return items

    def _prepare_not_empty_items(self, response_json, rules):
        items = []
        for expression, expected in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            matched = error is None and self._is_not_empty(actual)
            items.append(self._build_item(expression, 'not_empty', expected, actual, matched=matched, error=error))
        return items

    def _prepare_regex_items(self, response_json, rules):
        items = []
        for expression, pattern in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            matched = error is None and re.search(str(pattern), str(actual)) is not None
            items.append(self._build_item(expression, 'regex', pattern, actual, matched=matched, error=error))
        return items

    def _prepare_gt_items(self, response_json, rules):
        items = []
        for expression, expected in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            matched = error is None and self._compare_number(actual, expected, 'gt')
            items.append(self._build_item(expression, 'gt', expected, actual, matched=matched, error=error))
        return items

    def _prepare_lt_items(self, response_json, rules):
        items = []
        for expression, expected in rules.items():
            actual, error = self._extract_actual(response_json, expression)
            matched = error is None and self._compare_number(actual, expected, 'lt')
            items.append(self._build_item(expression, 'lt', expected, actual, matched=matched, error=error))
        return items

    @staticmethod
    def _extract_actual(response_json, expression):
        try:
            return extract_json_path(response_json, expression), None
        except JsonPathNotFound as exc:
            return '<jsonpath_not_found>', str(exc)
        except Exception as exc:
            return '<extract_error>', str(exc)

    @staticmethod
    def _build_item(field, operator, expected, actual, matched=None, error=None, source='response'):
        if matched is None:
            matched = error is None and AssertUtil._values_equal(actual, expected)
        message = f"{field} {operator} expected={expected} actual={actual}"
        if operator == 'skip_if' and matched:
            message = f"precondition not met: {field} is {actual}"
        if error:
            message = f"{message} error={error}"
        return {
            'source': source,
            'field': field,
            'operator': operator,
            'expected': expected,
            'actual': actual,
            'matched': matched,
            'message': message,
        }

    @staticmethod
    def _values_equal(actual, expected):
        if actual == expected:
            return True
        if isinstance(actual, bool) or isinstance(expected, bool):
            return False
        if isinstance(actual, (int, float)) and isinstance(expected, str):
            return str(actual) == expected
        if isinstance(expected, (int, float)) and isinstance(actual, str):
            return actual == str(expected)
        return False

    @staticmethod
    def _compare_number(actual, expected, operator):
        try:
            actual_number = float(actual)
            expected_number = float(expected)
        except (TypeError, ValueError):
            return False
        if operator == 'gt':
            return actual_number > expected_number
        if operator == 'lt':
            return actual_number < expected_number
        return False

    @staticmethod
    def _is_not_empty(value):
        if value is None:
            return False
        if isinstance(value, str):
            return value != ''
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) > 0
        return True
