# Own imports
from state_machine.base_step_function import BaseStepFunction
from common.logger import custom_logger


logger = custom_logger()


class ProcessImage(BaseStepFunction):
    """
    This class contains methods for the "image processing" of the State Machine.
    TBD: image understanding (e.g. Bedrock multimodal) before Agent invocation.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def process_image(self):
        """
        Method to process the image input message (TBD placeholder).
        """
        self.logger.info("Starting process_image for the chatbot (TBD)")

        # TODO: Add real image processing here (Bedrock multimodal models)...
        self.event["response_message"] = (
            "🚧 Aún no puedo procesar imágenes. "
            "Por favor envía tu mensaje como texto."
        )
        return self.event
