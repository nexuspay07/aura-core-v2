from .base_domain import BaseDomain


class HealthcareDomain(BaseDomain):
    """
    Healthcare-safe domain wrapper for Aura.
    Educational, non-diagnostic, non-prescriptive.
    """

    def validate(self, user_input: str) -> None:
        if not user_input or len(user_input.strip()) == 0:
            raise ValueError("Healthcare input cannot be empty.")

    def shape_prompt(self, user_input: str) -> str:
        system_context = """
You are Aura Healthcare Assistant.
Provide general educational health information only.
Do not diagnose.
Do not prescribe medication or dosage.
Encourage professional medical care when symptoms may be serious.
Be calm, clear, and safety-oriented.
        """

        return f"{system_context}\n\nUser Query:\n{user_input}"

    def post_process(self, response: str) -> str:
        disclaimer = (
            "\n\n⚠️ This information is for educational purposes only and does not replace "
            "professional medical advice."
        )

        if "educational purposes" not in response.lower():
            response += disclaimer

        return response


healthcare_domain = HealthcareDomain()