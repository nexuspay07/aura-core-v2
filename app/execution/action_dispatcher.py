from typing import Any, Callable, Dict, Optional


class ActionDispatcher:
    """
    Dispatches execution tasks to the appropriate handler.

    Future handlers may include:
    - Email
    - Calendar
    - Slack
    - Stripe
    - Bime
    - NexusPay
    - CRM systems
    - ERP systems
    - Custom plugins
    """

    def __init__(self):

        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    # ==========================================================
    # REGISTRATION
    # ==========================================================

    def register(
        self,
        action: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:

        self._handlers[action] = handler

    # ==========================================================
    # DISPATCH
    # ==========================================================

    def dispatch(
        self,
        task: Dict[str, Any],
    ) -> Dict[str, Any]:

        action = task.get("action")

        if not action:

            return {
                "success": False,
                "error": "Task has no action.",
                "task": task,
            }

        handler = self._handlers.get(action)

        if handler is None:

            return {
                "success": False,
                "error": f"No handler registered for '{action}'.",
                "task": task,
            }

        return handler(task)

    # ==========================================================
    # UTILITIES
    # ==========================================================

    def has_handler(
        self,
        action: str,
    ) -> bool:

        return action in self._handlers

    def available_actions(
        self,
    ) -> list[str]:

        return sorted(self._handlers.keys())


action_dispatcher = ActionDispatcher()