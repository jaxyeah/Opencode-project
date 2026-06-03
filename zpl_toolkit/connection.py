"""ZOS-API Connection Manager for OpticStudio."""

import logging
import os
import winreg

import clr

from zpl_toolkit.types import ConnectionConfig

logger = logging.getLogger(__name__)


class ConnectionException(Exception):
    """Raised when OpticStudio cannot be found or connected to."""


class LicenseException(Exception):
    """Raised when the OpticStudio license does not permit ZOS-API access."""


class InitializationException(Exception):
    """Raised when ZOS-API initialization fails."""


class SystemNotPresentException(Exception):
    """Raised when no PrimarySystem is available."""


class ZemaxConnection:
    """Manages a ZOS-API connection to OpticStudio.

    Usage:
        config = ConnectionConfig()
        with ZemaxConnection(config) as zos:
            print(zos.is_connected)
            # use zos.application, zos.system
    """

    _WELL_KNOWN_PATH = r"C:\Program Files\Ansys Zemax OpticStudio 2025 R2.01"

    def __init__(self, config: ConnectionConfig):
        self._config = config
        self._app = None
        self._connection = None
        self._system = None
        self._zosapi_dir = None
        self._connected = False

    # ── public API ──────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def application(self):
        """The ZOSAPI Application object. None if not connected."""
        return self._app

    @property
    def system(self):
        """The PrimarySystem. None if no lens is loaded."""
        return self._system

    def connect(self):
        """Establish connection to OpticStudio. Idempotent."""
        if self._connected:
            logger.debug("Already connected – skipping")
            return

        self._find_opticstudio()
        self._load_zosapi()
        self._create_connection()
        logger.info("Connected to OpticStudio at %s", self._zosapi_dir)

    def disconnect(self):
        """Disconnect and release COM resources. Idempotent."""
        try:
            if self._app is not None:
                self._app.CloseApplication()
        except Exception:
            logger.warning("Error closing application", exc_info=True)
        finally:
            self._app = None
            self._system = None
            self._connection = None
            self._connected = False
            logger.debug("Disconnected")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
        return False

    # ── internal helpers ────────────────────────────────────────

    def _find_opticstudio(self):
        """Locate OpticStudio installation via registry then fallbacks."""
        path = self._read_registry_path()
        if path is None and self._config.opticstudio_path:
            path = self._config.opticstudio_path
            logger.debug("Using config-provided path: %s", path)
        if path is None:
            path = self._WELL_KNOWN_PATH
            logger.debug("Using well-known path: %s", path)
        self._search_path = path

    @staticmethod
    def _read_registry_path():
        try:
            key = winreg.OpenKey(
                winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER),
                r"Software\Zemax",
                0,
                winreg.KEY_READ,
            )
            data = winreg.QueryValueEx(key, "ZemaxRoot")
            winreg.CloseKey(key)
            return data[0]
        except OSError:
            logger.debug("Registry key Software\\Zemax not found")
            return None

    def _load_zosapi(self):
        """Load ZOS-API .NET assemblies."""
        # Load NetHelper
        nethelper_reg = self._registry_zosapi_path()
        if nethelper_reg:
            nethelper = nethelper_reg
        else:
            nethelper = os.path.join(self._search_path, "ZOSAPI_NetHelper.dll")

        if not os.path.exists(nethelper):
            raise ConnectionException(
                f"ZOSAPI_NetHelper.dll not found at {nethelper}"
            )

        clr.AddReference(nethelper)
        import ZOSAPI_NetHelper  # noqa: E402

        # Initialize – try auto, then search_path, then well-known
        paths_to_try = [
            None,  # auto-detect
            self._search_path,
            self._WELL_KNOWN_PATH,
        ]

        initialized = False
        for attempt_path in paths_to_try:
            if attempt_path is None:
                initialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize()
                logger.debug("Initialize(auto): %s", initialized)
            else:
                initialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(
                    attempt_path
                )
                logger.debug("Initialize(%s): %s", attempt_path, initialized)
            if initialized:
                self._search_path = attempt_path or self._WELL_KNOWN_PATH
                break

        if not initialized:
            raise InitializationException(
                "Unable to initialize ZOS-API. Tried auto-detect, "
                f"{self._search_path}, {self._WELL_KNOWN_PATH}"
            )

        self._zosapi_dir = ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory()
        logger.debug("ZOS directory: %s", self._zosapi_dir)

        # Load main assemblies
        clr.AddReference(os.path.join(self._zosapi_dir, "ZOSAPI.dll"))
        clr.AddReference(os.path.join(self._zosapi_dir, "ZOSAPI_Interfaces.dll"))
        import ZOSAPI  # noqa: E402,F811

        self._ZOSAPI = ZOSAPI

    def _registry_zosapi_path(self):
        """Get ZOS-API helper path from registry (Documents/Zemax/ZOS-API/Libraries)."""
        registry_root = self._read_registry_path()
        if registry_root:
            candidate = os.path.join(
                registry_root, r"ZOS-API\Libraries\ZOSAPI_NetHelper.dll"
            )
            if os.path.exists(candidate):
                return candidate
        return None

    def _create_connection(self):
        """Create the actual ZOS-API connection and application."""
        self._connection = self._ZOSAPI.ZOSAPI_Connection()
        if self._connection is None:
            raise ConnectionException("Unable to create ZOSAPI_Connection")

        self._app = self._connection.CreateNewApplication()
        if self._app is None:
            raise ConnectionException("Unable to acquire ZOSAPI application")

        if not self._app.IsValidLicenseForAPI:
            self._app.CloseApplication()
            self._app = None
            raise LicenseException("License is not valid for ZOS-API access")

        self._system = self._app.PrimarySystem
        self._connected = True
