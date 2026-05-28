from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import datetime

router = APIRouter(
    prefix="/phase110",
    tags=["Phase 110 — Autonomous Multi-Instance Coordination Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class InstanceStatus(BaseModel):
    instance_id: str
    cpu_usage: float
    memory_usage: float
    active_tasks: int
    online: bool

class Phase110Input(BaseModel):
    global_mission: str
    instances_status: List[InstanceStatus]


# ---------------------------
# Output Models
# ---------------------------

class CoordinationResult(BaseModel):
    instance_id: str
    assigned_tasks: int
    load_after_coordination: float
    status: str

class Phase110Output(BaseModel):
    message: str
    coordination_results: List[CoordinationResult]
    global_coordination_efficiency: float
    timestamp: str


# ---------------------------
# Coordination Engine
# ---------------------------

class MultiInstanceCoordinationEngine:

    def coordinate_instance(self, instance: InstanceStatus):
        if not instance.online:
            status = "OFFLINE"
            assigned_tasks = 0
        else:
            # Assign tasks proportionally based on load
            avg_usage = (instance.cpu_usage + instance.memory_usage) / 2
            assigned_tasks = max(int(instance.active_tasks * (1 - avg_usage)), 0)
            status = "ONLINE"

        load_after = round((instance.cpu_usage + instance.memory_usage) / 2, 3)

        return CoordinationResult(
            instance_id=instance.instance_id,
            assigned_tasks=assigned_tasks,
            load_after_coordination=load_after,
            status=status
        )

    def run_coordination(self, instances: List[InstanceStatus]):
        results = []
        total_efficiency = 0
        active_count = 0

        for instance in instances:
            result = self.coordinate_instance(instance)
            results.append(result)
            if result.status == "ONLINE":
                total_efficiency += (1 - result.load_after_coordination)
                active_count += 1

        global_efficiency = round(total_efficiency / active_count, 3) if active_count else 0
        return results, global_efficiency


engine = MultiInstanceCoordinationEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/coordinate", response_model=Phase110Output)
def coordinate_instances(data: Phase110Input):
    results, efficiency = engine.run_coordination(data.instances_status)

    return Phase110Output(
        message="Phase 110 multi-instance coordination complete",
        coordination_results=results,
        global_coordination_efficiency=efficiency,
        timestamp=str(datetime.datetime.now())
    )