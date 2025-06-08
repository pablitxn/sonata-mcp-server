"""Tests for captcha solvers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.captcha.solvers import AntiCaptchaSolver, CapSolverAI, TwoCaptchaSolver


class TestCapSolverAI:
    """Tests for CapSolverAI."""
    
    @pytest.fixture
    def solver(self):
        """Creates a CapSolver solver."""
        return CapSolverAI("test_api_key")
    
    @pytest.fixture
    def mock_page(self):
        """Mock of a page."""
        page = MagicMock()
        page.evaluate = AsyncMock()
        page.screenshot = AsyncMock()
        return page
    
    def test_can_handle_supported_types(self, solver):
        """Verifies it can handle supported types."""
        assert solver.can_handle("recaptcha_v2") is True
        assert solver.can_handle("recaptcha_v3") is True
        assert solver.can_handle("hcaptcha") is True
        assert solver.can_handle("image") is True
    
    def test_can_handle_unsupported_types(self, solver):
        """Verifies it rejects unsupported types."""
        assert solver.can_handle("funcaptcha") is False
        assert solver.can_handle("geetest") is False
    
    @pytest.mark.asyncio
    async def test_solve_image_captcha(self, solver, mock_page):
        """Test for image captcha resolution."""
        # Mock of base64 image
        mock_page.evaluate.return_value = "base64_image_data"
        
        captcha_info = {
            "type": "image",
            "image_selector": "img.captcha"
        }
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await solver.solve(mock_page, captcha_info)
        
        assert result == "SIMULATED_CAPTCHA_SOLUTION"
        mock_page.evaluate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_solve_image_captcha_not_found(self, solver, mock_page):
        """Test when captcha image is not found."""
        mock_page.evaluate.return_value = None
        
        captcha_info = {
            "type": "image",
            "image_selector": "img.captcha"
        }
        
        result = await solver.solve(mock_page, captcha_info)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_solve_recaptcha_v2(self, solver, mock_page):
        """Test for ReCaptcha v2 resolution."""
        captcha_info = {
            "type": "recaptcha_v2",
            "site_key": "test_site_key"
        }
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await solver.solve(mock_page, captcha_info)
        
        assert result == "SIMULATED_RECAPTCHA_TOKEN"
    
    @pytest.mark.asyncio
    async def test_solve_recaptcha_without_site_key(self, solver, mock_page):
        """Test for ReCaptcha without site key."""
        captcha_info = {
            "type": "recaptcha_v2"
        }
        
        result = await solver.solve(mock_page, captcha_info)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_solve_unsupported_type(self, solver, mock_page):
        """Test with unsupported captcha type."""
        captcha_info = {
            "type": "unknown_type"
        }
        
        result = await solver.solve(mock_page, captcha_info)
        
        assert result is None


class TestTwoCaptchaSolver:
    """Tests for TwoCaptchaSolver."""
    
    @pytest.fixture
    def solver(self):
        """Creates a 2Captcha solver."""
        return TwoCaptchaSolver("test_api_key")
    
    @pytest.fixture
    def mock_page(self):
        """Mock of a page."""
        page = MagicMock()
        page.evaluate = AsyncMock()
        page.screenshot = AsyncMock()
        return page
    
    def test_can_handle_supported_types(self, solver):
        """Verifies it can handle supported types."""
        assert solver.can_handle("recaptcha_v2") is True
        assert solver.can_handle("recaptcha_v3") is True
        assert solver.can_handle("hcaptcha") is True
        assert solver.can_handle("image") is True
        assert solver.can_handle("text") is True
    
    @pytest.mark.asyncio
    async def test_solve_image_captcha(self, solver, mock_page):
        """Test for image captcha resolution."""
        captcha_info = {
            "type": "image",
            "image_selector": "img.captcha"
        }
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await solver.solve(mock_page, captcha_info)
        
        assert result == "SIMULATED_2CAPTCHA_SOLUTION"
        mock_page.screenshot.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_solve_text_captcha(self, solver, mock_page):
        """Test for text captcha resolution."""
        captcha_info = {
            "type": "text",
            "question": "What is 2+2?"
        }
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await solver.solve(mock_page, captcha_info)
        
        assert result == "SIMULATED_TEXT_ANSWER"
    
    @pytest.mark.asyncio
    async def test_solve_recaptcha_with_site_key(self, solver, mock_page):
        """Test for ReCaptcha resolution."""
        mock_page.evaluate.return_value = "https://example.com"
        
        captcha_info = {
            "type": "recaptcha_v2",
            "site_key": "test_site_key"
        }
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await solver.solve(mock_page, captcha_info)
        
        assert result == "SIMULATED_2CAPTCHA_RECAPTCHA_TOKEN"


class TestAntiCaptchaSolver:
    """Tests for AntiCaptchaSolver."""
    
    @pytest.fixture
    def solver(self):
        """Creates an Anti-Captcha solver."""
        return AntiCaptchaSolver("test_api_key")
    
    @pytest.fixture
    def mock_page(self):
        """Mock of a page."""
        return MagicMock()
    
    def test_can_handle_supported_types(self, solver):
        """Verifies it can handle supported types."""
        assert solver.can_handle("recaptcha_v2") is True
        assert solver.can_handle("recaptcha_v3") is True
        assert solver.can_handle("funcaptcha") is True
        assert solver.can_handle("image") is True
    
    def test_can_handle_unsupported_types(self, solver):
        """Verifies it rejects unsupported types."""
        assert solver.can_handle("text") is False
        assert solver.can_handle("geetest") is False
    
    @pytest.mark.asyncio
    async def test_solve_image_captcha(self, solver, mock_page):
        """Test for image captcha resolution."""
        captcha_info = {
            "type": "image"
        }
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await solver.solve(mock_page, captcha_info)
        
        assert result == "SIMULATED_ANTICAPTCHA_SOLUTION"
    
    @pytest.mark.asyncio
    async def test_solve_funcaptcha(self, solver, mock_page):
        """Test for FunCaptcha resolution."""
        captcha_info = {
            "type": "funcaptcha",
            "public_key": "test_public_key"
        }
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await solver.solve(mock_page, captcha_info)
        
        assert result == "SIMULATED_FUNCAPTCHA_TOKEN"
    
    @pytest.mark.asyncio
    async def test_solve_funcaptcha_without_key(self, solver, mock_page):
        """Test for FunCaptcha without public key."""
        captcha_info = {
            "type": "funcaptcha"
        }
        
        result = await solver.solve(mock_page, captcha_info)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_solve_recaptcha(self, solver, mock_page):
        """Test for ReCaptcha resolution."""
        captcha_info = {
            "type": "recaptcha_v2",
            "site_key": "test_site_key"
        }
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await solver.solve(mock_page, captcha_info)
        
        assert result == "SIMULATED_ANTICAPTCHA_RECAPTCHA_TOKEN"
    
    @pytest.mark.asyncio
    async def test_solve_unsupported_type(self, solver, mock_page):
        """Test with unsupported type."""
        captcha_info = {
            "type": "unsupported"
        }
        
        result = await solver.solve(mock_page, captcha_info)
        
        assert result is None