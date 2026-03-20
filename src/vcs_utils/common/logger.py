import logging
import logging.config
from pathlib import Path
from typing import Optional


"""Logging helper for the vcs_utils package.

Provides ``apply_config(config_path=None)`` to apply a logging config file
and ``get(name=None)`` to obtain a ``logging.Logger`` named ``vcs_utils`` or
``vcs_utils.<name>``.
"""


def apply_config(config_path: Optional[Path] = None) -> None:
    try:
        if config_path is None:
            config_path = Path(__file__).parent / "logging_default.ini"

        logger = logging.getLogger("vcs_utils")

        if config_path.exists():
            try:
                logging.config.fileConfig(str(config_path), disable_existing_loggers=False)
                return
            except Exception:
                # fall through to fallback handler
                pass

        # Fallback: ensure at least a StreamHandler exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
    except Exception:
        # Ensure we never raise during import/config application
        try:
            logging.getLogger("vcs_utils").addHandler(logging.StreamHandler())
        except Exception:
            pass


def get(name: Optional[str] = None) -> logging.Logger:
    """Return a :class:`logging.Logger` for the package.

    The returned logger name is ``vcs_utils`` when ``name`` is None,
    otherwise ``vcs_utils.<name>``.
    """

    logger_name = f"vcs_utils.{name}" if name else "vcs_utils"
    return logging.getLogger(logger_name)


if __name__ == "__main__":
    apply_config()
    logger = get()
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")