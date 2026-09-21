from app.models.schemas import PlannerOutput
from app.security.tool_permissions import ALLOWED_TOOLS

class PlanValidator:
    @staticmethod
    def validate(plan: PlannerOutput) -> tuple[bool, str]:
        if not plan.execution_stages:
            return False, "Plan has no execution stages."
            
        expected_stage_number = 1
        for stage in plan.execution_stages:
            if stage.stage_number != expected_stage_number:
                return False, f"Stage numbers are not sequential. Expected {expected_stage_number}, got {stage.stage_number}."
            
            if not stage.allowed_tools:
                return False, f"Stage {stage.stage_number} has no allowed tools."
                
            for tool in stage.allowed_tools:
                if tool not in ALLOWED_TOOLS:
                    return False, f"Stage {stage.stage_number} requests unknown/blocked tool: '{tool}'."
                    
            expected_stage_number += 1
            
        return True, "Plan is valid."
