#!/usr/bin/env python3
"""
agent/tools/speech_in.py · voice-to-text via Granite-Speech-4.1-2B-NAR.

Reference: https://huggingface.co/ibm-granite/granite-speech-4.1-2b-nar

Constraints:
  - Audio must be 16 kHz mono · resampling + channel-averaging done internally
  - Output is plain text · no confidences · no word timings
  - Auto-detects language · 5 supported (EN/FR/DE/ES/PT) · no target-lang arg
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import torch
import torchaudio

GRANITE_SPEECH = os.environ.get("GRANITE_SPEECH", "/home/smash/granite/granite-speech-4.1-2b-nar")

# Lazy load · model held in module scope after first call
_MODEL = None
_FX = None


def _ensure_loaded():
    global _MODEL, _FX
    if _MODEL is None:
        from transformers import AutoFeatureExtractor, AutoModel
        _FX = AutoFeatureExtractor.from_pretrained(GRANITE_SPEECH, trust_remote_code=True)
        _MODEL = AutoModel.from_pretrained(
            GRANITE_SPEECH,
            trust_remote_code=True,
            attn_implementation="flash_attention_2",
            device_map="cuda:0",
            dtype=torch.bfloat16,
        ).eval()
    return _MODEL, _FX


def transcribe(audio_path: str | Path) -> str:
    """Synchronous voice-to-text · returns plain transcript."""
    model, fx = _ensure_loaded()

    wav, sr = torchaudio.load(str(audio_path))
    if sr != 16000:
        wav = torchaudio.functional.resample(wav, sr, 16000)
    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    wav = wav.squeeze(0)

    inputs = fx([wav], device="cuda:0")
    out = model.generate(**inputs)
    return out.text_preds[0]


class SpeechInTool:
    name = "speech_in"
    description = (
        "Transcribe an audio file (wav/mp3/m4a) to plain text using Granite-Speech-4.1-2B. "
        "Auto-detects language. No confidences or timings. Returns transcript string."
    )

    def run(self, audio_path: str) -> str:
        return transcribe(audio_path)
