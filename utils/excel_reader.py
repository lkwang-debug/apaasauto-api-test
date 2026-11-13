import json
from pathlib import Path

from openpyxl import load_workbook


EXPECTED_HEADERS = [
    "用例ID",
    "用例标题",
    "请求方法",
    "接口路径",
    "请求头",
    "请求数据",
    "提取规则",
    "响应断言",
    "数据库断言",
    "是否运行",
]


class ExcelReader:
    def __init__(self, file_path):
        self.file_path = Path(file_path)

    def read_all_sheets(self):
        workbook = load_workbook(self.file_path)
        cases = []
        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
            cases.extend(self._read_sheet(worksheet))
        return cases

    def _read_sheet(self, worksheet):
        header_row = [cell.value for cell in worksheet[1]]
        if header_row != EXPECTED_HEADERS:
            raise ValueError(
                f"Sheet '{worksheet.title}' headers mismatch. Expected: {EXPECTED_HEADERS}, actual: {header_row}"
            )

        cases = []
        for row_index, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
            row_dict = dict(zip(EXPECTED_HEADERS, row))
            if not self._should_run(row_dict.get("是否运行")):
                continue

            case = {
                "sheet_name": worksheet.title,
                "row_number": row_index,
                "case_id": str(row_dict.get("用例ID", "")).strip(),
                "title": str(row_dict.get("用例标题", "")).strip(),
                "request_method": str(row_dict.get("请求方法", "")).strip().upper(),
                "api_path": str(row_dict.get("接口路径", "")).strip(),
                "request_headers": self._parse_json_cell(row_dict.get("请求头"), default={}),
                "request_data": self._parse_json_cell(row_dict.get("请求数据"), default={}),
                "extract_rule": self._parse_json_cell(row_dict.get("提取规则"), default={}),
                "response_assert": self._parse_json_cell(row_dict.get("响应断言"), default={}),
                "db_assert": self._parse_json_cell(row_dict.get("数据库断言"), default={}),
            }
            cases.append(case)
        return cases

    @staticmethod
    def _parse_json_cell(value, default):
        if value in (None, ""):
            return default
        if isinstance(value, (dict, list)):
            return value
        return json.loads(str(value))

    @staticmethod
    def _should_run(value):
        if value is None:
            return False
        return str(value).strip().upper() in {"Y", "YES", "TRUE", "1"}
