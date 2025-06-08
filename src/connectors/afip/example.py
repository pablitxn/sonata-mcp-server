"""Ejemplo de uso del connector AFIP."""

import asyncio
import os
from datetime import datetime

from src.browser.factory import BrowserEngineFactory
from src.browser.interfaces import BrowserConfig
from src.captcha.chain import CaptchaChain
from src.captcha.circuit_breaker import CircuitBreakerConfig
from src.captcha.solvers import CapSolverAI, TwoCaptchaSolver
from src.connectors.afip.connector import AFIPConnector
from src.connectors.afip.interfaces import AFIPCredentials, LoginStatus
from src.connectors.afip.session import EncryptedSessionStorage


async def main():
    """Ejemplo de uso del connector AFIP."""
    
    # Configurar el browser (usando Selenium)
    browser_config = BrowserConfig(
        headless=False,  # AFIP detecta headless, mejor usar con ventana
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    # Crear factory de browser
    browser_factory = BrowserEngineFactory()
    
    # Configurar almacenamiento seguro de sesiones
    session_storage = EncryptedSessionStorage(
        storage_path="/tmp/afip_sessions",
        # En producción, usar una clave segura desde variables de entorno
        encryption_key=os.getenv("AFIP_SESSION_KEY")
    )
    
    # Configurar cadena de captcha solvers
    captcha_chain = CaptchaChain()
    
    # Configuración del circuit breaker
    cb_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=timedelta(minutes=5),
        success_threshold=2
    )
    
    # Agregar solvers en orden de preferencia
    if os.getenv("CAPSOLVER_API_KEY"):
        captcha_chain.add_solver(
            CapSolverAI(os.getenv("CAPSOLVER_API_KEY")),
            cb_config
        )
    
    if os.getenv("TWOCAPTCHA_API_KEY"):
        captcha_chain.add_solver(
            TwoCaptchaSolver(os.getenv("TWOCAPTCHA_API_KEY")),
            cb_config
        )
    
    # Crear el connector
    connector = AFIPConnector(
        browser_factory=browser_factory,
        session_storage=session_storage,
        captcha_chain=captcha_chain,
        browser_config=browser_config
    )
    
    try:
        # Credenciales (en producción, obtener de forma segura)
        credentials = AFIPCredentials(
            cuit=os.getenv("AFIP_CUIT", "20-12345678-9"),
            password=os.getenv("AFIP_PASSWORD", "password")
        )
        
        print(f"Iniciando sesión en AFIP para CUIT: {credentials.cuit}")
        
        # Intentar login
        login_status = await connector.login(credentials)
        
        if login_status == LoginStatus.SUCCESS:
            print("✅ Login exitoso!")
            
            # Obtener información de la sesión
            session = await connector.get_session()
            if session:
                print(f"Sesión válida hasta: {session.expires_at}")
            
            # Consultar pagos pendientes
            print("\nConsultando pagos pendientes...")
            payments = await connector.get_pending_payments()
            
            if payments:
                print(f"\n📋 Se encontraron {len(payments)} pagos pendientes:")
                
                total = 0
                for payment in payments:
                    print(f"\n- ID: {payment.id}")
                    print(f"  Descripción: {payment.description}")
                    print(f"  Monto: ${payment.amount:,.2f}")
                    print(f"  Vencimiento: {payment.due_date.strftime('%d/%m/%Y')}")
                    print(f"  Estado: {payment.status.value}")
                    print(f"  Tipo: {payment.tax_type}")
                    print(f"  Período: {payment.period}")
                    
                    total += payment.amount
                
                print(f"\n💰 Total pendiente: ${total:,.2f}")
            else:
                print("✨ No hay pagos pendientes!")
            
        elif login_status == LoginStatus.CAPTCHA_REQUIRED:
            print("❌ No se pudo resolver el captcha automáticamente")
            
        elif login_status == LoginStatus.CERTIFICATE_REQUIRED:
            print("🔐 Se requiere certificado digital para el login")
            
        else:
            print("❌ Error en el login")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        # Cerrar sesión y limpiar recursos
        print("\nCerrando sesión...")
        await connector.logout()
        print("✅ Sesión cerrada")


# Ejemplo de uso con manejo de sesión existente
async def example_with_session_restore():
    """Ejemplo restaurando una sesión guardada."""
    
    browser_factory = BrowserEngineFactory()
    session_storage = EncryptedSessionStorage("/tmp/afip_sessions")
    
    connector = AFIPConnector(
        browser_factory=browser_factory,
        session_storage=session_storage
    )
    
    cuit = "20-12345678-9"
    
    # Intentar cargar sesión guardada
    saved_session = await session_storage.load(cuit)
    
    if saved_session and await session_storage.is_valid(saved_session):
        print("📂 Sesión guardada encontrada, intentando restaurar...")
        
        if await connector.restore_session(saved_session):
            print("✅ Sesión restaurada exitosamente!")
            
            # Usar la sesión restaurada
            payments = await connector.get_pending_payments()
            print(f"Pagos pendientes: {len(payments)}")
        else:
            print("❌ No se pudo restaurar la sesión")
    else:
        print("No hay sesión válida guardada")


if __name__ == "__main__":
    # Para ejecutar:
    # python -m src.connectors.afip.example
    
    from datetime import timedelta
    
    asyncio.run(main())
    
    # Ejemplo de restauración de sesión
    # asyncio.run(example_with_session_restore())