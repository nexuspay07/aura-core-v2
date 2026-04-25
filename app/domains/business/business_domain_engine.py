class BusinessDomainEngine:
    def __init__(self):
        self.subdomains = {
            "growth": ["grow", "growth", "scale", "customers", "revenue", "expand"],
            "pricing": ["price", "pricing", "charge", "cost", "subscription"],
            "hiring": ["hire", "hiring", "employee", "staff", "team", "recruit"],
            "market_entry": ["market", "competition", "enter market", "competitive", "launch"],
        }

    def detect_subdomain(self, message: str) -> str:
        m = message.lower()

        for subdomain, keywords in self.subdomains.items():
            if any(keyword in m for keyword in keywords):
                return subdomain

        return "general_business"

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

        return (
            f"For general business decisions, AURA recommends a {strategy_name.lower()} strategy "
            f"as the most practical option."
        )


business_domain_engine = BusinessDomainEngine()