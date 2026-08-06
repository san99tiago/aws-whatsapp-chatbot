################################################################################
# !!! IMPORTANT !!!
#  This __init__.py allows to load the relevant classes from the State Machine.
#  By importing this file, we leverage "globals" and "getattr" to dynamically
#  execute the Step Function's inner Lambda Functions classes.
################################################################################

# Validation
from state_machine.utils.validate_message import ValidateMessage  # noqa
from state_machine.utils.check_auth import CheckAuth  # noqa

# Processing
from state_machine.processing.process_message import ProcessMessage  # noqa
from state_machine.processing.fetch_audio import FetchAudio  # noqa
from state_machine.processing.transcribe_audio import TranscribeAudio  # noqa
from state_machine.processing.process_image import ProcessImage  # noqa
from state_machine.processing.process_video import ProcessVideo  # noqa
from state_machine.processing.send_response import SendResponse  # noqa

# Utils
from state_machine.utils.success import Success  # noqa
from state_machine.utils.failure import Failure  # noqa
