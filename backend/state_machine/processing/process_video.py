# Own imports
from state_machine.base_step_function import BaseStepFunction
from common.logger import custom_logger


logger = custom_logger()


class ProcessVideo(BaseStepFunction):
    """
    This class contains methods for the "video processing" of the State Machine.
    TBD: video understanding before Agent invocation.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def process_video(self):
        """
        Method to process the video input message (TBD placeholder).
        """
        self.logger.info("Starting process_video for the chatbot (TBD)")

        # TODO: Add real video processing here...
        self.event["response_message"] = (
            "🚧 Aún no puedo procesar videos. " "Por favor envía tu mensaje como texto."
        )
        return self.event
