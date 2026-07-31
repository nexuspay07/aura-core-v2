from typing import Dict, List


class ThoughtChain:
    """
    Evaluates a sequence of planned steps and assigns
    reasoning metadata to each one.
    """

    DEFAULT_CONFIDENCE = 0.80

    def evaluate(
        self,
        steps: List[str],
    ) -> List[Dict]:

        return [
            self._evaluate_step(step, index)
            for index, step in enumerate(steps)
        ]

    def _evaluate_step(
        self,
        step: str,
        index: int,
    ) -> Dict:
        """
        Evaluate a single reasoning step.
        """

        return {
            "order": index + 1,
            "step": step,
            "confidence": self.DEFAULT_CONFIDENCE,
            "status": "pending",
        }


thought_chain = ThoughtChain()