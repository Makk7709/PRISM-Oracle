"""
Legal-Safe Pipeline Integration - monologue_start hook
Executes legal pipeline and sets short-circuit flags to bypass LLM.
"""
from python.helpers.extension import Extension
from python.helpers.print_style import PrintStyle
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent import Agent, LoopData


class LegalSafePipelineHook(Extension):
    """
    Executes the legal pipeline during monologue_start.
    If successful, sets _pipeline_final_response to bypass LLM.
    """
    
    async def execute(self, loop_data: "LoopData" = None, **kwargs):
        """Execute the legal pipeline hook."""
        # DEBUG: Log that we're being called
        PrintStyle(font_color="cyan", bold=True).print(
            "🔧 DEBUG: LegalSafePipelineHook.execute() CALLED"
        )
        
        from python.extensions.legal_safe_mode._10_legal_safe_integration import (
            LegalSafeModeExtension
        )
        
        ext = LegalSafeModeExtension(agent=self.agent)
        await ext.monologue_start(
            agent=self.agent,
            loop_data=loop_data,
            **kwargs
        )
        
        # DEBUG: Check if flags were set
        flag = self.agent.get_data("_pipeline_final_response")
        skip = self.agent.get_data("_skip_llm")
        PrintStyle(font_color="cyan", bold=True).print(
            f"🔧 DEBUG: After monologue_start - _pipeline_final_response={flag is not None}, _skip_llm={skip}"
        )
