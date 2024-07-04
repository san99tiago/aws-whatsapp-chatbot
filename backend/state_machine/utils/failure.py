# Own imports
from common.logger import custom_logger
from state_machine.base_step_function import BaseStepFunction


logger = custom_logger()


class Failure(BaseStepFunction):
    """
    This class contains methods that serve as failure handling at Step Function's
    level.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def process_failure(self):
        """
        Method to finish a failed processed event and log final output.
        """
        self.logger.info("Failure during execution of the event")

        error_message = self.event.get("error_message", "No error message provided")
        self.logger.info(f"Error message: {error_message}")

        # TODO: Add additional failure processing here

        self.event.update({"success": False})

        return self.event
