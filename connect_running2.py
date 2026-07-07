# -*- coding: utf-8 -*-
"""Test ConnectAsExtension / ConnectToApplication for running OpticStudio."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import clr

ZOS_PATH = r"C:\Program Files\Ansys Zemax OpticStudio 2025 R2.01"

# Try initializing with explicit path
clr.AddReference(os.path.join(ZOS_PATH, "ZOSAPI_NetHelper.dll"))
import ZOSAPI_NetHelper

# Try multiple paths
for path in [None, ZOS_PATH]:
    try:
        if path is None:
            ok = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize()
        else:
            ok = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(path)
        if ok:
            zdir = ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory()
            print(f"Init OK. ZOS dir: {zdir}")
            break
    except Exception as e:
        print(f"Init({path}) failed: {e}")

if zdir is None:
    # Try the well-known ZOS-API assembly location
    zdir = os.path.join(ZOS_PATH, "ZOS-API", "Libraries")
    print(f"Fallback ZOS dir: {zdir}")

# Load assemblies
zosapi_dll = os.path.join(zdir, "ZOSAPI.dll")
zosapi_interfaces = os.path.join(zdir, "ZOSAPI_Interfaces.dll")
print(f"Loading {zosapi_dll}")
print(f"Loading {zosapi_interfaces}")

if os.path.exists(zosapi_dll) and os.path.exists(zosapi_interfaces):
    clr.AddReference(zosapi_dll)
    clr.AddReference(zosapi_interfaces)
else:
    # Try program files path
    alt_dll = os.path.join(ZOS_PATH, "ZOSAPI.dll")
    print(f"Trying alternative: {alt_dll}")
    clr.AddReference(alt_dll)
    clr.AddReference(os.path.join(ZOS_PATH, "ZOSAPI_Interfaces.dll"))

import ZOSAPI

# Now try connection methods
print("\n=== Method 1: ConnectAsExtension ===")
try:
    conn1 = ZOSAPI.ZOSAPI_Connection()
    conn1.ConnectAsExtension()
    app = conn1.TheApp
    system = app.PrimarySystem
    print(f"Success! Surfaces: {system.LDE.NumberOfSurfaces}")
    print(f"SystemFile: {system.SystemFile}")
except Exception as e:
    print(f"Failed: {e}")

print("\n=== Method 2: ConnectToApplication ===")
try:
    conn2 = ZOSAPI.ZOSAPI_Connection()
    conn2.ConnectToApplication()
    app = conn2.TheApp
    system = app.PrimarySystem
    print(f"Success! Surfaces: {system.LDE.NumberOfSurfaces}")
    print(f"SystemFile: {system.SystemFile}")
except Exception as e:
    print(f"Failed: {e}")

print("\n=== Method 3: CreateNewApplication (for comparison) ===")
try:
    conn3 = ZOSAPI.ZOSAPI_Connection()
    app3 = conn3.CreateNewApplication()
    system3 = app3.PrimarySystem
    print(f"Success! Surfaces: {system3.LDE.NumberOfSurfaces}")
except Exception as e:
    print(f"Failed: {e}")

print("\nDone.")
