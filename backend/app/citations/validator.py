from __future__ import annotations

from dataclasses import dataclass

from app.retrieval.qdrant_store import RetrievedChunk


@dataclass
class ValidatedClaim:
    claim_text: str
    support_status: str
    citation_indexes: list[int]


def validate_model_output(parsed: dict, retrieved: list[RetrievedChunk]) -> tuple[bool, str | None, str, list[ValidatedClaim]]:
    allowed = set(range(1, len(retrieved) + 1))
    abstain = bool(parsed.get("abstain"))
    reason = parsed.get("abstain_reason")
    answer = str(parsed.get("answer") or "").strip()
    raw_claims = parsed.get("claims") or []
    validated: list[ValidatedClaim] = []

    if not retrieved:
        return True, "No retrieved evidence in this workspace", "The sources do not answer this.", []

    if abstain:
        return True, str(reason or "Insufficient evidence"), answer or "The sources do not answer this.", []

    if not isinstance(raw_claims, list) or not raw_claims:
        return True, "Model did not produce citable claims", answer or "The sources do not answer this.", []

    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        text = str(item.get("claim_text") or "").strip()
        indexes = item.get("citation_indexes") or item.get("citation_ids") or []
        nums: list[int] = []
        if isinstance(indexes, list):
            for n in indexes:
                try:
                    nums.append(int(n))
                except (TypeError, ValueError):
                    continue
        valid_nums = [n for n in nums if n in allowed]
        if not text:
            continue
        if valid_nums:
            status = "supported"
        else:
            status = "unsupported"
        validated.append(ValidatedClaim(claim_text=text, support_status=status, citation_indexes=valid_nums))

    if not validated:
        return True, "No valid claims after citation checks", answer or "The sources do not answer this.", []

    if all(c.support_status == "unsupported" for c in validated):
        return True, "Citations were not in the retrieved set", answer or "The sources do not answer this.", validated

    return False, None, answer, validated
