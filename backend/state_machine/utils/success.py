# Own imports
from common.logger import custom_logger
from state_machine.base_step_function import BaseStepFunction


logger = custom_logger()


class Success(BaseStepFunction):
    """
    This class contains methods that serve as success handling at Step Function's
    level.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def process_success(self):
        """
        Method to finish a successfully processed event and log final output.
        """
        self.logger.info("Successfully processed the event")

        # TODO: Add additional success processing here

        self.event.update({"success": True})

        return self.event
