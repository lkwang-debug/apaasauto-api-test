# APAAS API 自动化测试项目说明

扫描日期：2026-04-29

## 1. 项目用途

`apaasauto-api-test` 是一个面向 APAAS 平台接口的自动化测试项目，当前主要覆盖组织部门管理和会议室管理两类接口。

项目采用“Excel 用例数据 + pytest 统一测试入口”的设计：测试人员在 `data/test_data.xlsx` 中维护接口路径、请求方法、请求数据、提取规则和断言，运行时由 `conftest.py` 读取 Excel 并参数化到 `testcases/test_all_api.py`，统一完成鉴权、发起请求、响应断言、变量提取和 Allure 报告输出。

## 2. 技术栈

| 类型 | 技术/库 | 当前用途 |
|---|---|---|
| 语言 | Python | 自动化测试脚本、工具模块 |
| 测试框架 | pytest 7.3.1 | 用例参数化、测试执行、fixture 管理 |
| HTTP 客户端 | requests 2.31.0 | 发起 APAAS HTTP 接口请求 |
| 数据驱动 | openpyxl 3.1.2 | 读取 `data/test_data.xlsx` 中的接口用例 |
| 测试报告 | allure-pytest 2.13.2 + Allure CLI | 生成请求、响应、断言和日志报告 |
| 数据库断言 | pymysql 1.1.1 | 支持 MySQL 查询断言，当前 Excel 未配置数据库断言 |
| 加密 | pycryptodome 3.20.0 | 对敏感字段执行 AES-CBC 加密 |
| 鉴权 | HMAC-SHA256 JWT | 基于 `app_key`、`app_secret` 生成 Bearer Token |

## 3. 目录结构

```text
apaasauto-api-test/
├── common/
│   ├── auth.py                 # JWT 生成
│   ├── crypto_util.py          # 密码类敏感字段加密
│   ├── request_util.py         # 请求构造、发送、变量提取
│   ├── assert_util.py          # 响应断言、数据库断言
│   ├── runtime_context.py      # 全局运行上下文
│   └── variable_store.py       # 跨用例变量存储
├── data/
│   ├── config.ini              # 环境地址、鉴权、数据库配置
│   └── test_data.xlsx          # Excel 用例源数据
├── testcases/
│   └── test_all_api.py         # 统一测试执行入口
├── utils/
│   ├── config_util.py          # 配置读取
│   ├── excel_reader.py         # Excel 用例解析
│   ├── jsonpath_util.py        # 简化 JSONPath 提取
│   ├── logger_util.py          # 控制台和内存日志
│   └── template_util.py        # ${变量} 模板替换
├── conftest.py                 # pytest 参数化和运行时清理
├── pytest.ini                  # pytest 配置
├── requirements.txt            # Python 依赖
└── run.py                      # 测试执行 + Allure 报告生成入口
```

## 4. 运行流程

1. `run.py` 清空并创建 `reports/allure-results`。
2. 调用 `python -m pytest testcases/test_all_api.py --alluredir reports/allure-results`。
3. `conftest.py` 使用 `ExcelReader` 读取 `data/test_data.xlsx` 所有 sheet，并将每一条启用用例参数化为一个 pytest case。
4. `test_all_api.py` 针对每条 `case_data` 调用 `RequestUtil.send_request`。
5. `RequestUtil` 生成 JWT，解析 `${变量}`，加密敏感字段，构造 URL、headers 和 payload 后发起请求。
6. `AssertUtil` 执行状态码、JSONPath 字段、包含关系、非等值、候选值包含、数据库等断言。
7. 如配置了提取规则，响应中的字段会写入 `VariableStore`，供后续用例通过 `${变量名}` 引用。
8. pytest 结束后，`run.py` 调用 Allure CLI 生成 `reports/allure-report`，并启动本地 HTTP 服务打开报告。

## 5. 配置说明

配置文件：`data/config.ini`

