"""
Strategic Document Enforcement - response_stream_end hook
Validates strategic document responses and triggers FAIL_CLOSED if necessary.
"""
from python.helpers.extension import Extension
from python.helpers.print_style import PrintStyle
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent import Agent, LoopData


class StrategicEnforcementResponseHook(Extension):
    """
    Validates strategic document responses during response_stream_end.
    Triggers FAIL_CLOSED if sourcing requirements are not met.
    """
    
    async def execute(self, loop_data: "LoopData" = None, **kwargs):
        """Execute the strategic validation hook."""
        from python.extensions.strategic_validation._10_strategic_enforcement import (
            StrategicEnforcementExtension
        )
        
        ext = StrategicEnforcementExtension(agent=self.agent)
        await ext.response_stream_end(
            agent=self.agent,
            loop_data=loop_data,
            **kwargs
        )
