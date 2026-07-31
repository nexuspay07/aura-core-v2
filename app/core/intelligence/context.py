from pydantic import BaseModel


class AuraExecutionContext(BaseModel):

    goal: str

    organization_id: str | None = None

    workspace_id: str | None = None

    user_id: str | None = None

    executive: dict = {}

    simulation: dict = {}

    response: dict = {}

    shared_memory: dict = {}

    metadata: dict = {}