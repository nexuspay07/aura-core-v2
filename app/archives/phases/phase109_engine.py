from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import datetime
import uuid

router = APIRouter(
    prefix="/phase109",
    tags=["Phase 109 — Autonomous Intelligence Scaling Engine"]
)

# ---------------------------
# Input Models
# ---------------------------

class InstanceLoadInput(BaseModel):
    instance_id: str
    cpu_usage: float
    memory_usage: float
    active_tasks: int


class Phase109Input(BaseModel):
    global_mission: str
    current_instances: List[InstanceLoadInput]
    scaling_threshold: float


# ---------------------------
# Output Models
# ---------------------------

class ScalingDecision(BaseModel):
    instance_id: str
    action: str
    new_instance_id: Optional[str] = None  # <-- FIXED to allow None
    load_after_scaling: float


class Phase109Output(BaseModel):
    message: str
    scaling_decisions: List[ScalingDecision]
    total_instances_after_scaling: int
    global_scaling_efficiency: float
    timestamp: str


# ---------------------------
# Scaling Engine
# ---------------------------

class IntelligenceScalingEngine:

    def calculate_load(self, instance: InstanceLoadInput):
        return (instance.cpu_usage + instance.memory_usage) / 2

    def evaluate_instance(self, instance: InstanceLoadInput, threshold: float):
        load = self.calculate_load(instance)

        if load > threshold:
            new_instance_id = str(uuid.uuid4())
            reduced_load = round(load / 2, 3)
            return ScalingDecision(
                instance_id=instance.instance_id,
                action="SCALED",
                new_instance_id=new_instance_id,
                load_after_scaling=reduced_load
            )
        else:
            return ScalingDecision(
                instance_id=instance.instance_id,
                action="NO_ACTION",
                new_instance_id=None,  # now allowed
                load_after_scaling=round(load, 3)
            )

    def scale_system(self, instances: List[InstanceLoadInput], threshold: float):
        decisions = []
        total_load = 0
        new_instances = 0

        for instance in instances:
            decision = self.evaluate_instance(instance, threshold)
            decisions.append(decision)
            total_load += decision.load_after_scaling
            if decision.action == "SCALED":
                new_instances += 1

        total_instances = len(instances) + new_instances
        avg_load = total_load / total_instances if total_instances else 0
        scaling_efficiency = round(1 - avg_load, 3)

        return decisions, total_instances, scaling_efficiency


engine = IntelligenceScalingEngine()


# ---------------------------
# API Endpoint
# ---------------------------

@router.post("/scale", response_model=Phase109Output)
def scale_intelligence(data: Phase109Input):
    decisions, total_instances, efficiency = engine.scale_system(
        data.current_instances,
        data.scaling_threshold
    )

    return Phase109Output(
        message="Phase 109 autonomous intelligence scaling complete",
        scaling_decisions=decisions,
        total_instances_after_scaling=total_instances,
        global_scaling_efficiency=efficiency,
        timestamp=str(datetime.datetime.now())
    )