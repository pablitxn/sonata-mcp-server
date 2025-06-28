"""PandasAI tools for MCP server.

This module provides MCP tools for querying spreadsheet files using PandasAI,
enabling natural language queries on Excel/CSV data.
"""

import os
import sys
import pandas as pd
from typing import Optional, Dict, Any
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from config.mcp_logger import logger


def register_pandas_ai_tools(mcp: FastMCP):
    """Register PandasAI tools with the MCP server."""
    
    @mcp.tool()
    async def query_spreadsheet(
        file_name: str = "complex_dataset.xlsx",
        query: str = ""
    ) -> TextContent:
        """Query spreadsheet data using natural language.
        
        This tool allows you to ask questions about spreadsheet data in natural language.
        The AI agent will analyze the data and provide answers based on the content.
        
        Args:
            file_name: Name of the spreadsheet file (currently supports only the mock file)
            query: Natural language question about the data
            
        Returns:
            TextContent with the answer to the query
        """
        try:
            logger.info("query_spreadsheet: Starting query", file_name=file_name, query=query)
            
            # Import here to avoid circular imports
            import sys
            from pathlib import Path
            
            # Add the agents directory to Python path as if pandasai was installed
            agents_path = Path(__file__).parent.parent.parent / "agents"
            if str(agents_path) not in sys.path:
                sys.path.insert(0, str(agents_path))
            
            from pandasai import Agent
            from pandasai.dataframe import DataFrame
            from pandasai.llm.openai_adapter import ConfigurableLLM
            from pandasai.config import Config
            
            # For now, we use the hardcoded mock file path
            # TODO: Integrate with file storage system when available
            base_path = Path(__file__).parent.parent.parent  # Navigate to src/
            file_path = base_path / "utils" / "mocks" / "complex_dataset.xlsx"
            
            if not file_path.exists():
                error_msg = f"Mock file not found at {file_path}"
                logger.error("query_spreadsheet: File not found", path=str(file_path))
                return TextContent(type="text", text=f"Error: {error_msg}")
            
            # Load the Excel file into a pandas DataFrame
            logger.debug("query_spreadsheet: Loading Excel file", path=str(file_path))
            pandas_df = pd.read_excel(file_path)
            logger.info("query_spreadsheet: DataFrame loaded", 
                       shape=pandas_df.shape, 
                       columns=list(pandas_df.columns))
            
            # Convert pandas DataFrame to PandasAI DataFrame
            df = DataFrame(pandas_df, name=file_name, description="Spreadsheet data for analysis")
            
            # Initialize the LLM adapter with environment configuration
            logger.debug("query_spreadsheet: Initializing LLM")
            llm = ConfigurableLLM()
            
            # Create config with LLM
            config = Config(llm=llm, verbose=True)
            
            # Create PandasAI agent with the dataframe and config
            logger.debug("query_spreadsheet: Creating PandasAI agent")
            agent = Agent([df], config=config)
            
            # Execute the query
            logger.info("query_spreadsheet: Executing query")
            result = agent.chat(query)
            
            # Format the response
            if result is None:
                response = "I couldn't find an answer to your query."
            elif isinstance(result, pd.DataFrame):
                # Convert DataFrame result to string representation
                response = f"Here's the result:\n\n{result.to_string()}"
            elif isinstance(result, (list, dict)):
                # Convert structured data to readable format
                response = f"Result: {str(result)}"
            else:
                response = str(result)
            
            logger.info("query_spreadsheet: Query completed successfully")
            return TextContent(type="text", text=response)
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error("query_spreadsheet: Error occurred", 
                        error=str(e), 
                        error_type=type(e).__name__)
            return TextContent(type="text", text=error_msg)
    
    logger.info("PandasAI tools registered successfully")