| 配置段 | 字段 | 说明 |
|---|---|---|
| `[api]` | `base_url` | 被测 APAAS 环境地址 |
| `[auth]` | `app_key`、`app_secret` | 生成 JWT 和敏感字段加密使用，不建议提交真实生产密钥 |
| `[db]` | `host`、`port`、`user`、`password`、`database`、`charset` | 数据库断言配置，当前 host 为空，因此数据库断言会跳过 |

运行命令：

```bash
pip install -r requirements.txt
python run.py --no-open
```

常用参数：

```bash
python run.py --no-open                 # 生成报告但不自动打开浏览器
python run.py --no-report               # 只执行 pytest，不生成 Allure HTML 报告
python run.py --report-port 18080       # 指定本地报告端口
python run.py -k DEP_001 --no-open      # 只跑匹配关键字的用例
```

注意：`run.py` 依赖本机已安装 Allure CLI 并加入 `PATH`。如果只执行 pytest 或 CI 中另行生成报告，可使用 `--no-report`。

## 6. 用例数据模型

Excel 表头固定为：

| 字段 | 说明 |
|---|---|
| 用例ID | pytest 参数 ID，例如 `DEP_001`、`ROOM_001` |
| 用例标题 | 报告中展示的中文用例名 |
| 请求方法 | 支持 `GET`、`GET2`、`POST`、`POST2`、`PUT`、`PATCH`、`DELETE`、`OPTIONS` |
| 接口路径 | 相对路径，会与 `base_url` 拼接，支持 `${变量}` |
| 请求头 | JSON 格式，可为空 |
| 请求数据 | JSON 格式，请求参数或 body |
| 提取规则 | JSON 格式，变量名到 JSONPath 的映射 |
| 响应断言 | JSON 格式，支持状态码和字段断言 |
| 数据库断言 | JSON 格式，支持 SQL 查询后字段 equals 断言 |
| 是否运行 | `Y`/`YES`/`TRUE`/`1` 表示启用 |

响应断言支持：

```json
{
  "status_code": 200,
  "equals": {
    "$.code": 0
  },
  "not_equals": {
    "$.result": null
  },
  "contains": {
    "$.message": "success"
  },
  "contains_any": {
    "$.message": ["成功", "success"]
  }
}
```

变量提取示例：

```json
{
  "room_id": "$.result"
}
```

后续用例可在接口路径、请求头、请求数据和断言中使用 `${room_id}`。

## 7. 当前用例概览

当前 `data/test_data.xlsx` 中可运行用例共 105 条：

| 模块 | 可运行用例数 | 覆盖重点 |
|---|---:|---|
| 组织部门管理 | 40 | 部门分页查询、新增、修改、删除、重复名称、必填项、类型错误、长度边界、父子层级异常 |
| 会议室管理 | 65 | 会议室创建、详情查询、列表查询、修改、删除、授权用户、录制配置、会控地址、入会链接、批量创建、参数异常 |

请求方法分布：

| 方法 | 数量 |
|---|---:|
| POST | 76 |
| GET | 11 |
| PUT | 9 |
| DELETE | 9 |

断言使用情况：

| 断言类型 | 用例数 |
|---|---:|
| `status_code` | 105 |
| `equals` | 72 |
| `contains_any` | 48 |
| `not_equals` | 33 |
| `contains` | 1 |
| 数据库断言 | 0 |

当前有 1 条未启用用例：`DEP_041`，标记为 `N`。

## 8. 当前已设计用例清单

