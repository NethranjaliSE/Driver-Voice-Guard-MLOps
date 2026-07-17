"""
Q&A chat — lets a user ask follow-up questions about their emotion prediction.
Backed by the Hugging Face Inference API.
"""

import os
from typing import Dict

from huggingface_hub import InferenceClient
from huggingface_hub.errors import GatedRepoError, HfHubHTTPError
from loguru import logger

MODEL = "meta-llama/Llama-3.1-8B-Instruct"
MAX_TOKENS = 500

SYSTEM_PROMPT = """You are the explainability assistant for a Speech Emotion \
Recognition (SER) system. The system extracts MFCC, Chroma, and Mel \
Spectrogram features from a short voice recording and classifies it into one \
of four emotions — calm, happy, fearful, disgust — using an MLPClassifier \
trained on the RAVDESS dataset.

You will be told the prediction the system made for the user's specific \
recording (the predicted emotion, its confidence, and the per-emotion score \
breakdown). Answer the user's question about that result. Explain what the \
scores mean, why a model might land on that emotion, and what could cause \
misclassification (background noise, short clips, atypical speaking style, \
overlap between acoustically similar emotions). Keep answers conversational \
and under 150 words unless the user asks for more detail. You do not have \
access to the audio itself — only the prediction shown to you."""


class ChatUnavailableError(RuntimeError):
    """Raised when the Q&A feature can't run (e.g. missing token)."""


def _get_client() -> InferenceClient:
    token = os.getenv("HF_TOKEN")
    if not token:
        raise ChatUnavailableError(
            "HF_TOKEN is not set. Add it to your .env to enable the "
            "'ask about this result' feature."
        )
    return InferenceClient(model=MODEL, token=token)


def ask_about_result(
    question: str,
    emotion: str,
    confidence: float,
    all_scores: Dict[str, float],
) -> str:
    """Answer a user question about one prediction result."""
    client = _get_client()

    scores_text = ", ".join(f"{label}: {score}%" for label, score in all_scores.items())
    context = (
        f"Predicted emotion: {emotion}\n"
        f"Confidence: {confidence}%\n"
        f"Per-emotion scores: {scores_text}\n\n"
        f"User question: {question}"
    )

    try:
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            max_tokens=MAX_TOKENS,
        )
    except GatedRepoError as e:
        logger.error(f"Hugging Face gated model access error: {e}")
        raise ChatUnavailableError(
            f"AI assistant is unavailable: your HF account hasn't accepted the "
            f"license for {MODEL} yet. Visit https://huggingface.co/{MODEL} "
            f"and click 'Agree and access repository'."
        ) from e
    except HfHubHTTPError as e:
        logger.error(f"Hugging Face Inference API error: {e}")
        raise ChatUnavailableError(f"AI assistant is unavailable: {e}") from e

    return response.choices[0].message.content or ""
