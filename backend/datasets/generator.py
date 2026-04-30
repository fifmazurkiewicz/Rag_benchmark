from __future__ import annotations
import json
import pathlib
import uuid
from typing import Literal
import anthropic

DATASETS_DIR = pathlib.Path("datasets_store")
DATASETS_DIR.mkdir(exist_ok=True)

_SYSTEM = """You are a QA dataset generator. Given a text passage, generate {n} question-answer pairs.
Each pair must be answerable solely from the passage.
Return a JSON array: [{{"question": "...", "answer": "..."}}]
Return ONLY the JSON array, no other text."""

DomainType = Literal["financial", "football", "volleyball", "neurology", "custom"]


def generate_qa_pairs(text: str, n: int = 5, model: str = "claude-haiku-4-5-20251001") -> list[dict]:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=_SYSTEM.format(n=n),
        messages=[{"role": "user", "content": text}],
    )
    raw = response.content[0].text.strip()
    import re
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    return json.loads(match.group()) if match else []


def build_dataset(
    name: str,
    documents: list[dict],
    qa_per_doc: int = 5,
    llm_model: str = "claude-haiku-4-5-20251001",
) -> pathlib.Path:
    """
    Build and save a dataset JSON from a list of {id, text, metadata} dicts.
    Generates QA pairs for each document using Claude.
    """
    all_qa: list[dict] = []
    for doc in documents:
        pairs = generate_qa_pairs(doc["text"], n=qa_per_doc, model=llm_model)
        for p in pairs:
            p["doc_id"] = doc["id"]
        all_qa.extend(pairs)

    dataset = {"documents": documents, "qa_pairs": all_qa}
    path = DATASETS_DIR / f"{name}.json"
    path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))
    return path


DOMAIN_SAMPLES: dict[DomainType, list[dict]] = {
    "football": [
        {
            "id": "football_001",
            "text": (
                "Robert Lewandowski is a Polish professional footballer who plays as a striker for "
                "FC Barcelona and the Poland national team. Born on August 21, 1988, in Warsaw, "
                "he is widely regarded as one of the best strikers of his generation. "
                "He won the FIFA Best Men's Player award in 2020 and 2021. "
                "He joined Bayern Munich in 2014 and scored 344 goals in 375 appearances before "
                "moving to FC Barcelona in 2022."
            ),
            "metadata": {"domain": "football", "topic": "player_profile"},
        }
    ],
    "volleyball": [
        {
            "id": "volleyball_001",
            "text": (
                "Wilfredo León is a Cuban-born Polish professional volleyball player who plays as "
                "an outside hitter. Born on July 31, 1993 in Santiago de Cuba, he is considered "
                "one of the best volleyball players in the world. He has been playing for the "
                "Polish national team since obtaining Polish citizenship in 2018. "
                "He plays for Sir Sicoma Monini Perugia in the Italian Serie A1."
            ),
            "metadata": {"domain": "volleyball", "topic": "player_profile"},
        }
    ],
    "neurology": [
        {
            "id": "neurology_001",
            "text": (
                "Multiple sclerosis (MS) is a chronic inflammatory demyelinating disease of the "
                "central nervous system. It affects approximately 2.8 million people worldwide. "
                "The disease is characterized by episodes of neurological dysfunction caused by "
                "demyelination and axonal damage. Common symptoms include fatigue, difficulty "
                "walking, numbness, muscle spasms, and vision problems. "
                "Disease-modifying therapies (DMTs) such as interferon beta, glatiramer acetate, "
                "and natalizumab can reduce relapse rates and slow progression."
            ),
            "metadata": {"domain": "neurology", "topic": "disease_overview"},
        }
    ],
    "financial": [
        {
            "id": "financial_001",
            "text": (
                "The Warsaw Stock Exchange (WSE), known in Polish as Giełda Papierów Wartościowych "
                "w Warszawie (GPW), is the largest stock exchange in Central and Eastern Europe. "
                "Founded in 1991 after the fall of communism, it lists over 400 companies with a "
                "total market capitalization exceeding 300 billion PLN. "
                "The main index is the WIG20, which tracks the 20 largest and most liquid companies. "
                "Foreign investors account for approximately 50% of trading volume."
            ),
            "metadata": {"domain": "financial", "topic": "market_overview"},
        }
    ],
}