| 模块 | 用例ID | 用例标题 | 方法 | 接口 |
|---|---|---|---|---|
| 组织部门管理 | DEP_001 | 查询部门分页成功并提取父部门ID | POST | `/paas/depart/v1/page` |
| 组织部门管理 | DEP_002 | 新增部门成功 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_003 | 查询新增部门成功 | POST | `/paas/depart/v1/page` |
| 组织部门管理 | DEP_004 | 修改部门成功 | POST | `/paas/depart/v1/update` |
| 组织部门管理 | DEP_005 | 查询修改后部门成功 | POST | `/paas/depart/v1/page` |
| 组织部门管理 | DEP_006 | 删除部门成功 | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_007 | 删除已删除部门返回不存在 | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_008 | 创建重复部门基础数据 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_009 | 新增重复部门名称失败 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_010 | 删除重复部门基础数据 | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_011 | 新增部门缺失departName | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_012 | 新增部门departName为空字符串 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_013 | 新增部门departName为null | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_014 | 新增部门departName超长 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_015 | 新增部门parentDepartId类型错误 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_016 | 分页查询currPage为0 | POST | `/paas/depart/v1/page` |
| 组织部门管理 | DEP_017 | 分页查询pageSize超限 | POST | `/paas/depart/v1/page` |
| 组织部门管理 | DEP_018 | 修改不存在部门失败 | POST | `/paas/depart/v1/update` |
| 组织部门管理 | DEP_019 | 创建业务场景父部门A | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_020 | 创建业务场景子部门B | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_021 | 更新父部门到子部门下失败 | POST | `/paas/depart/v1/update` |
| 组织部门管理 | DEP_022 | 删除业务场景子部门B | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_023 | 删除业务场景父部门A | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_024 | 新增部门名称纯数字成功 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_025 | 删除纯数字部门成功 | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_026 | 新增部门名称中文加数字成功 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_027 | 删除中文加数字部门成功 | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_028 | 新增部门名称大小写字母加数字成功 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_029 | 删除大小写字母加数字部门成功 | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_030 | 新增部门名称含特殊字符失败 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_031 | 删除组织departId为空字符串 | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_032 | 删除组织departId不传 | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_033 | 删除组织departId传字符串类型 | POST | `/paas/depart/v1/delete` |
| 组织部门管理 | DEP_034 | 创建修改接口参数覆盖基础部门 | POST | `/paas/depart/v1/create` |
| 组织部门管理 | DEP_035 | 修改部门departName超长失败 | POST | `/paas/depart/v1/update` |
| 组织部门管理 | DEP_036 | 修改部门departId类型错误 | POST | `/paas/depart/v1/update` |
| 组织部门管理 | DEP_037 | 修改部门parentDepartId类型错误 | POST | `/paas/depart/v1/update` |
| 组织部门管理 | DEP_038 | 修改部门departName为空字符串 | POST | `/paas/depart/v1/update` |
| 组织部门管理 | DEP_039 | 修改部门departName为null | POST | `/paas/depart/v1/update` |
| 组织部门管理 | DEP_040 | 删除修改接口参数覆盖基础部门 | POST | `/paas/depart/v1/delete` |
| 会议室管理 | ROOM_001 | 查询可用父部门ID | POST | `/paas/depart/v1/page` |
| 会议室管理 | ROOM_002 | 创建基础会议室standard+0 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_003 | 查询基础会议室详情 | GET | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_004 | 查询会议室列表按名称命中 | POST | `/paas/rooms/v1/queryRoomList` |
| 会议室管理 | ROOM_005 | 查询基础会议室录制配置默认值 | GET | `/paas/rooms/v1/record/setting/${room_id}` |
| 会议室管理 | ROOM_006 | 修改会议室discussion+1 | PUT | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_007 | 查询修改后会议室详情 | GET | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_008 | 修改会议室training+0 | PUT | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_009 | 查询training模式修改后详情 | GET | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_010 | 修改会议室custom+1 | PUT | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_011 | 查询custom模式修改后详情 | GET | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_012 | 会议室授权用户增量授权成功 | POST | `/paas/rooms/v1/authRoomUser` |
| 会议室管理 | ROOM_013 | 会议室授权用户role非法 | POST | `/paas/rooms/v1/authRoomUser` |
| 会议室管理 | ROOM_014 | 会议室授权用户授权列表为空 | POST | `/paas/rooms/v1/authRoomUser` |
| 会议室管理 | ROOM_015 | 会议室授权用户roomVid缺失 | POST | `/paas/rooms/v1/authRoomUser` |
| 会议室管理 | ROOM_016 | 会议室授权用户role类型错误 | POST | `/paas/rooms/v1/authRoomUser` |
| 会议室管理 | ROOM_017 | 更新录制配置A成功 | POST | `/paas/rooms/v1/record/setting/update` |
| 会议室管理 | ROOM_018 | 查询录制配置A成功 | GET | `/paas/rooms/v1/record/setting/${room_id}` |
| 会议室管理 | ROOM_019 | 更新录制配置B成功 | POST | `/paas/rooms/v1/record/setting/update` |
| 会议室管理 | ROOM_020 | 查询录制配置B成功 | GET | `/paas/rooms/v1/record/setting/${room_id}` |
| 会议室管理 | ROOM_021 | 更新录制配置mode4指定用户成功 | POST | `/paas/rooms/v1/record/setting/update` |
| 会议室管理 | ROOM_022 | 查询mode4录制配置返回成功 | GET | `/paas/rooms/v1/record/setting/${room_id}` |
| 会议室管理 | ROOM_023 | 录制配置recordVideoResolution非法 | POST | `/paas/rooms/v1/record/setting/update` |
| 会议室管理 | ROOM_024 | 录制配置sliceInterval过小 | POST | `/paas/rooms/v1/record/setting/update` |
| 会议室管理 | ROOM_025 | 会控地址获取成功 | GET | `/paas/rooms/v1/${room_id}/webControl?userId=1000000001` |
| 会议室管理 | ROOM_026 | 会控地址roomId不存在 | GET | `/paas/rooms/v1/99999999/webControl?userId=1000000001` |
| 会议室管理 | ROOM_027 | 会控地址userId类型错误 | GET | `/paas/rooms/v1/${room_id}/webControl?userId=abc` |
| 会议室管理 | ROOM_028 | 构造入会链接当前环境返回404 | POST | `/paas/rooms/v1/join-meeting/url` |
| 会议室管理 | ROOM_029 | 创建会议室standard+1成功 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_030 | 删除standard+1会议室成功 | DELETE | `/paas/rooms/v1/${room_combo_1_id}` |
| 会议室管理 | ROOM_031 | 创建会议室training+1成功 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_032 | 删除training+1会议室成功 | DELETE | `/paas/rooms/v1/${room_combo_2_id}` |
| 会议室管理 | ROOM_033 | 创建会议室custom+0成功 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_034 | 删除custom+0会议室成功 | DELETE | `/paas/rooms/v1/${room_combo_3_id}` |
| 会议室管理 | ROOM_035 | 创建verifyMode2密码房间成功 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_036 | 删除verifyMode2房间成功 | DELETE | `/paas/rooms/v1/${room_combo_4_id}` |
| 会议室管理 | ROOM_037 | 创建verifyMode1房间成功 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_038 | 删除verifyMode1房间成功 | DELETE | `/paas/rooms/v1/${room_combo_5_id}` |
| 会议室管理 | ROOM_039 | 创建会议室缺失roomName | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_040 | 创建会议室roomName为空字符串 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_041 | 创建会议室roomName为null | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_042 | 创建会议室roomName超长当前环境兼容通过 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_043 | 创建会议室roomName含特殊字符当前环境兼容通过 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_044 | 创建会议室verifyMode非法 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_045 | 创建会议室maxUserCount类型错误 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_046 | 创建会议室maxUserCount为0 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_047 | 创建verifyMode2缺失password | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_048 | 创建开启主席密码但chairPassword为空 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_049 | 创建会议室password类型错误 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_050 | 创建会议室chairPassword类型错误 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_051 | 创建会议室roomMode非法 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_052 | 创建会议室autoRecord非法值当前环境兼容通过 | POST | `/paas/rooms/v1/` |
| 会议室管理 | ROOM_053 | 查询会议室列表currPage为0 | POST | `/paas/rooms/v1/queryRoomList` |
| 会议室管理 | ROOM_054 | 查询会议室列表pageSize超限 | POST | `/paas/rooms/v1/queryRoomList` |
| 会议室管理 | ROOM_055 | 批量创建会议室成功 | POST | `/paas/rooms/v1/batchAddRoom` |
| 会议室管理 | ROOM_056 | 删除批量会议室A成功 | DELETE | `/paas/rooms/v1/${batch_room_id_1}` |
| 会议室管理 | ROOM_057 | 删除批量会议室B成功 | DELETE | `/paas/rooms/v1/${batch_room_id_2}` |
| 会议室管理 | ROOM_058 | 修改会议室roomId不存在 | PUT | `/paas/rooms/v1/99999999` |
| 会议室管理 | ROOM_059 | 修改会议室roomId类型错误 | PUT | `/paas/rooms/v1/abc` |
| 会议室管理 | ROOM_060 | 修改会议室roomName超长当前环境兼容通过 | PUT | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_061 | 修改会议室maxUserCount类型错误 | PUT | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_062 | 修改会议室roomMode非法值当前环境兼容通过 | PUT | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_063 | 修改会议室autoRecord非法值当前环境兼容通过 | PUT | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_064 | 删除基础会议室成功 | DELETE | `/paas/rooms/v1/${room_id}` |
| 会议室管理 | ROOM_065 | 删除已删除会议室返回失败 | DELETE | `/paas/rooms/v1/${room_id}` |

