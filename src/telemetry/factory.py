"""Factory for creating telemetry providers."""

import os
from typing import Dict, Any, Optional
from .interfaces import ITelemetryProvider


class TelemetryFactory:
    """Factory for creating telemetry providers based on configuration."""
    
    _providers: Dict[str, type[ITelemetryProvider]] = {}
    _instance: Optional[ITelemetryProvider] = None
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type[ITelemetryProvider]) -> None:
        """Register a telemetry provider."""
        cls._providers[name] = provider_class
    
    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ITelemetryProvider:
        """Create and return a telemetry provider instance."""
        if cls._instance is not None:
            return cls._instance
        
        provider_name = provider or os.getenv("TELEMETRY_PROVIDER", "noop")
        provider_config = config or cls._get_config_from_env()
        
        if provider_name not in cls._providers:
            # Lazy import providers
            if provider_name == "noop":
                from .providers.noop import NoOpTelemetryProvider
                cls.register_provider("noop", NoOpTelemetryProvider)
            elif provider_name == "langfuse":
                from .providers.langfuse import LangfuseTelemetryProvider
                cls.register_provider("langfuse", LangfuseTelemetryProvider)
            else:
                raise ValueError(f"Unknown telemetry provider: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        cls._instance = provider_class()
        cls._instance.initialize(provider_config)
        
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> Optional[ITelemetryProvider]:
        """Get the current telemetry provider instance."""
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the factory and shutdown current provider."""
        if cls._instance:
            cls._instance.shutdown()
            cls._instance = None
    
    @classmethod
    def _get_config_from_env(cls) -> Dict[str, Any]:
        """Get telemetry configuration from environment variables."""
        return {
            "service_name": os.getenv("TELEMETRY_SERVICE_NAME", "sonata-mcp-server"),
            "environment": os.getenv("TELEMETRY_ENVIRONMENT", "development"),
            "endpoint": os.getenv("TELEMETRY_ENDPOINT"),
            "api_key": os.getenv("TELEMETRY_API_KEY"),
            "sample_rate": float(os.getenv("TELEMETRY_SAMPLE_RATE", "1.0")),
            "debug": os.getenv("TELEMETRY_DEBUG", "false").lower() == "true",
            # LLM-specific configuration
            "langfuse_public_key": os.getenv("LANGFUSE_PUBLIC_KEY"),
            "langfuse_secret_key": os.getenv("LANGFUSE_SECRET_KEY"),
            "langfuse_host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        }


def get_telemetry_provider() -> ITelemetryProvider:
    """Get or create the default telemetry provider instance."""
    return TelemetryFactory.create()