################################################################################
# "Transcribe Audio" step: runs a SYNC Amazon Transcribe job over the audio
# stored in S3 (by the "Fetch Audio" step), waits for completion (polling with
# detailed logs), and passes the transcribed TEXT to the "Process Message"
# step (which re-utilizes it as the Agent's prompt).
################################################################################

# Built-in imports
import json
import time

# External imports
import boto3
import requests

# Own imports
from state_machine.base_step_function import BaseStepFunction
from common.logger import custom_logger


logger = custom_logger()

transcribe_client = boto3.client("transcribe")

# SYNC polling configurations (voice notes are short, jobs finish in seconds)
POLL_INTERVAL_SECONDS = 2
MAX_WAIT_SECONDS = 180

# Formats supported by Amazon Transcribe for the WhatsApp audio types
SUPPORTED_MEDIA_FORMATS = ["ogg", "mp3", "mp4", "amr", "webm", "wav", "flac"]


class TranscribeAudio(BaseStepFunction):
    """
    This class contains methods to run the SYNC Amazon Transcribe job that
    converts the WhatsApp audio (voice note / MP3) into text.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def transcribe_audio(self):
        """
        Method to transcribe the audio (SYNC job with polling) and enrich the
        event with the <transcribed_text> for the next Process Message step.
        """
        self.logger.info("Starting transcribe_audio (Amazon Transcribe SYNC job)")

        audio_s3_uri = self.event.get("audio_s3_uri", "")
        media_format = self.event.get("audio_media_format", "ogg")
        if not audio_s3_uri:
            raise ValueError("No <audio_s3_uri> in event (Fetch Audio must run first)")
        if media_format not in SUPPORTED_MEDIA_FORMATS:
            self.logger.warning(
                f"Media format <{media_format}> not supported, defaulting to ogg"
            )
            media_format = "ogg"

        # STEP 1: Start the transcription job (unique name per execution)
        job_name = f"wpp-audio-{self.correlation_id}-{int(time.time())}"
        self.logger.info(
            f"STEP 1/3: Starting Transcribe job <{job_name}> "
            f"for {audio_s3_uri} (format: {media_format})"
        )
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": audio_s3_uri},
            MediaFormat=media_format,
            IdentifyLanguage=True,
            LanguageOptions=["es-US", "en-US"],
        )

        # STEP 2: SYNC wait (polling) until the job completes
        self.logger.info("STEP 2/3: Waiting for the Transcribe job (SYNC polling)")
        elapsed_seconds = 0
        job_status = "IN_PROGRESS"
        transcript_uri = ""
        while elapsed_seconds < MAX_WAIT_SECONDS:
            job = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )["TranscriptionJob"]
            job_status = job["TranscriptionJobStatus"]
            self.logger.info(
                f"Transcribe job <{job_name}> status: {job_status} "
                f"(elapsed: {elapsed_seconds}s)"
            )
            if job_status == "COMPLETED":
                transcript_uri = job["Transcript"]["TranscriptFileUri"]
                break
            if job_status == "FAILED":
                failure_reason = job.get("FailureReason", "Unknown")
                raise RuntimeError(f"Transcribe job FAILED: {failure_reason}")
            time.sleep(POLL_INTERVAL_SECONDS)
            elapsed_seconds += POLL_INTERVAL_SECONDS

        if job_status != "COMPLETED":
            raise TimeoutError(
                f"Transcribe job <{job_name}> did not complete in {MAX_WAIT_SECONDS}s"
            )

        # STEP 3: Fetch the transcript JSON (pre-signed URI) and extract the text
        self.logger.info("STEP 3/3: Fetching the transcript result")
        transcript_response = requests.get(transcript_uri, timeout=30)
        transcript_response.raise_for_status()
        transcript_json = transcript_response.json()
        transcribed_text = (
            transcript_json.get("results", {})
            .get("transcripts", [{}])[0]
            .get("transcript", "")
        )
        language_code = transcript_json.get("results", {}).get("language_code", "")
        self.logger.info(
            f"Audio transcribed successfully (language: {language_code}): "
            f"{transcribed_text}"
        )

        if not transcribed_text:
            self.logger.warning("Empty transcription (silence or unsupported audio)")
            transcribed_text = (
                "(El usuario envio un audio que no se pudo transcribir. "
                "Pidele amablemente que lo intente de nuevo o escriba su mensaje.)"
            )

        # Enrich the event: Process Message RE-UTILIZES this text as the prompt
        self.event["transcribed_text"] = transcribed_text
        self.event["transcription_language"] = language_code
        self.event["transcription_job_name"] = job_name

        return self.event
