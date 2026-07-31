"""
=========================================================

                RESPONSE STATE

Stores all outputs produced during the
Response Pipeline.

Every Response Pipeline engine writes its output
here before the final response is returned.

=========================================================
"""

from pydantic import BaseModel, Field


class ResponseState(BaseModel):
    """
    Response Pipeline State
    """

    synthesis: dict = Field(default_factory=dict)

    advisor: dict = Field(default_factory=dict)

    executive_response: dict = Field(default_factory=dict)

    conversation: dict = Field(default_factory=dict)

    chat: dict = Field(default_factory=dict)

    composed: dict = Field(default_factory=dict)

    standardized: dict = Field(default_factory=dict)

    metadata: dict = Field(default_factory=dict)