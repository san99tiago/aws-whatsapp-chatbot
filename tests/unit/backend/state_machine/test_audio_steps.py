################################################################################
# Unit tests for the AUDIO pipeline steps: Fetch Audio (META media download)
# and Transcribe Audio (SYNC Amazon Transcribe job).
################################################################################

# External imports
import boto3
import pytest
from moto import mock_aws


def _build_audio_stream_event(phone_number: str = "573001112233") -> dict:
    """Helper to build a State Machine event for an AUDIO message."""
    return {
        "input": {
            "dynamodb": {
                "NewImage": {
                    "PK": {"S": f"NUMBER#{phone_number}"},
                    "SK": {"S": "MESSAGE#2026-08-05T00:00:00"},
                    "from_number": {"S": phone_number},
                    "type": {"S": "audio"},
                    "audio_id": {"S": "META-MEDIA-ID-123"},
                    "mime_type": {"S": "audio/ogg; codecs=opus"},
                    "correlation_id": {"S": "test-audio-correlation"},
                }
            }
        },
        "message_type": "audio",
        "correlation_id": "test-audio-correlation",
    }


class TestFetchAudio:
    def test_fetch_audio_uploads_to_s3(self, aws_credentials, monkeypatch):
        with mock_aws():
            s3_client = boto3.client("s3", region_name="us-east-1")
            s3_client.create_bucket(Bucket="test-audio-bucket")

            from state_machine.processing import fetch_audio as fetch_audio_module

            monkeypatch.setattr(
                fetch_audio_module, "AUDIO_BUCKET_NAME", "test-audio-bucket"
            )

            # Mock the META API (media metadata + binary download)
            class FakeMetaAPI:
                def __init__(self, logger=None):
                    pass

                def get_media_url(self, media_id):
                    assert media_id == "META-MEDIA-ID-123"
                    return {
                        "url": "https://meta.example.com/media/123",
                        "mime_type": "audio/ogg",
                    }

                def download_media(self, media_url):
                    return b"FAKE-OGG-AUDIO-BYTES"

            monkeypatch.setattr(fetch_audio_module, "MetaAPI", FakeMetaAPI)

            step = fetch_audio_module.FetchAudio(_build_audio_stream_event())
            result = step.fetch_audio()

            assert result["audio_s3_uri"] == (
                "s3://test-audio-bucket/audio/573001112233/"
                "test-audio-correlation.ogg"
            )
            assert result["audio_media_format"] == "ogg"
            stored = s3_client.get_object(
                Bucket="test-audio-bucket",
                Key="audio/573001112233/test-audio-correlation.ogg",
            )
            assert stored["Body"].read() == b"FAKE-OGG-AUDIO-BYTES"

    def test_fetch_audio_without_audio_id_raises(self, aws_credentials):
        from state_machine.processing.fetch_audio import FetchAudio

        event = _build_audio_stream_event()
        del event["input"]["dynamodb"]["NewImage"]["audio_id"]
        with pytest.raises(ValueError):
            FetchAudio(event).fetch_audio()


class TestTranscribeAudio:
    def test_transcribe_audio_sync_job(self, aws_credentials, monkeypatch):
        from state_machine.processing import transcribe_audio as transcribe_module

        # Mock the Transcribe client (SYNC job lifecycle) and transcript fetch
        class FakeTranscribeClient:
            def __init__(self):
                self.calls = 0

            def start_transcription_job(self, **kwargs):
                assert kwargs["Media"]["MediaFileUri"].startswith("s3://")
                assert kwargs["MediaFormat"] == "ogg"

            def get_transcription_job(self, TranscriptionJobName):
                self.calls += 1
                status = "IN_PROGRESS" if self.calls < 2 else "COMPLETED"
                return {
                    "TranscriptionJob": {
                        "TranscriptionJobStatus": status,
                        "Transcript": {
                            "TranscriptFileUri": "https://transcribe.example/job"
                        },
                    }
                }

        class FakeTranscriptResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "results": {
                        "language_code": "es-US",
                        "transcripts": [{"transcript": "Cual es mi saldo?"}],
                    }
                }

        monkeypatch.setattr(
            transcribe_module, "transcribe_client", FakeTranscribeClient()
        )
        monkeypatch.setattr(
            transcribe_module.requests,
            "get",
            lambda url, timeout: FakeTranscriptResponse(),
        )
        monkeypatch.setattr(transcribe_module, "POLL_INTERVAL_SECONDS", 0)

        event = _build_audio_stream_event()
        event["audio_s3_uri"] = "s3://test-audio-bucket/audio/x/y.ogg"
        event["audio_media_format"] = "ogg"

        result = transcribe_module.TranscribeAudio(event).transcribe_audio()
        assert result["transcribed_text"] == "Cual es mi saldo?"
        assert result["transcription_language"] == "es-US"

    def test_transcribe_audio_without_uri_raises(self, aws_credentials):
        from state_machine.processing.transcribe_audio import TranscribeAudio

        with pytest.raises(ValueError):
            TranscribeAudio(_build_audio_stream_event()).transcribe_audio()
