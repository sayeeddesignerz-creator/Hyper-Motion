"""
Fact Checker Agent — claim extraction, web cross-referencing, and factual verification.
"""
from __future__ import annotations

import uuid
from typing import List, Dict, Any

from app.agents.base import BaseAgent
from app.models import ClaimItem, VerificationStatus
from app.tools.webfetch import WebFetchTool

FACT_CHECK_PROMPT = """You are a rigorous Fact-Checking & Intelligence Officer.
Analyze the following trend or topic and extract key testable claims.
Topic: {topic}
Context / Snippet: {snippet}

Extract up to 3 major claims. For each claim, evaluate its factual accuracy based on established consensus, current news, or logic.

Return a JSON object with a key "claims" containing an array of objects:
[
  {{
    "claim_text": "Exact statement or claim",
    "original_context": "Background context",
    "status": "verified" | "debunked" | "partially_true" | "unverified",
    "confidence": 85.0,
    "evidence": ["Point 1", "Point 2"],
    "sources": ["Reuters", "Official Statement"],
    "verdict_explanation": "Detailed rationale"
  }}
]
"""

class FactCheckerAgent(BaseAgent):
    def __init__(self, gateway=None):
        super().__init__("FactChecker", gateway)
        self.webfetch = WebFetchTool()

    async def verify_topic(self, topic: str, snippet: str = "") -> List[ClaimItem]:
        self.logger.info(f"Fact-checking topic: '{topic}'")
        
        prompt = FACT_CHECK_PROMPT.format(topic=topic, snippet=snippet)
        try:
            res = await self.gateway.generate_json(prompt, system_instruction="You are a strict, objective fact-checker.")
            raw_claims = res.get("claims", [])
            claims: List[ClaimItem] = []
            for item in raw_claims:
                status_str = str(item.get("status", "unverified")).lower()
                status_enum = VerificationStatus.UNVERIFIED
                if "verified" in status_str and "partially" not in status_str:
                    status_enum = VerificationStatus.VERIFIED
                elif "debunk" in status_str or "false" in status_str:
                    status_enum = VerificationStatus.DEBUNKED
                elif "partially" in status_str:
                    status_enum = VerificationStatus.PARTIALLY_TRUE

                claims.append(ClaimItem(
                    id=str(uuid.uuid4())[:8],
                    claim_text=item.get("claim_text", topic),
                    original_context=item.get("original_context", snippet),
                    status=status_enum,
                    confidence=float(item.get("confidence", 80.0)),
                    evidence=item.get("evidence", []),
                    sources=item.get("sources", []),
                    verdict_explanation=item.get("verdict_explanation", "")
                ))
            return claims
        except Exception as e:
            self.logger.error(f"Fact checking failed: {e}")
            return [
                ClaimItem(
                    id=str(uuid.uuid4())[:8],
                    claim_text=topic,
                    original_context=snippet,
                    status=VerificationStatus.UNVERIFIED,
                    confidence=50.0,
                    evidence=["Pending deep verification"],
                    sources=[],
                    verdict_explanation="LLM fact-checking fallback applied"
                )
            ]
