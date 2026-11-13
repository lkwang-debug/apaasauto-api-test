import time
import uuid
import random
import string
from pathlib import Path

from common.assert_util import AssertUtil
from common.request_util import RequestUtil
from common.variable_store import VariableStore
from utils.config_util import ConfigUtil
from utils.logger_util import get_logger


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = BASE_DIR / 'data' / 'config.ini'

_RUNTIME_CONTEXT = None


class RuntimeContext:
    def __init__(self):
        self.logger = get_logger('apaas-auto-test')
        self.config = ConfigUtil(CONFIG_FILE)
        self.variable_store = VariableStore()
        self.variable_store.put('timestamp', str(int(time.time())))
        self.variable_store.put('uuid8', uuid.uuid4().hex[:8])
        self.variable_store.put('crurent_time', time.strftime('%Y-%m-%d %H:%M:%S'))
        self.variable_store.put('random_roomtName', self._random_room_name())
        self.request_util = RequestUtil(self.config, self.variable_store, self.logger)
        self.assert_util = AssertUtil(self.config, self.variable_store, self.logger)

    @staticmethod
    def _random_room_name():
        characters = string.ascii_letters + string.digits + '_'
        return ''.join(random.choice(characters) for _ in range(random.randint(1, 32)))


def get_runtime_context():
    global _RUNTIME_CONTEXT
    if _RUNTIME_CONTEXT is None:
        _RUNTIME_CONTEXT = RuntimeContext()
    return _RUNTIME_CONTEXT
