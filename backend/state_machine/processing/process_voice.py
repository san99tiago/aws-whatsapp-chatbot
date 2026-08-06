# Own imports
from state_machine.base_step_function import BaseStepFunction
from common.logger import custom_logger


logger = custom_logger()


class ProcessVoice(BaseStepFunction):
    """
    This class contains methods for the "voice processing" of the State Machine.
    TBD: voice-to-text conversion (e.g. Amazon Transcribe) before Agent invocation.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def process_voice(self):
        """
        Method to process the voice input message (TBD placeholder).
        """
        self.logger.info("Starting process_voice for the chatbot (TBD)")

        # TODO: Add real voice to text conversion here (Amazon Transcribe)...
        self.event["response_message"] = (
            "🚧 Aún no puedo procesar mensajes de voz. "
            "Por favor envía tu mensaje como texto."
        )
        return self.event
