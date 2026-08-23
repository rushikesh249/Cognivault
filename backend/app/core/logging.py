import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from backend.app.core.config import get_project_root


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging(config_path: Optional[Path] = None) -> None:
    root = get_project_root()
    if config_path is None:
        config_path = root / "configs" / "logging.yaml"

    level = "INFO"
    log_file: Optional[str] = "data/logs/app.log"
    fmt = "json"

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg: Dict[str, Any] = yaml.safe_load(f) or {}
                log_cfg = cfg.get("logging", {})
                level = log_cfg.get("level", level)
                log_file = log_cfg.get("log_file", log_file)
                fmt = log_cfg.get("format", fmt)
        except Exception:
            pass

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    if fmt.lower() == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
        )
    root_logger.addHandler(console_handler)

    # File Handler
    if log_file:
        log_path = root / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        if fmt.lower() == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
            )
        root_logger.addHandler(file_handler)
