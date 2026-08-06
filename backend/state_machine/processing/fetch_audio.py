################################################################################
# "Fetch Audio" step: FETCHES the audio media from META using the <audio_id>
# received in the WhatsApp webhook (media metadata -> short-lived URL ->
# binary download) and stores it in S3 for the Transcribe step.
################################################################################

# Built-in imports
import os

# External imports
import boto3

# Own imports
from state_machine.base_step_function import BaseStepFunction
from state_machine.integrations.meta.api_requests import MetaAPI
from common.logger import custom_logger


logger = custom_logger()

AUDIO_BUCKET_NAME = os.environ.get("AUDIO_BUCKET_NAME", "")

s3_client = boto3.client("s3")

# Map of common META audio MIME types to file extensions
MIME_TYPE_EXTENSIONS = {
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "mp4",
    "audio/amr": "amr",
    "audio/webm": "webm",
}


class FetchAudio(BaseStepFunction):
    """
    This class contains methods to FETCH the audio media from META (by media
    ID) and upload it to S3 (input for the Transcribe SYNC job).
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def fetch_audio(self):
        """
        Method to fetch the audio binary from META and upload it to S3.
        """
        self.logger.info("Starting fetch_audio (META media download)")

        new_image = self.event.get("input", {}).get("dynamodb", {}).get("NewImage", {})
        audio_id = new_image.get("audio_id", {}).get("S", "")
        phone_number = new_image.get("from_number", {}).get("S", "UNKNOWN")
        if not audio_id:
            raise ValueError("No <audio_id> found in the message (cannot fetch audio)")

        # STEP 1: Fetch the media metadata (short-lived download URL) from META
        self.logger.info(f"STEP 1/3: Fetching media URL for audio_id={audio_id}")
        meta_api = MetaAPI(logger=self.logger)
        media_info = meta_api.get_media_url(audio_id)
        media_url = media_info["url"]
        mime_type = media_info.get("mime_type", "audio/ogg").split(";")[0].strip()
        self.logger.info(f"Media URL fetched successfully (mime_type: {mime_type})")

        # STEP 2: Download the audio binary content
        self.logger.info("STEP 2/3: Downloading audio binary content")
        audio_content = meta_api.download_media(media_url)
        self.logger.info(f"Audio downloaded successfully ({len(audio_content)} bytes)")

        # STEP 3: Upload the audio to S3 (input for the Transcribe job)
        extension = MIME_TYPE_EXTENSIONS.get(mime_type, "ogg")
        s3_key = f"audio/{phone_number}/{self.correlation_id}.{extension}"
        self.logger.info(
            f"STEP 3/3: Uploading audio to s3://{AUDIO_BUCKET_NAME}/{s3_key}"
        )
        s3_client.put_object(
            Bucket=AUDIO_BUCKET_NAME,
            Key=s3_key,
            Body=audio_content,
            ContentType=mime_type,
        )
        self.logger.info("Audio uploaded to S3 successfully")

        # Enrich the event for the next step (Transcribe Audio)
        self.event["audio_s3_uri"] = f"s3://{AUDIO_BUCKET_NAME}/{s3_key}"
        self.event["audio_media_format"] = extension
        self.event["audio_mime_type"] = mime_type

        return self.event
