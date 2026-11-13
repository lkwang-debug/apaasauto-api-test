from configparser import ConfigParser
from pathlib import Path


class ConfigUtil:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.parser = ConfigParser()
        self.parser.read(self.config_path, encoding="utf-8")

    def get(self, section, option, fallback=None):
        return self.parser.get(section, option, fallback=fallback)

    def get_by_key(self, key, fallback=None):
        if "." in key:
            section, option = key.split(".", 1)
            return self.get(section, option, fallback=fallback)

        for section in self.parser.sections():
            if self.parser.has_option(section, key):
                return self.get(section, key, fallback=fallback)
        return fallback

    def get_base_url(self):
        return self.get("api", "base_url", fallback="").rstrip("/")

    def get_db_config(self):
        section = "db"
        if not self.parser.has_section(section):
            return {}
        return {
            "host": self.get(section, "host", fallback=""),
            "port": self.parser.getint(section, "port", fallback=3306),
            "user": self.get(section, "user", fallback=""),
            "password": self.get(section, "password", fallback=""),
            "database": self.get(section, "database", fallback=""),
            "charset": self.get(section, "charset", fallback="utf8mb4"),
        }
