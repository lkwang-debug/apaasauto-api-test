# APAAS API 自动化测试

基于Python、pytest、Requests和Excel的接口自动化框架，支持鉴权、敏感字段加密、变量提取、数据库断言及Allure报告。

## 准备

```powershell
python -m pip install -r requirements.txt
Copy-Item data/config.example.ini data/config.ini
```

在本地`data/config.ini`填写接口地址、app_key、app_secret和实际录制会议室。需要数据库断言时填写db段。已有配置不要覆盖，真实配置不提交到Git。

安装Java和Allure CLI后执行：

```powershell
# 只收集用例，不调用接口
python -m pytest --collect-only
# 执行用例并生成报告
python run.py --no-open
```

报告输出到`reports/allure-report`，原始结果在`reports/allure-results`。

## 用例及素材

- 核心用例：`data/test_data.xlsx`。在Excel中维护运行标记、请求、提取和断言。
- 录制场景需要真实客户端提前进入配置的会议，见[录制执行说明](RECORDING_MANUAL_E2E.md)。
- 上传测试视频需自行准备，并按用例中的路径放到`data/1080p15f.mp4`。视频不随仓库上传。
- 架构和详细使用方式见[项目说明](PROJECT_OVERVIEW.md)。

仓库仅包含运行代码、Excel用例、小型测试文本、必要文档和配置模板。日志、报告、真实配置、视频、独立JMX场景集和接口Word文档保留在本地。
