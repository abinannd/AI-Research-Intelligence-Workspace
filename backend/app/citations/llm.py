from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

from app.citations.prompts import SYSTEM_PROMPT, build_user_prompt
from app.config import Settings
from app.retrieval.qdrant_store import RetrievedChunk


class LLMService(ABC):
    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @abstractmethod
    def complete(self, system: str, user: str) -> str: ...


class StubLLMService(LLMService):
    def __init__(self) -> None:
        self._chunks: list[RetrievedChunk] = []

    @property
    def model_version(self) -> str:
        return "stub-llm"

    def complete(self, system: str, user: str) -> str:
        if "(no evidence retrieved)" in user:
            return json.dumps(
                {
                    "abstain": True,
                    "abstain_reason": "No retrieved evidence",
                    "answer": "The sources do not answer this.",
                    "claims": [],
                }
            )
        return json.dumps(
            {
                "abstain": False,
                "abstain_reason": None,
                "answer": "Based on the evidence [1].",
                "claims": [{"claim_text": "The evidence addresses the question.", "citation_indexes": [1]}],
            }
        )


class HuggingFaceLLMService(LLMService):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

    @property
    def model_version(self) -> str:
        return self.model_name

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float32,
            device_map="cpu",
        )

    def complete(self, system: str, user: str) -> str:
        self._load()
        assert self._model is not None and self._tokenizer is not None
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._tokenizer(prompt, return_tensors="pt")
        output_ids = self._model.generate(
            **inputs,
            max_new_tokens=700,
            do_sample=False,
            pad_token_id=self._tokenizer.eos_token_id,
        )
        generated = output_ids[0][inputs["input_ids"].shape[-1] :]
        return self._tokenizer.decode(generated, skip_special_tokens=True)


def build_llm(settings: Settings) -> LLMService:
    if settings.llm_backend == "hf":
        return HuggingFaceLLMService(settings.llm_model)
    return StubLLMService()


def extract_json(text: str) -> dict:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    raise ValueError("Model did not return JSON")


def format_evidence(chunks: list[RetrievedChunk]) -> list[str]:
    blocks: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        heading = f" heading={chunk.heading}" if chunk.heading else ""
        blocks.append(
            f"[{i}] doc={chunk.filename} page={chunk.page_number} chunk_id={chunk.chunk_id}{heading}\n{chunk.text}"
        )
    return blocks


def run_llm(llm: LLMService, question: str, chunks: list[RetrievedChunk]) -> dict:
    user = build_user_prompt(question, format_evidence(chunks))
    raw = llm.complete(SYSTEM_PROMPT, user)
    return extract_json(raw)
