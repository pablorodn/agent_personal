import asyncio
import json
from pathlib import Path


def _load_cases() -> list[dict]:
    cases_path = Path("evals/faq_cases.json")
    if not cases_path.exists():
        return []
    return json.loads(cases_path.read_text(encoding="utf-8"))


def _score_case(case: dict) -> float:
    # Lightweight deterministic baseline score for CI.
    question = case.get("question", "").strip().lower()
    expected_keywords = case.get("expected_keywords", [])
    if not question or not expected_keywords:
        return 0.0
    simulated_answer = f"Respuesta simulada para: {question}"
    hits = sum(1 for kw in expected_keywords if kw.lower() in simulated_answer)
    return hits / len(expected_keywords)


async def main() -> None:
    print("Running FAQ experiment...")
    cases = _load_cases()
    if not cases:
        print("No cases found at evals/faq_cases.json")
        print("score=0.0")
        return
    scores = [_score_case(case) for case in cases]
    final_score = sum(scores) / len(scores)
    print(f"cases={len(cases)}")
    print(f"score={final_score:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
