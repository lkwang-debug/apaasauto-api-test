import io
import logging


class InMemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self._buffer = io.StringIO()
        self.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s'))

    def emit(self, record):
        message = self.format(record)
        self._buffer.write(message + '\n')

    def clear(self):
        self._buffer = io.StringIO()

    def get_value(self):
        return self._buffer.getvalue().strip()


def get_logger(name):
    logger = logging.getLogger(name)
    if getattr(logger, '_apaas_initialized', False):
        return logger

    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s'))
    logger.addHandler(console_handler)

    memory_handler = InMemoryLogHandler()
    logger.addHandler(memory_handler)
    logger.memory_handler = memory_handler
    logger.propagate = False
    logger._apaas_initialized = True
    return logger


def clear_logger_logs(logger):
    memory_handler = getattr(logger, 'memory_handler', None)
    if memory_handler is not None:
        memory_handler.clear()


def get_logger_logs(logger):
    memory_handler = getattr(logger, 'memory_handler', None)
    if memory_handler is None:
        return ''
    return memory_handler.get_value()
