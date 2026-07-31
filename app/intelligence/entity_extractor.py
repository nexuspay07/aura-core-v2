import re


class EntityExtractor:
    """
    ======================================================

                ENTITY EXTRACTOR

    Purpose

    Convert a natural language question into
    structured business entities.

    This engine DOES NOT answer questions.

    It only understands them.

    ======================================================
    """

    def extract(

        self,

        question: str

    ):

        question_lower = question.lower()

        entities = {

            "question": question,

            "capital": self.extract_capital(question),

            "industry": self.extract_industry(question_lower),

            "intent": self.extract_intent(question_lower),

            "business_stage": self.extract_stage(question_lower),

            "location": self.extract_location(question),

            "timeframe": self.extract_timeframe(question_lower)

        }

        return entities

    # ==========================================
    # CAPITAL
    # ==========================================

    def extract_capital(

        self,

        question

    ):

        matches = re.findall(

            r"\$?\s?(\d+(?:,\d+)*)",

            question

        )

        if not matches:

            return None

        try:

            return int(

                matches[0].replace(",", "")

            )

        except:

            return None

    # ==========================================
    # INDUSTRY
    # ==========================================

    def extract_industry(

        self,

        question

    ):

        industries = {

            "barber": "barbering",

            "salon": "beauty",

            "restaurant": "restaurant",

            "cafe": "restaurant",

            "coffee": "restaurant",

            "software": "software",

            "saas": "software",

            "ai": "artificial_intelligence",

            "trucking": "logistics",

            "transport": "logistics",

            "real estate": "real_estate",

            "property": "real_estate",

            "hospital": "healthcare",

            "clinic": "healthcare",

            "bank": "finance",

            "investment": "finance"

        }

        for keyword, industry in industries.items():

            if keyword in question:

                return industry

        return "general"

    # ==========================================
    # INTENT
    # ==========================================

    def extract_intent(

        self,

        question

    ):

        if any(

            word in question

            for word in [

                "start",

                "open",

                "launch",

                "create"

            ]

        ):

            return "startup"

        if any(

            word in question

            for word in [

                "expand",

                "grow",

                "scale"

            ]

        ):

            return "growth"

        if any(

            word in question

            for word in [

                "buy",

                "purchase",

                "acquire"

            ]

        ):

            return "investment"

        return "general"

    # ==========================================
    # STAGE
    # ==========================================

    def extract_stage(

        self,

        question

    ):

        if any(

            word in question

            for word in [

                "idea",

                "start",

                "open"

            ]

        ):

            return "startup"

        if "expand" in question:

            return "growth"

        return "unknown"

    # ==========================================
    # LOCATION
    # ==========================================

    def extract_location(

        self,

        question

    ):

        locations = [

            "canada",

            "ontario",

            "toronto",

            "brampton",

            "usa",

            "california",

            "new york",

            "cameroon"

        ]

        q = question.lower()

        for location in locations:

            if location in q:

                return location.title()

        return None

    # ==========================================
    # TIMEFRAME
    # ==========================================

    def extract_timeframe(

        self,

        question

    ):

        if "next year" in question:

            return "1_year"

        if "5 years" in question:

            return "5_years"

        if "10 years" in question:

            return "10_years"

        return None


entity_extractor = EntityExtractor()