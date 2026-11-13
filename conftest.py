from pathlib import Path

import pytest

try:
    import allure
except ImportError:
    allure = None

from common.runtime_context import get_runtime_context
from utils.excel_reader import ExcelReader
from utils.logger_util import clear_logger_logs


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / 'data' / 'test_data.xlsx'


def pytest_generate_tests(metafunc):
    if 'case_data' not in metafunc.fixturenames:
        return

    reader = ExcelReader(DATA_FILE)
    cases = reader.read_all_sheets()
    ids = [case['case_id'] for case in cases]
    metafunc.parametrize('case_data', cases, ids=ids)


@pytest.fixture(autouse=True)
def reset_case_runtime():
    runtime = get_runtime_context()
    clear_logger_logs(runtime.logger)
    yield
    if allure:
        with allure.step('reset_case_runtime::0'):
            pass
