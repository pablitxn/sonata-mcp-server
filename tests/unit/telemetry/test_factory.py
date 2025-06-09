"""Tests for telemetry factory."""

import pytest
import os
from unittest.mock import patch, MagicMock

from telemetry.factory import TelemetryFactory
from telemetry.providers.noop import NoOpTelemetryProvider


class TestTelemetryFactory:
    """Test TelemetryFactory functionality."""
    
    def setup_method(self):
        """Reset factory before each test."""
        TelemetryFactory.reset()
        TelemetryFactory._providers.clear()
    
    def test_register_provider(self):
        """Test registering a provider."""
        mock_provider = MagicMock()
        TelemetryFactory.register_provider("test", mock_provider)
        
        assert "test" in TelemetryFactory._providers
        assert TelemetryFactory._providers["test"] == mock_provider
    
    def test_create_noop_provider_by_default(self):
        """Test creating NoOp provider by default."""
        provider = TelemetryFactory.create()
        
        assert isinstance(provider, NoOpTelemetryProvider)
        assert TelemetryFactory._instance == provider
    
    def test_create_noop_provider_explicitly(self):
        """Test creating NoOp provider explicitly."""
        provider = TelemetryFactory.create(provider="noop")
        
        assert isinstance(provider, NoOpTelemetryProvider)
    
    @patch.dict(os.environ, {"TELEMETRY_PROVIDER": "noop"})
    def test_create_from_environment(self):
        """Test creating provider from environment variable."""
        provider = TelemetryFactory.create()
        
        assert isinstance(provider, NoOpTelemetryProvider)
    
    def test_create_unknown_provider_raises(self):
        """Test creating unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown telemetry provider: unknown"):
            TelemetryFactory.create(provider="unknown")
    
    def test_get_instance(self):
        """Test getting current instance."""
        assert TelemetryFactory.get_instance() is None
        
        provider = TelemetryFactory.create()
        assert TelemetryFactory.get_instance() == provider
    
    def test_singleton_behavior(self):
        """Test factory returns same instance."""
        provider1 = TelemetryFactory.create()
        provider2 = TelemetryFactory.create()
        
        assert provider1 is provider2
    
    def test_reset(self):
        """Test resetting factory."""
        provider = TelemetryFactory.create()
        assert TelemetryFactory._instance is not None
        
        TelemetryFactory.reset()
        assert TelemetryFactory._instance is None
    
    @patch.dict(os.environ, {
        "TELEMETRY_SERVICE_NAME": "test-service",
        "TELEMETRY_ENVIRONMENT": "testing",
        "TELEMETRY_ENDPOINT": "http://localhost:8080",
        "TELEMETRY_API_KEY": "test-key",
        "TELEMETRY_SAMPLE_RATE": "0.5",
        "TELEMETRY_DEBUG": "true",
        "LANGFUSE_PUBLIC_KEY": "pub-key",
        "LANGFUSE_SECRET_KEY": "secret-key",
        "LANGFUSE_HOST": "https://test.langfuse.com",
    })
    def test_config_from_environment(self):
        """Test loading configuration from environment."""
        config = TelemetryFactory._get_config_from_env()
        
        assert config["service_name"] == "test-service"
        assert config["environment"] == "testing"
        assert config["endpoint"] == "http://localhost:8080"
        assert config["api_key"] == "test-key"
        assert config["sample_rate"] == 0.5
        assert config["debug"] is True
        assert config["langfuse_public_key"] == "pub-key"
        assert config["langfuse_secret_key"] == "secret-key"
        assert config["langfuse_host"] == "https://test.langfuse.com"
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = TelemetryFactory._get_config_from_env()
        
        assert config["service_name"] == "sonata-mcp-server"
        assert config["environment"] == "development"
        assert config["sample_rate"] == 1.0
        assert config["debug"] is False
        assert config["langfuse_host"] == "https://cloud.langfuse.com"
    
    def test_create_with_custom_config(self):
        """Test creating provider with custom config."""
        custom_config = {
            "service_name": "custom-service",
            "debug": True,
        }
        
        provider = TelemetryFactory.create(config=custom_config)
        # Provider should be initialized with custom config
        assert isinstance(provider, NoOpTelemetryProvider)