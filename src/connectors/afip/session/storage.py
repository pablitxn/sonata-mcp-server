"""Implementaciones de almacenamiento de sesiones."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from cryptography.fernet import Fernet

from src.connectors.afip.interfaces import AFIPSession, ISessionStorage

logger = structlog.get_logger()


class InMemorySessionStorage(ISessionStorage):
    """Almacenamiento de sesiones en memoria (para testing)."""
    
    def __init__(self):
        """Inicializa el almacenamiento en memoria."""
        self._sessions: Dict[str, AFIPSession] = {}
        self.logger = logger.bind(storage="memory")
    
    async def save(self, session: AFIPSession) -> bool:
        """Guarda una sesión en memoria.
        
        Args:
            session: Sesión a guardar.
            
        Returns:
            True si se guardó correctamente.
        """
        try:
            self._sessions[session.cuit] = session
            self.logger.info("session_saved", cuit=session.cuit)
            return True
        except Exception as e:
            self.logger.error("session_save_error", error=str(e))
            return False
    
    async def load(self, cuit: str) -> Optional[AFIPSession]:
        """Carga una sesión de memoria.
        
        Args:
            cuit: CUIT asociado a la sesión.
            
        Returns:
            Sesión guardada o None.
        """
        session = self._sessions.get(cuit)
        if session:
            self.logger.info("session_loaded", cuit=cuit)
        else:
            self.logger.debug("session_not_found", cuit=cuit)
        return session
    
    async def delete(self, cuit: str) -> bool:
        """Elimina una sesión de memoria.
        
        Args:
            cuit: CUIT asociado a la sesión.
            
        Returns:
            True si se eliminó correctamente.
        """
        if cuit in self._sessions:
            del self._sessions[cuit]
            self.logger.info("session_deleted", cuit=cuit)
            return True
        return False
    
    async def is_valid(self, session: AFIPSession) -> bool:
        """Verifica si una sesión es válida.
        
        Args:
            session: Sesión a verificar.
            
        Returns:
            True si la sesión es válida.
        """
        if not session.is_valid:
            return False
        
        # Verificar expiración
        if datetime.now() >= session.expires_at:
            self.logger.warning("session_expired", cuit=session.cuit)
            return False
        
        return True


class EncryptedSessionStorage(ISessionStorage):
    """Almacenamiento de sesiones encriptado en disco."""
    
    def __init__(self, storage_path: str, encryption_key: Optional[str] = None):
        """Inicializa el almacenamiento encriptado.
        
        Args:
            storage_path: Ruta donde guardar las sesiones.
            encryption_key: Clave de encriptación (se genera una si no se proporciona).
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = logger.bind(storage="encrypted", path=str(self.storage_path))
        
        # Generar o usar clave de encriptación
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        else:
            # Generar nueva clave y guardarla
            key = Fernet.generate_key()
            self.fernet = Fernet(key)
            self._save_encryption_key(key)
    
    def _save_encryption_key(self, key: bytes) -> None:
        """Guarda la clave de encriptación de forma segura.
        
        Args:
            key: Clave de encriptación.
        """
        key_path = self.storage_path / ".encryption_key"
        key_path.write_bytes(key)
        # Establecer permisos restrictivos
        os.chmod(key_path, 0o600)
        self.logger.info("encryption_key_saved")
    
    def _get_session_path(self, cuit: str) -> Path:
        """Obtiene la ruta del archivo de sesión.
        
        Args:
            cuit: CUIT de la sesión.
            
        Returns:
            Ruta del archivo.
        """
        # Sanitizar CUIT para nombre de archivo
        safe_cuit = cuit.replace("-", "")
        return self.storage_path / f"session_{safe_cuit}.enc"
    
    def _serialize_session(self, session: AFIPSession) -> Dict[str, Any]:
        """Serializa una sesión a diccionario.
        
        Args:
            session: Sesión a serializar.
            
        Returns:
            Diccionario serializable.
        """
        return {
            "session_id": session.session_id,
            "cuit": session.cuit,
            "cookies": session.cookies,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "is_valid": session.is_valid
        }
    
    def _deserialize_session(self, data: Dict[str, Any]) -> AFIPSession:
        """Deserializa un diccionario a sesión.
        
        Args:
            data: Datos de la sesión.
            
        Returns:
            Sesión deserializada.
        """
        return AFIPSession(
            session_id=data["session_id"],
            cuit=data["cuit"],
            cookies=data["cookies"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            is_valid=data["is_valid"]
        )
    
    async def save(self, session: AFIPSession) -> bool:
        """Guarda una sesión encriptada.
        
        Args:
            session: Sesión a guardar.
            
        Returns:
            True si se guardó correctamente.
        """
        try:
            # Serializar sesión
            session_data = self._serialize_session(session)
            json_data = json.dumps(session_data)
            
            # Encriptar
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            # Guardar
            session_path = self._get_session_path(session.cuit)
            session_path.write_bytes(encrypted_data)
            
            # Establecer permisos restrictivos
            os.chmod(session_path, 0o600)
            
            self.logger.info(
                "session_saved_encrypted",
                cuit=session.cuit,
                path=str(session_path)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "session_save_error",
                error=str(e),
                exc_info=True
            )
            return False
    
    async def load(self, cuit: str) -> Optional[AFIPSession]:
        """Carga una sesión encriptada.
        
        Args:
            cuit: CUIT asociado a la sesión.
            
        Returns:
            Sesión guardada o None.
        """
        try:
            session_path = self._get_session_path(cuit)
            
            if not session_path.exists():
                self.logger.debug("session_file_not_found", cuit=cuit)
                return None
            
            # Leer y desencriptar
            encrypted_data = session_path.read_bytes()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            
            # Deserializar
            session_data = json.loads(decrypted_data.decode())
            session = self._deserialize_session(session_data)
            
            self.logger.info("session_loaded_decrypted", cuit=cuit)
            return session
            
        except Exception as e:
            self.logger.error(
                "session_load_error",
                error=str(e),
                cuit=cuit,
                exc_info=True
            )
            return None
    
    async def delete(self, cuit: str) -> bool:
        """Elimina una sesión encriptada.
        
        Args:
            cuit: CUIT asociado a la sesión.
            
        Returns:
            True si se eliminó correctamente.
        """
        try:
            session_path = self._get_session_path(cuit)
            
            if session_path.exists():
                session_path.unlink()
                self.logger.info("session_deleted", cuit=cuit)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(
                "session_delete_error",
                error=str(e),
                cuit=cuit
            )
            return False
    
    async def is_valid(self, session: AFIPSession) -> bool:
        """Verifica si una sesión es válida.
        
        Args:
            session: Sesión a verificar.
            
        Returns:
            True si la sesión es válida.
        """
        if not session.is_valid:
            return False
        
        # Verificar expiración
        if datetime.now() >= session.expires_at:
            self.logger.warning(
                "session_expired",
                cuit=session.cuit,
                expired_at=session.expires_at.isoformat()
            )
            # Marcar como inválida y guardar
            session.is_valid = False
            await self.save(session)
            return False
        
        return True