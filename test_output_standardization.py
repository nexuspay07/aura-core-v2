from app.core.output_standardization_engine import (
    output_standardization_engine
)

executive_response = {
    "executive_summary":
        "Healthcare clinics should improve profitability by improving patient retention.",
    "key_findings": [
        "Market opportunity is strong.",
        "Customer trust is critical."
    ],
    "recommendations": [
        "Improve patient retention.",
        "Optimize staff utilization."
    ],
    "risks": [
        "Operational inefficiency."
    ],
    "next_steps": [
        "Review workflows",
        "Increase patient follow-ups"
    ]
}

strategic_simulation = {
    "30_day_projection":
        "Validate demand and improve operations.",

    "90_day_projection":
        "Scale after proving profitability."
}

operational_intelligence = {
    "recommended_operational_move":
        "Standardize patient onboarding."
}

dynamic_reasoning = {
    "strategic_warning":
        "Growing too quickly could reduce service quality."
}

result = output_standardization_engine.standardize(
    executive_response,
    strategic_simulation,
    operational_intelligence,
    dynamic_reasoning
)

print("\n========== STANDARDIZED OUTPUT ==========\n")
print(result)
print("\n=========================================\n")