"""Enhanced PandasAI Agent with comprehensive telemetry and MCP visibility"""

import traceback
import warnings
from typing import Any, List, Optional, Union
import time
import json

import pandas as pd

from pandasai.core.code_execution.code_executor import CodeExecutor
from pandasai.core.code_generation.telemetry_generator import TelemetryCodeGenerator
from pandasai.core.prompts import (
    get_chat_prompt_for_sql,
    get_correct_error_prompt_for_sql,
    get_correct_output_type_error_prompt,
)
from pandasai.core.response.error import ErrorResponse
from pandasai.core.response.parser import ResponseParser
from pandasai.core.user_query import UserQuery
from pandasai.dataframe.base import DataFrame
from pandasai.dataframe.virtual_dataframe import VirtualDataFrame
from pandasai.exceptions import (
    CodeExecutionError,
    InvalidLLMOutputType,
    MissingVectorStoreError,
)
from pandasai.sandbox import Sandbox
from pandasai.vectorstores.vectorstore import VectorStore

from config import Config
from ..data_loader.duck_db_connection_manager import DuckDBConnectionManager
from ..query_builders.base_query_builder import BaseQueryBuilder
from ..query_builders.sql_parser import SQLParser
from .state import AgentState
from .base import Agent
from config.telemetry_logger import logger, get_telemetry
from telemetry.interfaces import SpanKind


