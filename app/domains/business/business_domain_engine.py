class BusinessDomainEngine:
    def __init__(self):
        self.subdomains = {
            "growth": [
                "grow", "growth", "scale", "scaling", "customers",
                "revenue", "expand", "expansion"
            ],
            "pricing": [
                "price", "pricing", "charge", "cost", "subscription",
                "monthly fee", "sell for", "how much"
            ],
            "hiring": [
                "hire", "hiring", "employee", "staff", "team",
                "recruit", "worker"
            ],
            "market_entry": [
                "market", "competition", "competitor", "enter market",
                "competitive", "launch", "positioning"
            ],
            "cost_control": [
                "reduce cost", "cut cost", "expenses", "save money",
                "lower expenses", "burn rate"
            ],
            "customer_acquisition": [
                "get customers", "find customers", "clients",
                "users", "leads", "sales", "marketing"
            ],
        }

    def detect_subdomain(self, message: str) -> str:
        m = message.lower()

        for subdomain, keywords in self.subdomains.items():
            if any(keyword in m for keyword in keywords):
                return subdomain

        return "general_business"

    def detect_business_intent(self, message: str) -> str:
        """
        Business Intelligence V2 intent detection.
        This gives AURA a more practical business decision category.
        """
        m = message.lower()

        if any(x in m for x in ["price", "pricing", "charge", "subscription", "how much"]):
            return "pricing"

        if any(x in m for x in ["grow", "growth", "scale", "expand", "revenue"]):
            return "growth"

        if any(x in m for x in ["cost", "expenses", "save money", "burn rate", "reduce cost"]):
            return "cost"

        if any(x in m for x in ["customer", "customers", "clients", "users", "leads", "sales", "marketing"]):
            return "acquisition"

        if any(x in m for x in ["hire", "hiring", "employee", "staff", "team", "recruit"]):
            return "hiring"

        if any(x in m for x in ["market", "competition", "competitor", "launch", "positioning"]):
            return "market_entry"

        return "general"

    def build_business_context(self, subdomain: str) -> dict:
        if subdomain == "growth":
            return {
                "focus": "customer acquisition, retention, revenue expansion, and sustainable scaling",
                "risk_bias": "balanced",
                "recommended_frame": "medium-term"
            }

        if subdomain == "pricing":
            return {
                "focus": "value capture, affordability, margins, and customer conversion",
                "risk_bias": "balanced",
                "recommended_frame": "short-term"
            }

        if subdomain == "hiring":
            return {
                "focus": "team capacity, burn control, role prioritization, and efficiency",
                "risk_bias": "low",
                "recommended_frame": "medium-term"
            }

        if subdomain == "market_entry":
            return {
                "focus": "positioning, timing, competition, and differentiation",
                "risk_bias": "balanced",
                "recommended_frame": "medium-term"
            }

        if subdomain == "cost_control":
            return {
                "focus": "expense control, operational efficiency, cash preservation, and profitability",
                "risk_bias": "low",
                "recommended_frame": "short-term"
            }

        if subdomain == "customer_acquisition":
            return {
                "focus": "lead generation, customer targeting, sales channels, and conversion",
                "risk_bias": "balanced",
                "recommended_frame": "short-term"
            }

        return {
            "focus": "general business optimization",
            "risk_bias": "balanced",
            "recommended_frame": "medium-term"
        }

    def build_business_advice(self, subdomain: str, best_strategy: dict) -> str:
        strategy_name = best_strategy.get("name", "Balanced")

        if subdomain == "growth":
            return (
                f"For growth, AURA prefers a {strategy_name.lower()} path that improves expansion "
                f"without losing control of execution."
            )

        if subdomain == "pricing":
            return (
                f"For pricing, AURA recommends a {strategy_name.lower()} approach that balances "
                f"customer adoption with revenue quality."
            )

        if subdomain == "hiring":
            return (
                f"For hiring, AURA recommends a {strategy_name.lower()} approach so you expand team "
                f"capacity without creating unnecessary burn."
            )

        if subdomain == "market_entry":
            return (
                f"For market entry, AURA recommends a {strategy_name.lower()} approach that balances "
                f"speed with competitive survival."
            )

        if subdomain == "cost_control":
            return (
                f"For cost control, AURA recommends a {strategy_name.lower()} approach that protects cash "
                f"while keeping the business functional."
            )

        if subdomain == "customer_acquisition":
            return (
                f"For customer acquisition, AURA recommends a {strategy_name.lower()} approach that focuses "
                f"on finding the right customers before scaling spend."
            )

        return (
            f"For general business decisions, AURA recommends a {strategy_name.lower()} strategy "
            f"as the most practical option."
        )


business_domain_engine = BusinessDomainEngine()