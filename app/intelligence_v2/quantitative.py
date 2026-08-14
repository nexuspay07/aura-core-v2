"""Explicit deterministic calculations available to V2 evidence assembly."""

from decimal import Decimal, ROUND_HALF_UP
import re

from app.intelligence_v2.contracts import DecisionType, DerivedEvidence, EvidenceItem, EvidenceSourceType


def delivery_cost_reduction_target(evidence: list[EvidenceItem], reduction_percent: str | None) -> dict[str, str]:
    """Return a target only when both a persisted baseline and requested percent exist."""
    if not reduction_percent:
        return {}
    percentage = Decimal(reduction_percent.rstrip("%"))
    for item in evidence:
        content = item.content or ""
        match = re.search(r"\$\s*(\d+(?:\.\d+)?)\s*(?:per|/)\s*(?:order|delivery)", content, re.I)
        if match:
            baseline = Decimal(match.group(1))
            target = (baseline * (Decimal("1") - percentage / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return {"delivery_cost_baseline": f"{baseline:.2f}", "delivery_cost_target": f"{target:.2f}", "unit": "per order", "method": "baseline * (1 - reduction_percent / 100)"}
    return {}


def personal_job_offer_derived_evidence(evidence: list[EvidenceItem]) -> list[DerivedEvidence]:
    """Create only arithmetic facts whose complete operands are user evidence."""
    result: list[DerivedEvidence] = []
    for item in evidence:
        if item.source_type is not EvidenceSourceType.USER_STATEMENT or not item.content:
            continue
        text = item.content
        offer_a = re.search(r"offer\s+a(?:\s+pays)?\s*:?(?:\s*-)?\s*\$\s*([\d,]+)", text, re.I)
        offer_b = re.search(r"offer\s+b(?:\s+pays)?\s*:?(?:\s*-)?\s*\$\s*([\d,]+)", text, re.I)
        if offer_a and offer_b:
            a, b = (Decimal(match.group(1).replace(",", "")) for match in (offer_a, offer_b))
            difference = abs(b - a).quantize(Decimal("1"))
            result.append(DerivedEvidence("derived:annual_salary_difference", f"Offer B pays ${difference:,.0f} more annually.", f"{a:.0f} - {b:.0f} = {difference:.0f}" if a > b else f"{b:.0f} - {a:.0f} = {difference:.0f}", [item.id], [f"{difference:.0f}"], "difference", {"offer_a":f"{a:.0f}","offer_b":f"{b:.0f}"}, "USD/year", "annual_salary_difference", "career compensation comparison"))
        commute = re.search(r"(\d+)\s*-?minute\s+commute\s+each\s+way", text, re.I)
        if commute:
            one_way = Decimal(commute.group(1)); minutes = one_way * 2
            hours = minutes / Decimal("60")
            hours_text = f"{hours.normalize():g} hours" if hours == hours.to_integral() else f"{hours.normalize():g} hours"
            result.append(DerivedEvidence("derived:commute_per_day", f"The commute is {minutes:.0f} minutes ({hours_text}) per commuting day.", f"{one_way:.0f} + {one_way:.0f} = {minutes:.0f} minutes", [item.id], [f"{minutes:.0f}", f"{hours.normalize():g}"], "addition", {"one_way_minutes":f"{one_way:.0f}"}, "minutes per commuting day", "commute_per_day", "career lifestyle comparison"))
    return result


def major_purchase_derived_evidence(evidence: list[EvidenceItem]) -> list[DerivedEvidence]:
    """Compute only explicit cash-flow and stated-constraint arithmetic."""
    result=[]
    for item in evidence:
        if item.source_type is not EvidenceSourceType.USER_STATEMENT or not item.content:
            continue
        text=item.content
        def amount(pattern):
            match=re.search(pattern,text,re.I|re.S)
            value=next((group for group in match.groups() if group is not None),None) if match else None
            return Decimal(value.replace(",","")) if value else None
        savings=amount(r"\$\s*([\d,]+)\s+in\s+savings")
        income=amount(r"(?:earn|income(?:\s+is)?)\s+\$\s*([\d,]+)\s+(?:per\s+month|monthly)")
        expenses=amount(r"(?:regular\s+monthly\s+expenses|monthly\s+expenses|regular\s+expenses|expenses\s+(?:are|of)).*?\$\s*([\d,]+)")
        purchase=amount(r"(?:buying|buy|purchase|spend).*?(?:car|vehicle).*?(?:for|costs?|at)\s+\$\s*([\d,]+)")
        if purchase is None:
            purchase=amount(r"(?:spend|pay)\s+\$\s*([\d,]+)\s+(?:in\s+cash\s+)?(?:on|for)\s+(?:a\s+)?(?:used\s+)?(?:car|vehicle)")
        if purchase is None:
            purchase=amount(r"(?:car|vehicle).*?(?:price|cost)\s+(?:is|of)?\s*\$\s*([\d,]+)")
        emergency=amount(r"at\s+least\s+\$\s*([\d,]+)\s+in\s+emergency\s+savings")
        def derived(identifier,claim,calculation,values,label,relevance,unit="USD"):
            result.append(DerivedEvidence(identifier,claim,calculation,[item.id],[f"{value:.0f}" for value in values.values()],"subtraction",{name:f"{value:.0f}" for name,value in values.items()},unit,label,relevance))
        if income is not None and expenses is not None:
            surplus=income-expenses; derived("derived:monthly_surplus",f"Current monthly surplus is ${surplus:,.0f} per month.",f"{income:.0f} - {expenses:.0f} = {surplus:.0f}",{"income":income,"expenses":expenses,"surplus":surplus},"monthly_surplus","major purchase affordability","USD/month")
        after=None
        if savings is not None and purchase is not None:
            after=savings-purchase; derived("derived:savings_after_purchase",f"Savings after a cash purchase would be ${after:,.0f}.",f"{savings:.0f} - {purchase:.0f} = {after:.0f}",{"savings":savings,"purchase":purchase,"remaining":after},"savings_after_purchase","emergency reserve impact")
        if emergency is not None and after is not None:
            gap=emergency-after; derived("derived:emergency_savings_gap",f"The purchase would leave savings ${gap:,.0f} below the stated emergency-savings goal.",f"{emergency:.0f} - {after:.0f} = {gap:.0f}",{"emergency_goal":emergency,"after_purchase":after,"gap":gap},"emergency_savings_constraint_gap","stated financial constraint")
    return result


def education_derived_evidence(evidence: list[EvidenceItem]) -> list[DerivedEvidence]:
    """Derive total stated tuition only; employment income is not assumed lost."""
    result=[]
    for item in evidence:
        if item.source_type is not EvidenceSourceType.USER_STATEMENT or not item.content:
            continue
        text=item.content
        years=re.search(r"\b(\d+)\s*[- ]?year\s+(?:college\s+)?program\b",text,re.I)
        annual=re.search(r"(?:costs?|tuition(?:\s+is)?)\s+\$\s*([\d,]+)\s+per\s+year",text,re.I)
        if years and annual:
            duration=Decimal(years.group(1)); yearly=Decimal(annual.group(1).replace(",","")); total=duration*yearly
            result.append(DerivedEvidence("derived:total_stated_tuition",f"Stated tuition totals ${total:,.0f} across the {duration:.0f}-year program.",f"{duration:.0f} * {yearly:.0f} = {total:.0f}",[item.id],[f"{duration:.0f}",f"{yearly:.0f}",f"{total:.0f}"],"multiplication",{"program_years":f"{duration:.0f}","annual_tuition":f"{yearly:.0f}","total_tuition":f"{total:.0f}"},"USD","total_stated_tuition","education cost comparison"))
    return result


def derive_decision_evidence(evidence: list[EvidenceItem], decision_type: DecisionType) -> list[DerivedEvidence]:
    if decision_type is DecisionType.CAREER_DECISION:
        return personal_job_offer_derived_evidence(evidence)
    if decision_type in {DecisionType.MAJOR_PURCHASE,DecisionType.PERSONAL_FINANCE}:
        return major_purchase_derived_evidence(evidence)
    if decision_type is DecisionType.EDUCATION_DECISION:
        return education_derived_evidence(evidence)
    return []


def derived_evidence_items(items: list[DerivedEvidence], *, organization_id: int, workspace_id: int) -> list[EvidenceItem]:
    return [EvidenceItem(id=item.id, source_type=EvidenceSourceType.OPERATIONAL_DATA, source_name="aura_deterministic_quantitative", content=item.claim, structured_value={"operation":item.operation,"calculation":item.calculation,"source_values":item.source_values,"numeric_values":item.numeric_values,"unit":item.unit,"semantic_label":item.semantic_label,"decision_relevance":item.decision_relevance}, organization_id=organization_id, workspace_id=workspace_id, permission_scope="derived", citation_label="Aura deterministic calculation", provenance={"derived":True,"operation":item.operation,"source_evidence_ids":item.source_evidence_ids,"source_values":item.source_values,"calculation":item.calculation,"numeric_values":item.numeric_values,"unit":item.unit,"semantic_label":item.semantic_label,"decision_relevance":item.decision_relevance}) for item in items]
