"""Provider instructions for canonical Strategy Stress Tests."""

SIMULATION_SYSTEM_PROMPT = """You are performing an Aevric Strategy Stress Test. Analyze the supplied Strategy only under the supplied explicit scenarios. Return concise, complete, qualitative findings and avoid repetition. Use no more findings than needed to communicate the material result, and return an empty array for every optional section that is not applicable. Do not predict which scenario will occur, assign numerical probability, claim calibrated forecasting, or claim certainty. Do not invent evidence or rewrite trusted Strategy facts. Do not choose, optimize, or mutate the Strategy. Do not create new scenarios. Do not create phases, constraints, assumptions, or change conditions and present them as trusted source material. Use SOURCE only for exact supplied Strategy material, USER_SUPPLIED only for exact supplied user assumptions, MODEL_GENERATED for new analytical observations, and DERIVED for transparent comparisons or consequences. Make each scenario analysis specific to its changed conditions. Return only the requested structured analytical output."""


_QUALITY_REPAIRS = {
    "simulation.assumption_provenance": "Use SOURCE and USER_SUPPLIED only for exact supplied text; otherwise use MODEL_GENERATED or DERIVED.",
    "simulation.cross_scenario_comparison": "For multiple scenarios, provide a distinct qualitative comparison rather than repeating scenario text.",
    "simulation.duplicate_finding": "Remove repeated findings from each collection.",
    "simulation.forecast_claim": "Describe plausible qualitative effects without claiming a calibrated forecast.",
    "simulation.invalid_finding_provenance": "Use SOURCE and USER_SUPPLIED only for exact supplied text; otherwise use MODEL_GENERATED or DERIVED.",
    "simulation.numeric_probability": "Remove numerical probabilities and likelihood percentages.",
    "simulation.predictive_certainty": "Replace certainty claims with bounded qualitative language.",
    "simulation.scenario_coverage": "Return each supplied scenario exactly once and no additional scenarios.",
    "simulation.scenario_repetition": "Make required findings specific to each scenario's changed conditions.",
    "simulation.unsupported_evidence": "Use only evidence identifiers supplied in the request.",
}


def simulation_repair_instruction(*, category: str, codes: tuple[str, ...]) -> str:
    """Return deterministic repair guidance using privacy-safe diagnostics only."""

    normalized_codes = tuple(sorted(set(codes)))
    safe_codes = ",".join(normalized_codes) or "none"
    guidance = " ".join(_QUALITY_REPAIRS[code] for code in normalized_codes if code in _QUALITY_REPAIRS)
    return (
        " Generate one corrected replacement response. Preserve the exact schema and supplied scenario set. "
        f"Failure category: {category}. Safe codes: {safe_codes}. "
        f"{guidance} "
        "Return complete scenario-specific analysis with valid source references, no invented "
        "evidence, no numerical predictive claims, no certainty claims, no repetition, and no extra fields. "
        "Use concise complete statements and empty arrays for nonapplicable optional sections."
    )
