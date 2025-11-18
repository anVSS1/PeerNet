from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self, agent_id: str, name: str = None):
        self.agent_id = agent_id
        self.name = name or "Agent_%s" % agent_id

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and return results.
        Must be implemented by subclasses.
        """
        pass

    def log_activity(self, message: str, level: str = 'info'):
        """
        Log agent activity.
        """
        try:
            log_message = "[%s] %s" % (self.name, message)
            if level == 'info':
                logger.info(log_message)
            elif level == 'warning':
                logger.warning(log_message)
            elif level == 'error':
                logger.error(log_message)
            elif level == 'debug':
                logger.debug(log_message)
        except Exception as e:
            logger.error("Error in log_activity: %s", str(e))
