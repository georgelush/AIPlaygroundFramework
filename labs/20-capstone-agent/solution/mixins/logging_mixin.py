import logging

logger = logging.getLogger("agent_framework")


class LoggingMixin:

    def log_info(self, message: str) -> None:
        logger.info("[%s] %s", self.__class__.__name__, message)

    def log_warning(self, message: str) -> None:
        logger.warning("[%s] %s", self.__class__.__name__, message)

    def log_error(self, message: str) -> None:
        logger.error("[%s] %s", self.__class__.__name__, message)

    def log_step(self, step: str, detail: str = "") -> None:
        msg = f"STEP={step}" + (f" | {detail}" if detail else "")
        logger.info("[%s] %s", self.__class__.__name__, msg)
