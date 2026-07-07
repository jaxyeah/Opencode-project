# -*- coding: utf-8 -*-
"""Minimal: Load lens, set stop, check if file on disk is modified."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\dell\zemax-zpl-automation")

from zpl_toolkit.connection import ZemaxConnection
from zpl_toolkit.types import ConnectionConfig

LENS_FILE = r"C:\Users\dell\Desktop\Benz214-FOV9.16x3.42-LDA3.6-LOA0.8-VID3.8m-20260225-v1.zmx"

print("=== Minimal test: Load + modify, check if disk file changes ===")

config = ConnectionConfig()
conn = ZemaxConnection(config)
conn.connect()
system = conn.system

# Check what's loaded before
print(f"Before LoadFile - surfaces: {system.LDE.NumberOfSurfaces}")

# Load
system.LoadFile(LENS_FILE, False)
print(f"After LoadFile - surfaces: {system.LDE.NumberOfSurfaces}")

# Check if system.NeedsSave is True
try:
    needs_save = system.NeedsSave
    print(f"system.NeedsSave: {needs_save}")
except Exception as e:
    print(f"NeedsSave error: {e}")

# Check SystemFile
try:
    print(f"system.SystemFile: {system.SystemFile}")
except Exception as e:
    print(f"SystemFile error: {e}")

# Set stop semi-diameter
stop_n = system.LDE.StopSurface
print(f"Stop surface: {stop_n}, current SemiDia: {system.LDE.GetSurfaceAt(stop_n).SemiDiameter}")
system.LDE.GetSurfaceAt(stop_n).SemiDiameter = 2.0

# Check NeedsSave again
try:
    needs_save2 = system.NeedsSave
    print(f"After set SemiDia - NeedsSave: {needs_save2}")
except Exception as e:
    print(f"NeedsSave2 error: {e}")

# Check if Save exists and what it does
print("\nTesting Save methods...")
try:
    print(f"  system.Save() signature: {system.Save}")
except Exception:
    pass

# Check app methods
app = conn.application
# Look for file-related methods on app
for attr in dir(app):
    low = attr.lower()
    if any(x in low for x in ['save', 'load', 'open', 'file', 'close']):
        print(f"  app.{attr}")

# Also check: does the ZOSAPI_Connection save anything on close?
print(f"\nDisconnecting (this calls CloseApplication)...")
conn.disconnect()

# Check: does CloseApplication trigger a save?
# We can check by looking at the file modification time again
print("Check the file hash on disk after disconnect to see if it changed.")
