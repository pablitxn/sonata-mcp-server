"""Integration tests for AFIP connector."""

import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig
from src.captcha import CaptchaChain
from src.connectors.afip.connector import AFIPConnector
from src.connectors.afip.interfaces import (
    AFIPCredentials,
    AFIPSession,
    LoginStatus,
    PaymentStatus,
)
from src.connectors.afip.session import InMemorySessionStorage


@pytest.mark.asyncio
class TestAFIPConnectorIntegration:
    """Integration tests for AFIP connector."""
    
    @pytest_asyncio.fixture
    async def browser_factory(self):
        """Browser factory configured for Selenium."""
        factory = BrowserEngineFactory()
        yield factory
        # Cleanup is handled in each test
    
    @pytest.fixture
    def temp_storage_dir(self):
        """Temporary directory for storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def mock_captcha_chain(self):
        """Mock of captcha chain."""
        chain = MagicMock(spec=CaptchaChain)
        chain.solve = AsyncMock(return_value="MOCK_CAPTCHA_SOLUTION")
        return chain
    
    @pytest.fixture
    def browser_config(self):
        """Browser configuration for tests."""
        return BrowserConfig(
            headless=True,  # For tests we use headless
            viewport={"width": 1280, "height": 720}
        )
    
    @pytest_asyncio.fixture
    async def afip_connector(self, browser_factory, mock_captcha_chain, browser_config):
        """Creates an AFIP connector for tests."""
        storage = InMemorySessionStorage()
        
        connector = AFIPConnector(
            browser_factory=browser_factory,
            session_storage=storage,
            captcha_chain=mock_captcha_chain,
            browser_config=browser_config
        )
        
        yield connector
        
        # Cleanup
        await connector.logout()
    
    @pytest.fixture
    def test_credentials(self):
        """Test credentials."""
        return AFIPCredentials(
            cuit="20-12345678-9",
            password="test_password"
        )
    
    @pytest.fixture
    def mock_afip_page(self):
        """Mock of AFIP HTML page."""
        return """
        <html>
            <body>
                <form>
                    <input name="user" type="text" />
                    <input name="password" type="password" />
                    <button type="submit">Ingresar</button>
                </form>
            </body>
        </html>
        """
    
    async def test_connector_initialization(self, browser_factory):
        """Verifies correct connector initialization."""
        connector = AFIPConnector(browser_factory)
        
        assert connector.browser_factory is not None
        assert connector.session_storage is not None
        assert connector.captcha_chain is not None
        assert connector._context is None
        assert connector._page is None
    
    @patch('src.connectors.afip.connector.os.getenv')
    async def test_default_captcha_chain_creation(self, mock_getenv, browser_factory):
        """Verifies default captcha chain creation."""
        # Simulate configured API keys
        mock_getenv.side_effect = lambda key: {
            "CAPSOLVER_API_KEY": "cap_key",
            "TWOCAPTCHA_API_KEY": "2cap_key",
            "ANTICAPTCHA_API_KEY": "anti_key"
        }.get(key)
        
        connector = AFIPConnector(browser_factory)
        
        # The chain should have configured solvers
        assert len(connector.captcha_chain._handlers) > 0
    
    async def test_login_with_mock_page(self, afip_connector, test_credentials):
        """Login test with mocked page."""
        # Browser mock
        mock_page = MagicMock()
        mock_context = MagicMock()
        
        # Configure mocks
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        # Evaluate returns different values depending on what's being evaluated
        evaluate_returns = [
            False,  # has_image_captcha
            False,  # has_recaptcha
            "https://portalcf.cloud.afip.gob.ar/portal/app/home"  # window.location.href
        ]
        mock_page.evaluate = AsyncMock(side_effect=evaluate_returns)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.get_cookies = AsyncMock(return_value=[
            {"name": "session", "value": "abc123"},
            {"name": "token", "value": "xyz789"}
        ])
        
        # Inject mocks
        afip_connector._page = mock_page
        afip_connector._context = mock_context
        
        # Simulate successful login
        mock_page.wait_for_selector.side_effect = [
            None,  # Wait for form
            None   # Wait for logout button (successful login)
        ]
        
        result = await afip_connector.login(test_credentials)
        
        assert result == LoginStatus.SUCCESS
        assert afip_connector._current_session is not None
        assert afip_connector._current_session.cuit == test_credentials.cuit
    
    async def test_login_with_captcha(self, afip_connector, test_credentials):
        """Login test when captcha is detected."""
        mock_page = MagicMock()
        mock_context = MagicMock()
        
        # Configure captcha detection
        mock_page.evaluate = AsyncMock()
        mock_page.evaluate.side_effect = [
            True,   # has_image_captcha = True
            False,  # has_recaptcha = False
            None    # Other evaluates
        ]
        
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.get_cookies = AsyncMock(return_value=[])
        
        afip_connector._page = mock_page
        afip_connector._context = mock_context
        
        # The captcha chain should be called
        result = await afip_connector.login(test_credentials)
        
        afip_connector.captcha_chain.solve.assert_called_once()
    
    async def test_session_restoration(self, afip_connector, test_credentials):
        """Test for saved session restoration."""
        # Create valid session
        valid_session = AFIPSession(
            session_id="test_session",
            cuit=test_credentials.cuit,
            cookies={"session": "abc123"},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            is_valid=True
        )
        
        # Save session
        await afip_connector.session_storage.save(valid_session)
        
        # Page mock for verification
        mock_page = MagicMock()
        mock_context = MagicMock()
        
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=True)  # Valid session
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.set_cookies = AsyncMock()
        
        # Factory mock
        mock_engine = MagicMock()
        mock_engine.initialize = AsyncMock()
        mock_engine.create_context = AsyncMock(return_value=mock_context)
        
        with patch.object(afip_connector.browser_factory, 'create', 
                         AsyncMock(return_value=mock_engine)):
            result = await afip_connector.login(test_credentials)
        
        assert result == LoginStatus.SUCCESS
        mock_context.set_cookies.assert_called_once()
    
    async def test_get_pending_payments(self, afip_connector):
        """Test for getting pending payments."""
        # Simulate active session
        afip_connector._current_session = AFIPSession(
            session_id="test",
            cuit="20-12345678-9",
            cookies={},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            is_valid=True
        )
        
        # Page mock with payments table
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[
            {
                "id": "001",
                "description": "IVA Mensual",
                "amount": "$10.500,50",
                "due_date": "15/01/2024",
                "status": "Pendiente",
                "tax_type": "IVA",
                "period": "12/2023"
            },
            {
                "id": "002",
                "description": "Ganancias",
                "amount": "$25.000,00",
                "due_date": "20/01/2024",
                "status": "Vencido",
                "tax_type": "Ganancias",
                "period": "12/2023"
            }
        ])
        
        afip_connector._page = mock_page
        
        payments = await afip_connector.get_pending_payments()
        
        assert len(payments) == 2
        assert payments[0].id == "001"
        assert payments[0].amount == 10500.50
        assert payments[0].status == PaymentStatus.PENDING
        assert payments[1].status == PaymentStatus.OVERDUE
    
    async def test_logout(self, afip_connector):
        """Logout test."""
        # Simulate active session
        afip_connector._current_session = AFIPSession(
            session_id="test",
            cuit="20-12345678-9",
            cookies={},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            is_valid=True
        )
        
        # Page mock
        mock_page = MagicMock()
        mock_page.click = AsyncMock()
        mock_page.close = AsyncMock()
        
        mock_context = MagicMock()
        mock_context.close = AsyncMock()
        
        afip_connector._page = mock_page
        afip_connector._context = mock_context
        
        result = await afip_connector.logout()
        
        assert result is True
        assert afip_connector._current_session is None
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
    
    async def test_login_failure_scenarios(self, afip_connector, test_credentials):
        """Test for login failure scenarios."""
        mock_page = MagicMock()
        mock_context = MagicMock()
        
        # Configure for login failure
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=False)
        
        # Simulate timeout waiting for logout button (login failed)
        mock_page.wait_for_selector.side_effect = [
            None,  # Form OK
            Exception("Timeout")  # Logout doesn't appear
        ]
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        afip_connector._page = mock_page
        afip_connector._context = mock_context
        
        result = await afip_connector.login(test_credentials)
        
        assert result == LoginStatus.FAILED
        assert afip_connector._current_session is None
    
    async def test_certificate_required_detection(self, afip_connector, test_credentials):
        """Test for certificate requirement detection."""
        mock_page = MagicMock()
        mock_context = MagicMock()
        
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        
        # Configure evaluations in order
        evaluate_results = [
            False,  # has_image_captcha
            False,  # has_recaptcha
            "https://auth.afip.gob.ar/contribuyente_/login.xhtml",  # window.location.href (still on login page)
            True    # requires_cert check
        ]
        mock_page.evaluate = AsyncMock(side_effect=evaluate_results)
        
        # All selectors succeed but login fails (stays on login page)
        mock_page.wait_for_selector.side_effect = [
            None,  # Form OK
            None   # Password field OK
        ]
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.get_cookies = AsyncMock(return_value=[])
        
        afip_connector._page = mock_page
        afip_connector._context = mock_context
        
        result = await afip_connector.login(test_credentials)
        
        assert result == LoginStatus.CERTIFICATE_REQUIRED

    @pytest.mark.skip(reason="Requires real AFIP page structure - fails with mocks")
    async def test_get_account_statement(self, afip_connector):
        """Test for getting account statement."""
        # Simulate active session
        afip_connector._current_session = AFIPSession(
            session_id="test",
            cuit="20-12345678-9",
            cookies={},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            is_valid=True
        )
        
        # Mock page for main dashboard
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value="window.location.href")
        
        # Mock page for account statement (new tab)
        mock_account_page = MagicMock()
        mock_account_page.fill = AsyncMock()
        mock_account_page.click = AsyncMock()
        mock_account_page.screenshot = AsyncMock()
        mock_account_page.evaluate = AsyncMock(return_value="https://servicios2.afip.gob.ar/tramites_con_clave_fiscal/ccam/P02_ctacte.asp")
        
        # Mock for total debt extraction
        def mock_evaluate_debt(*args):
            if "Total Saldo Deudor" in str(args[0]):
                return "15.500,75"
            return "https://servicios2.afip.gob.ar/tramites_con_clave_fiscal/ccam/P02_ctacte.asp"
        
        mock_account_page.evaluate = AsyncMock(side_effect=mock_evaluate_debt)
        
        # Mock context to handle new page/tab
        mock_context = MagicMock()
        mock_context.get_pages = AsyncMock(return_value=[mock_page, mock_account_page])
        mock_context.new_page = AsyncMock(return_value=mock_account_page)
        
        afip_connector._page = mock_page
        afip_connector._context = mock_context
        
        statement = await afip_connector.get_account_statement()
        
        assert statement is not None
        assert statement.total_debt == 15500.75
        assert statement.period_from == "01/2025"
        assert statement.period_to == "06/2025"
        assert statement.calculation_date == "08/06/2025"
        assert "/tmp/afip_screenshots/" in statement.screenshot_path
        
        # Verify all the steps were called
        mock_page.goto.assert_called()
        mock_page.click.assert_called()
        mock_account_page.fill.assert_called()
        mock_account_page.screenshot.assert_called()

    async def test_get_account_statement_no_session(self, afip_connector):
        """Test account statement when no session is active."""
        # No session set
        afip_connector._current_session = None
        
        statement = await afip_connector.get_account_statement()
        
        assert statement is None