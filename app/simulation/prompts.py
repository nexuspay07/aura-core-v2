"""Provider instructions for canonical Strategy Stress Tests."""

SIMULATION_SYSTEM_PROMPT = """You are performing an Aevric Strategy Stress Test. Analyze the supplied Strategy only under the supplied explicit scenarios. Do not predict which scenario will occur, assign numerical probability, claim calibrated forecasting, or claim certainty. Do not invent evidence or rewrite trusted Strategy facts. Do not choose, optimize, or mutate the Strategy. Do not create new scenarios. Do not create phases, constraints, assumptions, or change conditions and present them as trusted source material. Use SOURCE only for exact supplied Strategy material, USER_SUPPLIED only for exact supplied user assumptions, MODEL_GENERATED for new analytical observations, and DERIVED for transparent comparisons or consequences. Make each scenario analysis specific to its changed conditions. Return only the requested structured analytical output."""


def simulation_repair_instruction(*, category: str, codes: tuple[str, ...]) -> str:
    """Return deterministic repair guidance using privacy-safe diagnostics only."""

    safe_codes = ",".join(sorted(set(codes))) or "none"
    return (
        " Repair the previous response once. Preserve the exact schema and supplied scenario set. "
        f"Failure category: {category}. Safe codes: {safe_codes}. "
        "Return complete scenario-specific analysis with valid source references, no invented "
        "evidence, no numerical predictive claims, no certainty claims, and no extra fields."
    )
