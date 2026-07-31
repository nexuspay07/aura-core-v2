"""
=========================================================

                KNOWLEDGE EXTRACTOR

Extracts structured knowledge from user input.

Currently supports simple fact extraction.

Future versions will integrate the LLM for
entity extraction, relationship extraction,
intent detection, and knowledge graph updates.

=========================================================
"""

import re


class KnowledgeExtractor:

    def extract(self, message: str):

        message = message.lower()

        patterns = [

            ("favorite_food", r"my favorite food is (.+)"),
            ("favorite_color", r"my favorite color is (.+)"),
            ("name", r"my name is (.+)"),
            ("age", r"i am (\d+) years old"),

        ]

        for fact_type, pattern in patterns:

            match = re.search(pattern, message)

            if match:

                return {

                    "type": fact_type,

                    "value": match.group(1).strip()

                }

        return None


knowledge_extractor = KnowledgeExtractor()