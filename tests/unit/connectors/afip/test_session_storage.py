"""Tests para el almacenamiento de sesiones."""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.connectors.afip.interfaces import AFIPSession
from src.connectors.afip.session.storage import EncryptedSessionStorage, InMemorySessionStorage


class TestInMemorySessionStorage:
    """Tests para el almacenamiento en memoria."""
    
    @pytest.fixture
    def storage(self):
        """Crea un almacenamiento en memoria."""
        return InMemorySessionStorage()
    
    @pytest.fixture
    def sample_session(self):
        """Crea una sesión de ejemplo."""
        return AFIPSession(
            session_id="test_session_123",
            cuit="20-12345678-9",
            cookies={"session": "abc123", "token": "xyz789"},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=2),
            is_valid=True
        )
    
    @pytest.mark.asyncio
    async def test_save_and_load_session(self, storage, sample_session):
        """Verifica guardar y cargar una sesión."""
        # Guardar
        result = await storage.save(sample_session)
        assert result is True
        
        # Cargar
        loaded = await storage.load(sample_session.cuit)
        assert loaded is not None
        assert loaded.session_id == sample_session.session_id
        assert loaded.cuit == sample_session.cuit
        assert loaded.cookies == sample_session.cookies
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, storage):
        """Verifica cargar una sesión que no existe."""
        loaded = await storage.load("99-99999999-9")
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_delete_session(self, storage, sample_session):
        """Verifica eliminar una sesión."""
        # Guardar
        await storage.save(sample_session)
        
        # Eliminar
        result = await storage.delete(sample_session.cuit)
        assert result is True
        
        # Verificar que no existe
        loaded = await storage.load(sample_session.cuit)
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, storage):
        """Verifica eliminar una sesión que no existe."""
        result = await storage.delete("99-99999999-9")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_valid_with_valid_session(self, storage, sample_session):
        """Verifica validación de sesión válida."""
        is_valid = await storage.is_valid(sample_session)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_is_valid_with_expired_session(self, storage):
        """Verifica validación de sesión expirada."""
        expired_session = AFIPSession(
            session_id="expired_123",
            cuit="20-12345678-9",
            cookies={},
            created_at=datetime.now() - timedelta(hours=3),
            expires_at=datetime.now() - timedelta(hours=1),
            is_valid=True
        )
        
        is_valid = await storage.is_valid(expired_session)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_is_valid_with_invalid_session(self, storage):
        """Verifica validación de sesión marcada como inválida."""
        invalid_session = AFIPSession(
            session_id="invalid_123",
            cuit="20-12345678-9",
            cookies={},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=2),
            is_valid=False
        )
        
        is_valid = await storage.is_valid(invalid_session)
        assert is_valid is False


class TestEncryptedSessionStorage:
    """Tests para el almacenamiento encriptado."""
    
    @pytest.fixture
    def temp_dir(self):
        """Crea un directorio temporal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Crea un almacenamiento encriptado."""
        return EncryptedSessionStorage(temp_dir)
    
    @pytest.fixture
    def sample_session(self):
        """Crea una sesión de ejemplo."""
        return AFIPSession(
            session_id="encrypted_session_123",
            cuit="20-12345678-9",
            cookies={"session": "abc123", "token": "xyz789"},
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=2),
            is_valid=True
        )
    
    @pytest.mark.asyncio
    async def test_save_creates_encrypted_file(self, storage, sample_session, temp_dir):
        """Verifica que se cree un archivo encriptado."""
        result = await storage.save(sample_session)
        assert result is True
        
        # Verificar que el archivo existe
        session_path = Path(temp_dir) / "session_20123456789.enc"
        assert session_path.exists()
        
        # Verificar que está encriptado (no contiene texto plano)
        content = session_path.read_bytes()
        assert b"abc123" not in content  # Cookie no debe estar en texto plano
        assert b"20-12345678-9" not in content  # CUIT no debe estar en texto plano
    
    @pytest.mark.asyncio
    async def test_load_decrypts_correctly(self, storage, sample_session):
        """Verifica que la carga desencripte correctamente."""
        # Guardar
        await storage.save(sample_session)
        
        # Cargar
        loaded = await storage.load(sample_session.cuit)
        assert loaded is not None
        assert loaded.session_id == sample_session.session_id
        assert loaded.cookies == sample_session.cookies
        assert loaded.cuit == sample_session.cuit
    
    @pytest.mark.asyncio
    async def test_encryption_key_generation(self, temp_dir):
        """Verifica la generación automática de clave de encriptación."""
        storage = EncryptedSessionStorage(temp_dir)
        
        # Verificar que se generó la clave
        key_path = Path(temp_dir) / ".encryption_key"
        assert key_path.exists()
        
        # Verificar permisos restrictivos
        stat_info = os.stat(key_path)
        assert stat_info.st_mode & 0o777 == 0o600
    
    @pytest.mark.asyncio
    async def test_custom_encryption_key(self, temp_dir, sample_session):
        """Verifica el uso de clave de encriptación personalizada."""
        from cryptography.fernet import Fernet
        
        # Generar clave personalizada
        custom_key = Fernet.generate_key()
        
        # Crear storage con clave personalizada
        storage = EncryptedSessionStorage(temp_dir, custom_key)
        
        # Guardar y cargar
        await storage.save(sample_session)
        loaded = await storage.load(sample_session.cuit)
        
        assert loaded is not None
        assert loaded.session_id == sample_session.session_id
    
    @pytest.mark.asyncio
    async def test_file_permissions(self, storage, sample_session, temp_dir):
        """Verifica que los archivos tengan permisos restrictivos."""
        await storage.save(sample_session)
        
        session_path = Path(temp_dir) / "session_20123456789.enc"
        stat_info = os.stat(session_path)
        
        # Verificar que solo el owner puede leer/escribir
        assert stat_info.st_mode & 0o777 == 0o600
    
    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self, storage, temp_dir):
        """Verifica el manejo de archivos corruptos."""
        # Crear archivo corrupto
        corrupted_path = Path(temp_dir) / "session_20999999999.enc"
        corrupted_path.write_bytes(b"corrupted data")
        
        # Intentar cargar
        loaded = await storage.load("20-99999999-9")
        assert loaded is None
    
    @pytest.mark.asyncio
    async def test_expired_session_invalidation(self, storage):
        """Verifica que las sesiones expiradas se marquen como inválidas."""
        expired_session = AFIPSession(
            session_id="expired_123",
            cuit="20-88888888-8",
            cookies={},
            created_at=datetime.now() - timedelta(hours=3),
            expires_at=datetime.now() - timedelta(hours=1),
            is_valid=True
        )
        
        # Guardar sesión expirada
        await storage.save(expired_session)
        
        # Verificar validez
        is_valid = await storage.is_valid(expired_session)
        assert is_valid is False
        
        # Cargar y verificar que se marcó como inválida
        loaded = await storage.load(expired_session.cuit)
        assert loaded is not None
        assert loaded.is_valid is False