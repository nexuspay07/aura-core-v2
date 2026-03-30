# app/core/system_router.py

from app.core.system_decision import execute_decision, execute_evolution

def run_system():
    """
    Main system loop for Phase 184.
    Executes decision and evolves strategies.
    """
    decision_result = execute_decision()

    if decision_result.get('status') == 'decision_executed':
        # Find executed strategy in registry
        strategy_name = decision_result['strategy_used']
        strategy = next(
            (s for s in strategy_registry if s.get('name') == strategy_name),
            None
        )
        if strategy:
            execute_evolution(strategy)

    return decision_result