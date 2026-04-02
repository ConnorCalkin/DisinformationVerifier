"""
This module contains all classes that are used in the backed. Including structured output classes.
"""

from pydantic import BaseModel

class Claim:
    """
    This class represents a claim that has been extracted from the users input
    """

    def __init__(self, claim_text: str, category: str = None):
        self.claim_text = claim_text
        self.category = category


class RatedClaim(BaseModel):
    claim: str
    rating: str
    explanation: str
    sources: list[str]


class RatedClaimResponse(BaseModel):
    rated_claims: list[RatedClaim]


class UnratedClaimResponse(BaseModel):
    summary: str
    claims: list[str]