## 9. 后续维护建议

### 9.1 新增接口用例

1. 优先在 `data/test_data.xlsx` 新增 sheet 或追加到已有模块 sheet。
2. 保持表头完全一致，否则 `ExcelReader` 会直接报错。
3. 用例 ID 建议使用模块前缀递增，例如 `DEP_042`、`ROOM_066`。
4. 请求数据、提取规则、响应断言、数据库断言必须是合法 JSON。
5. 需要跨用例传递数据时，先在前置用例配置“提取规则”，后续用 `${变量名}` 引用。
6. 新增创建类用例时，应同步设计清理用例，避免测试环境残留数据。

### 9.2 断言维护

建议至少保留三层断言：

| 层级 | 建议 |
|---|---|
| HTTP 层 | 所有用例必须断言 `status_code` |
| 业务层 | 断言业务码、消息、关键字段，例如 `$.code`、`$.message`、`$.result.id` |
| 数据层 | 对关键新增、修改、删除流程补充数据库断言，当前项目能力已具备但还未实际使用 |

对于错误场景，不建议只断言 HTTP 200，应同时断言业务错误码或错误消息，避免接口“失败但返回格式变化”时漏检。

### 9.3 配置和密钥维护

1. `data/config.ini` 中的 `app_key`、`app_secret` 属于敏感配置，不建议提交生产值。
2. 建议按环境维护不同配置文件，例如 `config.dev.ini`、`config.test.ini`，再通过启动参数或环境变量选择。
3. 如果后续接入 CI，建议从 CI secret 注入鉴权和数据库配置。

