"""Example of telemetry integration in the Sonata MCP Server.

This module demonstrates how to use the telemetry system with different providers
and shows integration patterns for various scenarios.
"""

import asyncio
import os
from typing import Dict, Any

from telemetry.factory import get_telemetry_provider, TelemetryFactory
from config.telemetry_logger import logger


async def example_with_noop_provider():
    """Example using the NoOp provider (default for development)."""
    # NoOp provider is the default when no TELEMETRY_PROVIDER env var is set
    telemetry = get_telemetry_provider()
    
    logger.info("Starting example with NoOp provider")
    
    # Use traced operation context manager
    with telemetry.trace("example_operation") as trace:
        trace.add_metadata({"user_id": "test123", "operation": "demo"})
        
        # Simulate some work
        await asyncio.sleep(0.1)
        
        # Use timed operation for performance tracking
        with telemetry.timed_operation("database_query", {"query": "SELECT * FROM users"}):
            await asyncio.sleep(0.05)
        
        # Track a metric
        telemetry.track_metric("api_calls", 1, {"endpoint": "/example"})
        
        logger.info("Operation completed", trace_id=trace.id)


async def example_with_langfuse_provider():
    """Example using Langfuse provider for LLM observability."""
    # Reset factory to use Langfuse
    TelemetryFactory.reset()
    
    # Set environment variables for Langfuse
    os.environ["TELEMETRY_PROVIDER"] = "langfuse"
    # In production, set these via environment:
    # os.environ["LANGFUSE_PUBLIC_KEY"] = "your-public-key"
    # os.environ["LANGFUSE_SECRET_KEY"] = "your-secret-key"
    
    telemetry = get_telemetry_provider()
    
    logger.info("Starting example with Langfuse provider")
    
    # Track an LLM generation
    with telemetry.llm_generation(
        name="example_generation",
        model="gpt-4",
        model_parameters={"temperature": 0.7, "max_tokens": 100}
    ) as generation:
        # Simulate LLM call
        prompt = "What is the capital of France?"
        generation.add_prompt(prompt)
        
        await asyncio.sleep(0.2)  # Simulate API call
        
        response = "The capital of France is Paris."
        generation.add_completion(response)
        
        # Track token usage
        generation.add_metadata({
            "prompt_tokens": 8,
            "completion_tokens": 7,
            "total_tokens": 15
        })
        
        logger.info("LLM generation completed", 
                   model="gpt-4", 
                   tokens=15)


async def example_afip_login_with_telemetry():
    """Example showing how telemetry is integrated in AFIP login."""
    from connectors.afip.connector import AFIPConnector
    from connectors.afip.interfaces import AFIPCredentials
    
    # The connector already has telemetry integrated
    connector = AFIPConnector()
    
    # Mock credentials (don't use real ones!)
    credentials = AFIPCredentials(
        cuit="20123456789",
        password="dummy_password"
    )
    
    logger.info("Starting AFIP login example with telemetry")
    
    try:
        # The login method internally uses telemetry to track:
        # - Session restoration attempts
        # - Captcha handling
        # - Login success/failure
        # - Performance metrics
        status = await connector.login(credentials)
        
        logger.info("Login attempt completed", status=status.value)
    except Exception as e:
        logger.error("Login failed", error=str(e))


async def example_browser_automation_with_telemetry():
    """Example showing telemetry in browser automation."""
    from browser.factory import BrowserEngineFactory
    from browser.interfaces import BrowserConfig, BrowserType
    
    # Create browser with telemetry already integrated
    factory = BrowserEngineFactory()
    config = BrowserConfig(
        browser_type=BrowserType.CHROMIUM,
        headless=True
    )
    
    engine = await factory.create(config)
    context = await engine.create_context()
    page = await context.new_page()
    
    logger.info("Starting browser automation example")
    
    try:
        # Browser operations are automatically tracked with telemetry
        await page.goto("https://example.com")
        await page.wait_for_selector("h1")
        await page.click("a")
        
        logger.info("Browser automation completed")
    finally:
        await engine.close()


async def main():
    """Run all telemetry examples."""
    logger.info("Starting telemetry examples")
    
    # Example 1: NoOp provider (default)
    await example_with_noop_provider()
    
    # Example 2: Langfuse provider for LLMs
    await example_with_langfuse_provider()
    
    # Note: The following examples would require actual services
    # Uncomment to test with real services:
    
    # Example 3: AFIP login with integrated telemetry
    # await example_afip_login_with_telemetry()
    
    # Example 4: Browser automation with telemetry
    # await example_browser_automation_with_telemetry()
    
    logger.info("All telemetry examples completed")
    
    # Cleanup
    TelemetryFactory.reset()


if __name__ == "__main__":
    asyncio.run(main())