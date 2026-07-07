# -*- coding: utf-8 -*-
"""Connect to RUNNING OpticStudio via ZOS-API (not CreateNewApplication)."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load ZOS-API assemblies directly
import clr
import winreg

# Find OpticStudio
def find_zos():
    try:
        key = winreg.OpenKey(winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER),
                            r"Software\Zemax", 0, winreg.KEY_READ)
        path = winreg.QueryValueEx(key, "ZemaxRoot")[0]
        winreg.CloseKey(key)
        return path
    except:
        return r"C:\Program Files\Ansys Zemax OpticStudio 2025 R2.01"

zos_path = find_zos()
print(f"OpticStudio path: {zos_path}")

clr.AddReference(os.path.join(zos_path, r"ZOS-API\Libraries\ZOSAPI_NetHelper.dll"))
import ZOSAPI_NetHelper
ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize()
zdir = ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory()
print(f"ZOS dir: {zdir}")

clr.AddReference(os.path.join(zdir, "ZOSAPI.dll"))
clr.AddReference(os.path.join(zdir, "ZOSAPI_Interfaces.dll"))
import ZOSAPI

conn = ZOSAPI.ZOSAPI_Connection()
print(f"Connection created. IsAlive: {conn.IsAlive}")

# Try ConnectToApplication first
print("\n=== Trying ConnectToApplication ===")
try:
    conn.ConnectToApplication()
    print(f"  Success! IsAlive: {conn.IsAlive}")
except Exception as e:
    print(f"  Failed: {e}")

# If that failed, try ConnectAsExtension
print("\n=== Trying ConnectAsExtension ===")
try:
    # Need a new connection object
    conn2 = ZOSAPI.ZOSAPI_Connection()
    conn2.ConnectAsExtension()
    print(f"  Success! TheApp: {conn2.TheApp}")
except Exception as e:
    print(f"  Failed: {e}")

# Try CreateZemaxServer
print("\n=== Trying CreateZemaxServer ===")
try:
    conn3 = ZOSAPI.ZOSAPI_Connection()
    conn3.CreateZemaxServer()
    print(f"  Success! TheApp: {conn3.TheApp}")
except Exception as e:
    print(f"  Failed: {e}")

# Check existing connection's TheApp
print(f"\nCurrent conn.TheApp: {conn.TheApp}")

# If we got an application, check what's loaded
if conn.TheApp is not None:
    app = conn.TheApp
    system = app.PrimarySystem
    if system is not None:
        print(f"PrimarySystem surfaces: {system.LDE.NumberOfSurfaces}")
        try:
            print(f"SystemFile: {system.SystemFile}")
        except:
            pass

print("\nDone.")
