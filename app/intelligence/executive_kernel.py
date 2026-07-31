from app.intelligence.entity_extractor import (
    entity_extractor
)

from app.intelligence.context_retriever import (
    context_retriever
)

from app.intelligence.analysis_router import (
    analysis_router
)


class ExecutiveKernel:
    """
    =====================================================

                EXECUTIVE KERNEL

    The Executive Kernel is Aura's CPU.

    It coordinates the entire thinking process.

    It DOES NOT perform intelligence.

    It coordinates intelligence.

    =====================================================
    """

    def process(

        self,

        question: str,

        user_context: dict | None = None

    ):

        # -----------------------------------
        # STEP 1
        # Understand the question
        # -----------------------------------

        entities = (

            entity_extractor.extract(

                question

            )

        )

        # -----------------------------------
        # STEP 2
        # Retrieve Context
        # -----------------------------------

        context = (

            context_retriever.retrieve(

                entities,

                user_context

            )

        )

        # -----------------------------------
        # STEP 3
        # Decide which engines to execute
        # -----------------------------------

        execution_plan = (

            analysis_router.build_plan(

                entities,

                context

            )

        )

        return {

            "question": question,

            "entities": entities,

            "context": context,

            "execution_plan": execution_plan

        }


executive_kernel = ExecutiveKernel()