class TelemetryAgent(Agent):
    """
    Enhanced Agent class with comprehensive telemetry for MCP visibility
    """

    def __init__(
        self,
        dfs: Union[
            Union[DataFrame, VirtualDataFrame], List[Union[DataFrame, VirtualDataFrame]]
        ],
        config: Optional[Union[Config, dict]] = None,
        memory_size: Optional[int] = 10,
        vectorstore: Optional[VectorStore] = None,
        description: str = None,
        sandbox: Sandbox = None,
    ):
        """Initialize agent with telemetry support"""
        super().__init__(dfs, config, memory_size, vectorstore, description, sandbox)
        
        # Replace code generator with telemetry version
        self._code_generator = TelemetryCodeGenerator(self._state)
        
        # Initialize telemetry
        self.telemetry = get_telemetry()
        self.tracer = self.telemetry.get_tracer() if self.telemetry else None
        self.metrics = self.telemetry.get_metrics() if self.telemetry else None
        
        logger.info(
            "initialized_telemetry_agent",
            event_type="agent_init",
            memory_size=memory_size,
            has_vectorstore=bool(vectorstore),
            dataframes_count=len(dfs) if isinstance(dfs, list) else 1,
            telemetry_enabled=bool(self.telemetry)
        )

    def chat(self, query: str, output_type: Optional[str] = None):
        """Start a new chat interaction with comprehensive telemetry"""
        logger.info(
            "pandasai_chat_started",
            event_type="chat_started",
            query=query,
            output_type=output_type,
            conversation_id=self._state.prompt_id
        )
        
        if self.metrics:
            self.metrics.increment("pandasai.chat.requests", tags={"output_type": output_type or "any"})
        
        try:
            result = super().chat(query, output_type)
            
            logger.info(
                "pandasai_chat_completed",
                event_type="chat_completed",
                query=query,
                output_type=output_type,
                conversation_id=self._state.prompt_id,
                success=True
            )
            
            if self.metrics:
                self.metrics.increment("pandasai.chat.success")
            
            return result
            
        except Exception as e:
            logger.error(
                "pandasai_chat_failed",
                event_type="chat_failed",
                query=query,
                output_type=output_type,
                conversation_id=self._state.prompt_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            if self.metrics:
                self.metrics.increment("pandasai.chat.errors", tags={"error_type": type(e).__name__})
            
            raise

    def generate_code(self, query: Union[UserQuery, str]) -> str:
        """Generate code with telemetry tracking"""
        span_context = None
        if self.tracer:
            span_context = self.tracer.span(
                "pandasai_code_generation",
                kind=SpanKind.INTERNAL,
                attributes={
                    "query": str(query),
                    "conversation_id": self._state.prompt_id,
                    "memory_size": len(self._state.memory),
                }
            )
        
        with span_context if span_context else nullcontext():
            start_time = time.time()
            
            # Log thinking process start
            logger.info(
                "pandasai_thinking_started",
                event_type="thinking_started",
                phase="code_generation",
                query=str(query),
                conversation_id=self._state.prompt_id
            )
            
            # Add to memory with logging
            self._state.memory.add(str(query), is_user=True)
            logger.debug(
                "memory_updated",
                event_type="memory_add",
                is_user=True,
                memory_size=len(self._state.memory)
            )
            
            # Log prompt generation
            logger.info(
                "generating_prompt",
                event_type="prompt_generation",
                phase="preparing"
            )
            
            prompt = get_chat_prompt_for_sql(self._state)
            self._state.last_prompt_used = prompt
            
            # Log the prompt details for visibility
            logger.info(
                "prompt_generated",
                event_type="prompt_ready",
                prompt_length=len(prompt.to_string()),
                prompt_preview=prompt.to_string()[:500] + "..." if len(prompt.to_string()) > 500 else prompt.to_string()
            )
            
            # Generate code with LLM
            logger.info(
                "llm_code_generation_started",
                event_type="llm_started",
                llm_type=self._state.config.llm.type if self._state.config.llm else "unknown"
            )
            
            code = self._code_generator.generate_code(prompt)
            
            generation_time = time.time() - start_time
            
            # Log generated code
            logger.info(
                "code_generated",
                event_type="code_ready",
                code_length=len(code),
                generation_time_ms=generation_time * 1000,
                code_preview=code[:500] + "..." if len(code) > 500 else code
            )
            
            # Log full thinking process
            logger.info(
                "pandasai_thinking_completed",
                event_type="thinking_completed",
                phase="code_generation",
                duration_ms=generation_time * 1000,
                generated_code=code,
                conversation_id=self._state.prompt_id
            )
            
            if self.metrics:
                self.metrics.timing("pandasai.code_generation.duration", generation_time * 1000)
                self.metrics.gauge("pandasai.code_generation.size", len(code))
            
            return code

    def execute_code(self, code: str) -> dict:
        """Execute code with detailed telemetry"""
        span_context = None
        if self.tracer:
            span_context = self.tracer.span(
                "pandasai_code_execution",
                kind=SpanKind.INTERNAL,
                attributes={
                    "code_length": len(code),
                    "conversation_id": self._state.prompt_id,
                }
            )
        
        with span_context if span_context else nullcontext():
            start_time = time.time()
            
            # Log execution start
            logger.info(
                "code_execution_started",
                event_type="execution_started",
                code_length=len(code),
                code_snippet=code[:200] + "..." if len(code) > 200 else code
            )
            
            try:
                # Create executor with telemetry
                code_executor = CodeExecutor(self._state.config)
                code_executor.add_to_env("execute_sql_query", self._execute_sql_query)
                
                # Execute in sandbox or directly
                if self._sandbox:
                    logger.debug("executing_in_sandbox", sandbox_type=type(self._sandbox).__name__)
                    result = self._sandbox.execute(code, code_executor.environment)
                else:
                    logger.debug("executing_directly")
                    result = code_executor.execute_and_return_result(code)
                
                execution_time = time.time() - start_time
                
                # Log execution result
                logger.info(
                    "code_execution_completed",
                    event_type="execution_completed",
                    duration_ms=execution_time * 1000,
                    result_type=type(result).__name__,
                    has_error="error" in result if isinstance(result, dict) else False
                )
                
                # Log the output for MCP visibility
                if isinstance(result, dict):
                    logger.info(
                        "pandasai_output",
                        event_type="execution_output",
                        output_type=result.get("type", "unknown"),
                        output_value=str(result.get("value", ""))[:1000],  # Truncate large outputs
                        conversation_id=self._state.prompt_id
                    )
                
                if self.metrics:
                    self.metrics.timing("pandasai.code_execution.duration", execution_time * 1000)
                    self.metrics.increment("pandasai.code_execution.success")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.error(
                    "code_execution_failed",
                    event_type="execution_failed",
                    duration_ms=execution_time * 1000,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    error_trace=traceback.format_exc()
                )
                
                if self.metrics:
                    self.metrics.increment("pandasai.code_execution.errors", tags={"error_type": type(e).__name__})
                
                raise

    def _process_query(self, query: str, output_type: Optional[str] = None):
        """Process query with comprehensive telemetry"""
        query_obj = UserQuery(query)
        
        # Create main span for the entire query processing
        span_context = None
        if self.tracer:
            span_context = self.tracer.span(
                "pandasai_query_processing",
                kind=SpanKind.SERVER,
                attributes={
                    "query": str(query),
                    "output_type": output_type,
                    "conversation_id": self._state.prompt_id,
                }
            )
        
        with span_context if span_context else nullcontext():
            process_start = time.time()
            
            # Log query processing start
            logger.info(
                "query_processing_started",
                event_type="query_started",
                query=str(query),
                output_type=output_type,
                conversation_id=self._state.prompt_id,
                llm_type=self._state.config.llm.type if self._state.config.llm else "unknown"
            )
            
            self._state.output_type = output_type
            
            try:
                self._state.assign_prompt_id()
                
                # Track retries
                code_generation_retries = 0
                execution_retries = 0
                
                # Generate code with tracking
                logger.info("starting_code_generation_phase")
                code = self._generate_code_with_retry_tracking(query_obj, code_generation_retries)
                
                # Execute code with tracking
                logger.info("starting_code_execution_phase")
                result = self._execute_with_retry_tracking(code, execution_retries)
                
                total_time = time.time() - process_start
                
                # Log successful completion
                logger.info(
                    "query_processing_completed",
                    event_type="query_completed",
                    query=str(query),
                    output_type=output_type,
                    conversation_id=self._state.prompt_id,
                    total_duration_ms=total_time * 1000,
                    code_generation_retries=code_generation_retries,
                    execution_retries=execution_retries,
                    final_code_length=len(code),
                    result_type=type(result).__name__
                )
                
                if self.metrics:
                    self.metrics.timing("pandasai.query.total_duration", total_time * 1000)
                    self.metrics.increment("pandasai.query.success")
                
                return result
                
            except Exception as e:
                total_time = time.time() - process_start
                
                logger.error(
                    "query_processing_failed",
                    event_type="query_failed",
                    query=str(query),
                    output_type=output_type,
                    conversation_id=self._state.prompt_id,
                    total_duration_ms=total_time * 1000,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                
                if self.metrics:
                    self.metrics.increment("pandasai.query.errors", tags={"error_type": type(e).__name__})
                
                if isinstance(e, CodeExecutionError):
                    return self._handle_exception(code)
                raise

    def _generate_code_with_retry_tracking(self, query: UserQuery, retry_count: int) -> str:
        """Generate code with retry tracking"""
        max_retries = self._state.config.max_retries
        attempts = 0
        
        try:
            return self.generate_code(query)
        except Exception as e:
            exception = e
            while attempts <= max_retries:
                try:
                    logger.info(
                        "retrying_code_generation",
                        event_type="retry",
                        phase="code_generation",
                        attempt=attempts + 1,
                        max_retries=max_retries,
                        error_type=type(exception).__name__
                    )
                    
                    retry_count += 1
                    return self._regenerate_code_after_error(
                        self._state.last_code_generated, exception
                    )
                except Exception as e:
                    exception = e
                    attempts += 1
                    if attempts > max_retries:
                        logger.error(
                            "code_generation_max_retries_exceeded",
                            event_type="max_retries",
                            phase="code_generation",
                            final_error=str(e)
                        )
                        raise
            return None

    def _execute_with_retry_tracking(self, code: str, retry_count: int) -> Any:
        """Execute code with retry tracking"""
        max_retries = self._state.config.max_retries
        attempts = 0
        
        while attempts <= max_retries:
            try:
                result = self.execute_code(code)
                return self._response_parser.parse(result, code)
            except Exception as e:
                attempts += 1
                retry_count += 1
                
                if attempts > max_retries:
                    logger.error(
                        "execution_max_retries_exceeded",
                        event_type="max_retries",
                        phase="execution",
                        final_error=str(e)
                    )
                    raise
                
                logger.info(
                    "retrying_execution",
                    event_type="retry",
                    phase="execution",
                    attempt=attempts,
                    max_retries=max_retries,
                    error_type=type(e).__name__
                )
                
                code = self._regenerate_code_after_error(code, e)
        
        return None

    def _regenerate_code_after_error(self, code: str, error: Exception) -> str:
        """Regenerate code with error tracking"""
        error_trace = traceback.format_exc()
        
        logger.info(
            "regenerating_code_after_error",
            event_type="code_regeneration",
            error_type=type(error).__name__,
            error_message=str(error),
            previous_code_length=len(code)
        )
        
        if isinstance(error, InvalidLLMOutputType):
            prompt = get_correct_output_type_error_prompt(
                self._state, code, error_trace
            )
        else:
            prompt = get_correct_error_prompt_for_sql(self._state, code, error_trace)
        
        regenerated_code = self._code_generator.generate_code(prompt)
        
        logger.info(
            "code_regenerated",
            event_type="code_regenerated",
            new_code_length=len(regenerated_code),
            changed_lines=self._count_changed_lines(code, regenerated_code)
        )
        
        return regenerated_code

    def _count_changed_lines(self, old_code: str, new_code: str) -> int:
        """Count changed lines between two code snippets"""
        old_lines = old_code.splitlines()
        new_lines = new_code.splitlines()
        
        changed = 0
        for i, (old, new) in enumerate(zip(old_lines, new_lines)):
            if old != new:
                changed += 1
        
        # Add difference in number of lines
        changed += abs(len(old_lines) - len(new_lines))
        
        return changed


def nullcontext():
    """Simple context manager that does nothing"""
    from contextlib import contextmanager
    
    @contextmanager
    def _nullcontext():
        yield
    
    return _nullcontext()