### 9.4 用例执行顺序和依赖

当前用例存在明显顺序依赖，例如先创建部门/会议室，再提取 ID，后续查询、修改、删除引用该 ID。维护时需要注意：

1. 同一业务链路内不要随意调整顺序。
2. 如果需要并发执行或打乱顺序，需要先改造为每条用例自行准备和清理数据。
3. 当某个前置变量缺失时，当前框架会 `pytest.skip` 依赖该变量的用例。

### 9.5 框架维护建议

| 方向 | 建议 |
|---|---|
| Excel 可维护性 | 对用例 JSON 做格式校验工具，避免运行时才发现 JSON 语法错误 |
| 报告质量 | 保持请求、响应、断言、日志附件完整，便于定位失败 |
| 数据清理 | 对创建型用例统一约定清理用例或 teardown 机制 |
| 数据库断言 | 当前支持但未使用，可逐步补充核心链路的数据落库校验 |
| 安全 | 对 Allure 报告中的 Authorization、密码字段做脱敏，避免报告泄露敏感信息 |
| 稳定性 | 对依赖外部环境的数据，例如父部门、默认用户，建议做前置探测或固定测试租户 |

## 10. 当前风险点

1. 用例强依赖执行顺序和前置变量，不适合直接并发执行。
2. `data/config.ini` 包含鉴权配置，后续需要按环境做密钥隔离。
3. 当前数据库断言未启用，接口返回正确但数据落库异常的场景可能漏检。
4. Allure 附件会记录 headers 和 payload，需注意 Authorization 和密码类字段脱敏。
5. 部分用例标题中包含“当前环境兼容通过”，这类断言可能绑定当前环境行为，接口规范变更时需要重点复核。

