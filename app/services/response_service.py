class ResponseService:
    """
    =========================================================

                    RESPONSE SERVICE

    Converts raw Aura intelligence output into a
    standardized API response.

    Responsibilities

    • Normalize AI output
    • Hide engine implementation details
    • Maintain response contract

    This service MUST NOT contain any AI logic.

    =========================================================
    """

    def build_response(

        self,

        *,

        pipeline_result: dict,

        organization_name: str | None = None,

        workspace_name: str | None = None,

        session_id: str | None = None,

        profile: dict | None = None,

        memory_count: int = 0

    ) -> dict:

        executive_response = (
            pipeline_result.get(
                "executive_response"
            )
            or {}
        )

        executive_synthesis = (
            pipeline_result.get(
                "executive_synthesis"
            )
            or {}
        )

        final_response = (
            pipeline_result.get(
                "final_response"
            )
            or {}
        )

        standardized_output = (
            pipeline_result.get(
                "standardized_output"
            )
            or {}
        )

        executive_advisor = (
            pipeline_result.get(
                "executive_advisor"
            )
            or {}
        )

        conversational_response = (
            pipeline_result.get(
                "conversational_response"
            )
            or {}
        )

        chat_response = (
            pipeline_result.get(
                "chat_response"
            )
            or {}
        )

        conversation_history = (
            pipeline_result.get(
                "conversation_history"
            )
            or []
        )

        return {

            "success": True,

            "session_id": session_id,

            "organization": organization_name,

            "workspace": workspace_name,

            "profile": profile,

            "memory_count": memory_count,

            "chat_response": chat_response,

            "executive_advisor":
                executive_advisor,

            "conversational_response":
                conversational_response,

            "standardized_output":
                standardized_output,

            "executive_response":
                executive_response,

            "executive_synthesis":
                executive_synthesis,

            "final_response":
                final_response,

            "conversation_history":
                conversation_history,

            "pipeline":
                pipeline_result

        }


response_service = ResponseService()