import base64
import io
import wave

import httpx

from app.domain import Claim
from app.llm.fake import FakeLLM
from app.pipeline.generate import GenerationOut
from app.pipeline.understand import UnderstandOut


def wav(seconds: float) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(8000)
        w.writeframes(b"\x80" * int(8000 * seconds))
    return buffer.getvalue()


def script_answer(llm: FakeLLM) -> None:
    llm.transcript = "Summarize Kanban Board"
    llm.script(
        UnderstandOut(
            intent="project_summary",
            language="en",
            entities=["Kanban Board"],
            asks_for="Kanban summary",
            wants_action=None,
        ),
        GenerationOut(
            claims=[Claim(text="A drag-and-drop task board.", evidence=["E1"])], missing=[]
        ),
    )


async def test_voice_transcribes_and_answers(client: httpx.AsyncClient, fake_llm: FakeLLM) -> None:
    script_answer(fake_llm)
    response = await client.post(
        "/v1/voice", files={"audio": ("q.wav", wav(2), "audio/wav")}, data={"tts": "true"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transcript"] == "Summarize Kanban Board"
    assert body["answer"] == "A drag-and-drop task board."
    assert base64.b64decode(body["audio_b64"]) == b"ID3fake"
    assert body["trace"]["channel"] == "voice"


async def test_voice_tts_failure_still_answers(
    client: httpx.AsyncClient, fake_llm: FakeLLM
) -> None:
    script_answer(fake_llm)
    fake_llm.speech = RuntimeError("tts down")
    response = await client.post(
        "/v1/voice", files={"audio": ("q.wav", wav(2), "audio/wav")}, data={"tts": "true"}
    )
    body = response.json()
    assert body["audio_b64"] is None
    assert any(t["name"] == "tts" and not t["ok"] for t in body["trace"]["tools_called"])


async def test_voice_rejects_too_long_audio_422(client: httpx.AsyncClient) -> None:
    response = await client.post("/v1/voice", files={"audio": ("q.wav", wav(61), "audio/wav")})
    assert response.status_code == 422
    assert "60" in response.json()["detail"]


async def test_voice_rejects_oversized_upload(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/v1/voice", files={"audio": ("q.wav", b"0" * 10_100_000, "audio/wav")}
    )
    assert response.status_code == 413


async def test_voice_rejects_non_audio_422(client: httpx.AsyncClient) -> None:
    response = await client.post("/v1/voice", files={"audio": ("x.txt", b"hello", "text/plain")})
    assert response.status_code == 422


async def test_voice_empty_transcript_422(client: httpx.AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.transcript = "   "
    response = await client.post("/v1/voice", files={"audio": ("q.wav", wav(1), "audio/wav")})
    assert response.status_code == 422
