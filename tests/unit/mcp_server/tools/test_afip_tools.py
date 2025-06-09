"""Tests for AFIP MCP tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP
from src.mcp_server.tools.afip_tools import register_afip_tools
from src.connectors.afip.interfaces import LoginStatus, AFIPSession, AccountStatement, Payment, PaymentStatus


@pytest.fixture
def mcp_server():
    """Create a test MCP server instance."""
    return FastMCP("test-server")


@pytest.fixture
def mock_connector():
    """Create a mock AFIP connector."""
    return AsyncMock()


@pytest.fixture
def sample_session():
    """Create a sample AFIP session."""
    return AFIPSession(
        session_id="test_session_123",
        cuit="20123456789",
        cookies={"auth": "token123"},
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=2),
        is_valid=True
    )


@pytest.fixture
def sample_account_statement():
    """Create a sample account statement."""
    return AccountStatement(
        total_debt=15000.50,
        screenshot_path="/tmp/afip_screenshots/estado_cuenta_20123456789_20250608_120000.png",
        period_from="01/2025",
        period_to="06/2025",
        calculation_date="08/06/2025",
        retrieved_at=datetime.now()
    )


@pytest.fixture
def sample_payments():
    """Create sample pending payments."""
    return [
        Payment(
            id="PAY001",
            description="IVA - Junio 2025",
            amount=5000.00,
            due_date=datetime(2025, 7, 15),
            status=PaymentStatus.PENDING,
            tax_type="IVA",
            period="06/2025"
        ),
        Payment(
            id="PAY002",
            description="Ganancias - Q1 2025",
            amount=10000.00,
            due_date=datetime(2025, 6, 30),
            status=PaymentStatus.OVERDUE,
            tax_type="Ganancias",
            period="Q1/2025"
        )
    ]


class TestAFIPTools:
    """Test suite for AFIP MCP tools."""
    
    @pytest.mark.asyncio
    async def test_register_afip_tools(self, mcp_server):
        """Test that AFIP tools are registered correctly."""
        register_afip_tools(mcp_server)
        
        # Check that all tools are registered
        tool_names = [tool.name for tool in mcp_server._tools.values()]
        assert "afip_login" in tool_names
        assert "afip_logout" in tool_names
        assert "afip_get_account_statement" in tool_names
        assert "afip_get_pending_payments" in tool_names
        assert "afip_get_session_status" in tool_names
    
    @pytest.mark.asyncio
    async def test_afip_login_success(self, mcp_server, mock_connector, sample_session):
        """Test successful AFIP login."""
        register_afip_tools(mcp_server)
        
        with patch('src.mcp_server.tools.afip_tools._get_connector', return_value=mock_connector):
            mock_connector.login.return_value = LoginStatus.SUCCESS
            mock_connector.get_session.return_value = sample_session
            
            # Get the tool function
            login_tool = next(tool for tool in mcp_server._tools.values() if tool.name == "afip_login")
            
            # Call the tool
            result = await login_tool.fn(cuit="20-12345678-9", password="test123")
            
            assert result["success"] is True
            assert result["status"] == "success"
            assert "session" in result
            assert result["session"]["cuit"] == "20123456789"
    
    @pytest.mark.asyncio
    async def test_afip_login_failure(self, mcp_server, mock_connector):
        """Test failed AFIP login."""
        register_afip_tools(mcp_server)
        
        with patch('src.mcp_server.tools.afip_tools._get_connector', return_value=mock_connector):
            mock_connector.login.return_value = LoginStatus.FAILED
            
            login_tool = next(tool for tool in mcp_server._tools.values() if tool.name == "afip_login")
            result = await login_tool.fn(cuit="20-12345678-9", password="wrong")
            
            assert result["success"] is False
            assert result["status"] == "failed"
            assert "session" not in result
    
    @pytest.mark.asyncio
    async def test_afip_logout(self, mcp_server, mock_connector):
        """Test AFIP logout."""
        register_afip_tools(mcp_server)
        
        with patch('src.mcp_server.tools.afip_tools._get_connector', return_value=mock_connector):
            mock_connector.logout.return_value = True
            
            logout_tool = next(tool for tool in mcp_server._tools.values() if tool.name == "afip_logout")
            result = await logout_tool.fn()
            
            assert result["success"] is True
            assert "Logout successful" in result["message"]
    
    @pytest.mark.asyncio
    async def test_afip_get_account_statement_success(self, mcp_server, mock_connector, sample_session, sample_account_statement):
        """Test successful account statement retrieval."""
        register_afip_tools(mcp_server)
        
        with patch('src.mcp_server.tools.afip_tools._get_connector', return_value=mock_connector):
            mock_connector.get_session.return_value = sample_session
            mock_connector.get_account_statement.return_value = sample_account_statement
            
            statement_tool = next(tool for tool in mcp_server._tools.values() if tool.name == "afip_get_account_statement")
            result = await statement_tool.fn(period_from="01/2025", period_to="06/2025")
            
            assert result["success"] is True
            assert result["total_debt"] == 15000.50
            assert "screenshot_path" in result
            assert result["period_from"] == "01/2025"
    
    @pytest.mark.asyncio
    async def test_afip_get_account_statement_no_session(self, mcp_server, mock_connector):
        """Test account statement request without active session."""
        register_afip_tools(mcp_server)
        
        with patch('src.mcp_server.tools.afip_tools._get_connector', return_value=mock_connector):
            mock_connector.get_session.return_value = None
            
            statement_tool = next(tool for tool in mcp_server._tools.values() if tool.name == "afip_get_account_statement")
            result = await statement_tool.fn()
            
            assert result["success"] is False
            assert "No active session" in result["message"]
    
    @pytest.mark.asyncio
    async def test_afip_get_pending_payments_success(self, mcp_server, mock_connector, sample_session, sample_payments):
        """Test successful pending payments retrieval."""
        register_afip_tools(mcp_server)
        
        with patch('src.mcp_server.tools.afip_tools._get_connector', return_value=mock_connector):
            mock_connector.get_session.return_value = sample_session
            mock_connector.get_pending_payments.return_value = sample_payments
            
            payments_tool = next(tool for tool in mcp_server._tools.values() if tool.name == "afip_get_pending_payments")
            result = await payments_tool.fn()
            
            assert result["success"] is True
            assert result["count"] == 2
            assert len(result["payments"]) == 2
            assert result["payments"][0]["id"] == "PAY001"
            assert result["payments"][0]["amount"] == 5000.00
            assert result["payments"][1]["status"] == "overdue"
    
    @pytest.mark.asyncio
    async def test_afip_get_session_status_with_session(self, mcp_server, mock_connector, sample_session):
        """Test session status when logged in."""
        register_afip_tools(mcp_server)
        
        with patch('src.mcp_server.tools.afip_tools._get_connector', return_value=mock_connector):
            mock_connector.get_session.return_value = sample_session
            
            status_tool = next(tool for tool in mcp_server._tools.values() if tool.name == "afip_get_session_status")
            result = await status_tool.fn()
            
            assert result["success"] is True
            assert result["has_session"] is True
            assert result["cuit"] == "20123456789"
            assert result["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_afip_get_session_status_no_session(self, mcp_server, mock_connector):
        """Test session status when not logged in."""
        register_afip_tools(mcp_server)
        
        with patch('src.mcp_server.tools.afip_tools._get_connector', return_value=mock_connector):
            mock_connector.get_session.return_value = None
            
            status_tool = next(tool for tool in mcp_server._tools.values() if tool.name == "afip_get_session_status")
            result = await status_tool.fn()
            
            assert result["success"] is True
            assert result["has_session"] is False
            assert "No active session" in result["message"]
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server, mock_connector):
        """Test error handling in tools."""
        register_afip_tools(mcp_server)
        
        with patch('src.mcp_server.tools.afip_tools._get_connector', return_value=mock_connector):
            mock_connector.login.side_effect = Exception("Connection error")
            
            login_tool = next(tool for tool in mcp_server._tools.values() if tool.name == "afip_login")
            result = await login_tool.fn(cuit="20-12345678-9", password="test123")
            
            assert result["success"] is False
            assert "error" in result["status"]
            assert "Connection error" in result["message"]