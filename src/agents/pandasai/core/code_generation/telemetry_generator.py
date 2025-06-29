"""Enhanced code generator with comprehensive telemetry for MCP visibility."""

import traceback
import time
from typing import Optional, Dict, Any

from pandasai.agent.state import AgentState
from pandasai.core.prompts.base import BasePrompt

from .code_cleaning import CodeCleaner
from .code_validation import CodeRequirementValidator
from .base import CodeGenerator
from agents.pandasai.helpers.telemetry_logger import TelemetryLogger
from config.telemetry_logger import logger as mcp_logger


class TelemetryCodeGenerator(CodeGenerator):
    """Code generator with enhanced telemetry for thinking process visibility."""
    
    def __init__(self, context: AgentState):
        """Initialize with telemetry logger."""
        super().__init__(context)
        
        # Replace logger with telemetry-enabled version if needed
        if not isinstance(context.logger, TelemetryLogger):
            self._original_logger = context.logger
            context.logger = TelemetryLogger(
                save_logs=getattr(context.logger, '_save_logs', True),
                verbose=getattr(context.logger, '_verbose', False)
            )
        
        self._telemetry_logger = context.logger
        
    def generate_code(self, prompt: BasePrompt) -> str:
        """Generate code with comprehensive telemetry tracking."""
        generation_start = time.time()
        prompt_str = prompt.to_string()
        
        # Set context for all subsequent logs
        self._telemetry_logger.set_context(
            conversation_id=self._context.prompt_id,
            phase="code_generation"
        )
        
        try:
            # Log thinking process start
            mcp_logger.info(
                "pandasai_thinking_process",
                event_type="thinking_start",
                phase="code_generation",
                prompt_type=prompt.__class__.__name__,
                prompt_length=len(prompt_str),
                conversation_id=self._context.prompt_id
            )
            
            # Log prompt details
            self._telemetry_logger.log_prompt(prompt_str, prompt_type=prompt.__class__.__name__)
            
            # Analyze prompt for thinking visibility
            self._log_prompt_analysis(prompt)
            
            # Generate the code with thinking steps
            mcp_logger.info(
                "llm_invocation_started",
                event_type="thinking_step",
                step="calling_llm",
                description="Sending prompt to LLM for code generation"
            )
            
            code = self._context.config.llm.generate_code(prompt, self._context)
            self._context.last_code_generated = code
            
            generation_time = time.time() - generation_start
            
            # Log generated code with analysis
            self._log_code_analysis(code, generation_time)
            
            # Validate and clean with telemetry
            cleaned_code = self._validate_and_clean_with_telemetry(code)
            
            # Log thinking process completion
            total_time = time.time() - generation_start
            mcp_logger.info(
                "pandasai_thinking_completed",
                event_type="thinking_end",
                phase="code_generation",
                total_duration_ms=total_time * 1000,
                generation_time_ms=generation_time * 1000,
                original_code_length=len(code),
                cleaned_code_length=len(cleaned_code),
                conversation_id=self._context.prompt_id
            )
            
            return cleaned_code
            
        except Exception as e:
            error_message = f"An error occurred during code generation: {e}"
            stack_trace = traceback.format_exc()
            
            # Log error with full context
            mcp_logger.error(
                "code_generation_failed",
                event_type="thinking_error",
                phase="code_generation",
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=stack_trace,
                duration_ms=(time.time() - generation_start) * 1000,
                conversation_id=self._context.prompt_id
            )
            
            self._telemetry_logger.log_error(error_message)
            self._telemetry_logger.log(f"Stack Trace:\n{stack_trace}")
            
            raise e
        finally:
            # Clear context
            self._telemetry_logger.clear_context()
            
    def _log_prompt_analysis(self, prompt: BasePrompt):
        """Analyze and log prompt details for thinking visibility."""
        prompt_str = prompt.to_string()
        
        # Extract key components from prompt
        analysis = {
            "has_dataframe_info": "dataframe" in prompt_str.lower(),
            "has_memory_context": hasattr(self._context, 'memory') and len(self._context.memory) > 0,
            "has_error_context": "error" in prompt_str.lower() or "exception" in prompt_str.lower(),
            "has_retry_context": "retry" in prompt_str.lower() or "correct" in prompt_str.lower(),
        }
        
        # Log thinking steps
        if analysis["has_dataframe_info"]:
            self._telemetry_logger.log_thinking_step(
                "analyzing_dataframes",
                "Understanding available dataframes and their schemas"
            )
            
        if analysis["has_memory_context"]:
            self._telemetry_logger.log_thinking_step(
                "reviewing_conversation_history",
                f"Considering {len(self._context.memory)} previous interactions"
            )
            
        if analysis["has_error_context"]:
            self._telemetry_logger.log_thinking_step(
                "analyzing_error",
                "Understanding previous error to generate corrected code"
            )
            
        if analysis["has_retry_context"]:
            self._telemetry_logger.log_thinking_step(
                "applying_corrections",
                "Generating improved code based on error feedback"
            )
            
        # Log prompt analysis summary
        mcp_logger.info(
            "prompt_analysis_complete",
            event_type="thinking_step",
            step="prompt_analyzed",
            **analysis
        )
        
    def _log_code_analysis(self, code: str, generation_time: float):
        """Analyze and log generated code for visibility."""
        # Basic code analysis
        lines = code.strip().split('\n')
        imports = [line for line in lines if line.strip().startswith('import') or line.strip().startswith('from')]
        functions = [line for line in lines if 'def ' in line]
        dataframe_ops = [line for line in lines if 'df' in line.lower() or 'dataframe' in line.lower()]
        
        analysis = {
            "total_lines": len(lines),
            "import_count": len(imports),
            "function_count": len(functions),
            "dataframe_operations": len(dataframe_ops),
            "has_sql": "execute_sql_query" in code or "sql" in code.lower(),
            "has_visualization": any(viz in code.lower() for viz in ['plot', 'chart', 'graph', 'visualize']),
            "has_aggregation": any(agg in code for agg in ['groupby', 'agg', 'sum', 'mean', 'count']),
            "generation_time_ms": generation_time * 1000
        }
        
        # Log code characteristics
        self._telemetry_logger.log_code(code, phase="generated")
        
        # Log thinking steps based on code content
        if analysis["has_sql"]:
            self._telemetry_logger.log_thinking_step(
                "sql_generation",
                "Generated SQL query for data extraction"
            )
            
        if analysis["has_visualization"]:
            self._telemetry_logger.log_thinking_step(
                "visualization_setup",
                "Preparing data visualization"
            )
            
        if analysis["has_aggregation"]:
            self._telemetry_logger.log_thinking_step(
                "data_aggregation",
                "Setting up data aggregation operations"
            )
            
        # Log analysis summary
        mcp_logger.info(
            "code_analysis_complete",
            event_type="thinking_step",
            step="code_analyzed",
            **analysis
        )
        
    def _validate_and_clean_with_telemetry(self, code: str) -> str:
        """Validate and clean code with telemetry tracking."""
        validation_start = time.time()
        
        # Validate code requirements
        self._telemetry_logger.log_thinking_step(
            "code_validation",
            "Checking code requirements and safety"
        )
        
        mcp_logger.info(
            "code_validation_started",
            event_type="thinking_step",
            step="validating_code"
        )
        
        if not self._code_validator.validate(code):
            mcp_logger.error(
                "code_validation_failed",
                event_type="validation_error",
                reason="Code requirements not met"
            )
            raise ValueError("Code validation failed due to unmet requirements.")
            
        validation_time = time.time() - validation_start
        
        mcp_logger.info(
            "code_validation_completed",
            event_type="thinking_step",
            step="validation_complete",
            duration_ms=validation_time * 1000
        )
        
        # Clean the code
        cleaning_start = time.time()
        
        self._telemetry_logger.log_thinking_step(
            "code_cleaning",
            "Removing unnecessary elements and formatting code"
        )
        
        cleaned_code = self._code_cleaner.clean_code(code)
        
        cleaning_time = time.time() - cleaning_start
        
        # Log cleaning results
        mcp_logger.info(
            "code_cleaning_completed",
            event_type="thinking_step", 
            step="cleaning_complete",
            duration_ms=cleaning_time * 1000,
            chars_removed=len(code) - len(cleaned_code),
            lines_before=len(code.split('\n')),
            lines_after=len(cleaned_code.split('\n'))
        )
        
        return cleaned_code