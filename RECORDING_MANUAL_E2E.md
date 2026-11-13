# 录制管理第一版执行说明

## 目标

第一版采用固定测试会议室 + 手动客户端入会。接口脚本只负责录制控制链路，不控制客户端。

## 配置

固定会议室配置在 `data/config.ini`：

```ini
[recording]
room_id = 10001
room_name = manual-recording-test-room
record_name_prefix = api_auto_manual_recording
manual_join_required = true
min_record_seconds = 10
record_query_retry_attempts = 37
record_query_retry_interval_seconds = 5
```

执行前请确认：

- `room_id`：真实可入会的固定测试会议室 ID。
- `room_name`：该会议室的备注名称，便于核对。
- `record_name_prefix`：本次自动化录制文件名前缀，脚本会追加 `${timestamp}_${uuid8}`。

## 用例分组

`data/test_data.xlsx` 已新增 `录制管理` sheet。

- `REC_E2E_*`：需要手动客户端入会，用于验证真实录制链路。
- `REC_API_*`：不需要客户端入会，用于验证参数异常和边界。

## 手动入会链路

1. 确认 `recording.room_id` 对应会议室存在。
2. 使用客户端进入该会议室。
3. 打开摄像头和麦克风，保持在线。
4. 执行：

```bash
python run.py -k REC_E2E --no-open
```

命令启动后会打印当前 `room_id`、`room_name`、`record_name_prefix`，并要求输入 `READY`。
只有在客户端已经入会且摄像头/麦克风已打开后，才输入 `READY` 继续。

如果已经由外部流程确认客户端入会，可使用：

```bash
python run.py -k REC_E2E --no-open --confirm-recording-ready
```

脚本会执行：

1. 开始录制并提取 `record_id`。
2. 等待 10 秒。
3. 查询录制中状态。
4. 停止录制。
5. 立即开始轮询查询录制文件，默认每 5 秒查一次，最多查 37 次，查到 `file_id` 就立刻继续。
7. 获取下载地址。
8. 查询任务列表并提取旧文件名。
9. 修改录制任务名称。
10. 删除录制任务但保留录制文件。

如果没有手动入会，开始录制可能返回 `code=1000035`、`msg=The room does not open.`，用例会标记为前置条件不满足。

## 普通接口用例

不需要客户端入会时可执行：

```bash
python run.py -k REC_API --no-open
```

这组用例覆盖 `roomId` 为空、不存在、非法，查询不存在录制 ID，分页参数越界，改名和删除参数校验。
