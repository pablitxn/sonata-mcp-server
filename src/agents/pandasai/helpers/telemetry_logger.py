"""Telemetry-enabled logger for PandasAI that integrates with MCP logging."""

import io
import time
from typing import Any, List, Optional, TextIO, Union
from pathlib import Path

from .logger import Logger as PandasAILogger
from config.telemetry_logger import logger as mcp_logger


class TelemetryLogger(PandasAILogger):
    """Enhanced PandasAI logger that sends logs through MCP telemetry."""
    
    def __init__(
        self,
        save_logs: bool = True,
        logs_filename: str = "pandasai.log",
        verbose: bool = False
    ):
        """Initialize telemetry logger."""
        super().__init__(save_logs, logs_filename, verbose)
        self._context = {}
        self._thinking_buffer = []
        self._code_generation_buffer = []
        
    def set_context(self, **kwargs):
        """Set context that will be included in all log messages."""
        self._context.update(kwargs)
        
    def clear_context(self):
        """Clear the logging context."""
        self._context = {}
    
    def log(self, message: str) -> None:
        """Log a message with MCP telemetry integration."""
        # Call parent implementation
        super().log(message)
        
        # Determine log type and phase based on message content
        event_type = self._determine_event_type(message)
        log_data = {
            "event_type": event_type,
            "message": message,
            "timestamp": time.time(),
            **self._context
        }
        
        # Buffer thinking process messages
        if self._is_thinking_message(message):
            self._thinking_buffer.append(message)
            log_data["thinking_phase"] = True
            
        # Buffer code generation messages
        if self._is_code_generation_message(message):
            self._code_generation_buffer.append(message)
            log_data["code_generation_phase"] = True
        
        # Send to MCP logger
        if self._verbose or event_type in ["error", "warning", "code_generated", "execution_result"]:
            mcp_logger.info("pandasai_log", **log_data)
            
        # Flush thinking buffer when complete
        if "completed" in message.lower() and self._thinking_buffer:
            self._flush_thinking_buffer()
            
    def log_error(self, message: str) -> None:
        """Log an error message."""
        super().log(f"Error: {message}")
        
        mcp_logger.error(
            "pandasai_error",
            event_type="error",
            message=message,
            **self._context
        )
        
    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        super().log(f"Warning: {message}")
        
        mcp_logger.warning(
            "pandasai_warning",
            event_type="warning",
            message=message,
            **self._context
        )
        
    def log_dataframe_info(self, name: str, df: Any) -> None:
        """Log dataframe information."""
        info_msg = f"Dataframe '{name}' loaded: {df.shape[0]} rows x {df.shape[1]} columns"
        self.log(info_msg)
        
        mcp_logger.info(
            "pandasai_dataframe_loaded",
            event_type="dataframe_info",
            dataframe_name=name,
            rows=df.shape[0],
            columns=df.shape[1],
            column_names=list(df.columns) if hasattr(df, 'columns') else [],
            **self._context
        )
        
    def log_prompt(self, prompt: str, prompt_type: str = "unknown") -> None:
        """Log a prompt sent to the LLM."""
        self.log(f"Prompt ({prompt_type}): {prompt[:200]}...")
        
        mcp_logger.info(
            "pandasai_prompt",
            event_type="prompt_generated",
            prompt_type=prompt_type,
            prompt_length=len(prompt),
            prompt_preview=prompt[:500] + "..." if len(prompt) > 500 else prompt,
            **self._context
        )
        
    def log_code(self, code: str, phase: str = "generated") -> None:
        """Log generated or executed code."""
        self.log(f"Code {phase}: {code[:200]}...")
        
        mcp_logger.info(
            "pandasai_code",
            event_type=f"code_{phase}",
            code_length=len(code),
            code_snippet=code[:500] + "..." if len(code) > 500 else code,
            full_code=code,
            **self._context
        )
        
    def log_execution_start(self, code: str) -> None:
        """Log the start of code execution."""
        self.log("Starting code execution...")
        
        mcp_logger.info(
            "pandasai_execution_start",
            event_type="execution_started",
            code_preview=code[:200] + "..." if len(code) > 200 else code,
            **self._context
        )
        
    def log_execution_result(self, result: Any, execution_time: float) -> None:
        """Log execution result."""
        self.log(f"Execution completed in {execution_time:.2f}s")
        
        result_type = type(result).__name__
        result_preview = str(result)[:500] if result is not None else "None"
        
        mcp_logger.info(
            "pandasai_execution_result",
            event_type="execution_completed",
            result_type=result_type,
            result_preview=result_preview,
            execution_time_ms=execution_time * 1000,
            **self._context
        )
        
    def log_thinking_start(self, query: str) -> None:
        """Log the start of the thinking process."""
        self._thinking_buffer = []
        self.log(f"Starting to process query: {query}")
        
        mcp_logger.info(
            "pandasai_thinking_start",
            event_type="thinking_started",
            query=query,
            **self._context
        )
        
    def log_thinking_step(self, step: str, details: Optional[str] = None) -> None:
        """Log a thinking step."""
        msg = f"Thinking step: {step}"
        if details:
            msg += f" - {details}"
        self.log(msg)
        self._thinking_buffer.append({"step": step, "details": details})
        
    def _flush_thinking_buffer(self) -> None:
        """Flush the thinking buffer to telemetry."""
        if self._thinking_buffer:
            mcp_logger.info(
                "pandasai_thinking_process",
                event_type="thinking_summary",
                steps=self._thinking_buffer,
                total_steps=len(self._thinking_buffer),
                **self._context
            )
            self._thinking_buffer = []
            
    def _determine_event_type(self, message: str) -> str:
        """Determine event type from message content."""
        message_lower = message.lower()
        
        if "error" in message_lower:
            return "error"
        elif "warning" in message_lower:
            return "warning"
        elif "generating" in message_lower and "code" in message_lower:
            return "code_generation"
        elif "executing" in message_lower:
            return "execution"
        elif "prompt" in message_lower:
            return "prompt"
        elif "dataframe" in message_lower:
            return "dataframe"
        elif "thinking" in message_lower or "processing" in message_lower:
            return "thinking"
        elif "completed" in message_lower or "success" in message_lower:
            return "completion"
        else:
            return "info"
            
    def _is_thinking_message(self, message: str) -> bool:
        """Check if message is part of thinking process."""
        thinking_keywords = [
            "thinking", "processing", "analyzing", "understanding",
            "determining", "checking", "validating", "preparing"
        ]
        return any(keyword in message.lower() for keyword in thinking_keywords)
        
    def _is_code_generation_message(self, message: str) -> bool:
        """Check if message is part of code generation."""
        generation_keywords = [
            "generating", "code", "prompt", "template", "creating"
        ]
        return any(keyword in message.lower() for keyword in generation_keywords)