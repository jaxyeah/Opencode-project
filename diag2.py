# -*- coding: utf-8 -*-
"""Diagnose: Check if a running OpticStudio instance exists and probe connection modes."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\dell\zemax-zpl-automation")

from zpl_toolkit.connection import ZemaxConnection
from zpl_toolkit.types import ConnectionConfig

LENS_FILE = r"C:\Users\dell\Desktop\Benz214-FOV9.16x3.42-LDA3.6-LOA0.8-VID3.8m-20260225-v1.zmx"

print("=== Test 1: What happens with LoadFile(True) vs LoadFile(False) ===")

config = ConnectionConfig()
conn = ZemaxConnection(config)
conn.connect()
system = conn.system

# Check if a real lens is already loaded (suggesting we connected to running instance)
ld = system.LDE
print(f"Surfaces after connect: {ld.NumberOfSurfaces}")

# TEST A: Load with saveCurrentFile=True
system.LoadFile(LENS_FILE, True)
print(f"A) LoadFile(True)  -> Surfaces: {ld.NumberOfSurfaces}, Stop: {ld.StopSurface}, StopSemiDia: {ld.GetSurfaceAt(ld.StopSurface).SemiDiameter}")

conn.disconnect()

# TEST B: Fresh connection, LoadFile with saveCurrentFile=False
conn2 = ZemaxConnection(config)
conn2.connect()
system2 = conn2.system
system2.LoadFile(LENS_FILE, False)
print(f"B) LoadFile(False) -> Surfaces: {system2.LDE.NumberOfSurfaces}, Stop: {system2.LDE.StopSurface}, StopSemiDia: {system2.LDE.GetSurfaceAt(system2.LDE.StopSurface).SemiDiameter}")
conn2.disconnect()

# TEST C: Check if OpticStudio process is running
print("\n=== Test 2: Running OpticStudio processes ===")
import subprocess
result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq OpticStudio.exe'], capture_output=True, text=True)
print(result.stdout.strip())

print("\n=== Test 3: Try ZOSAPI_Connection methods ===")
config3 = ConnectionConfig()
conn3 = ZemaxConnection(config3)
conn3.connect()
system3 = conn3.system

# What methods does system have?
print("System methods related to file:")
for attr in dir(system3):
    if 'file' in attr.lower() or 'save' in attr.lower() or 'load' in attr.lower() or 'open' in attr.lower():
        print(f"  system.{attr}")

# What about the application object?
print("\nApplication methods related to file:")
app = conn3.application
for attr in dir(app):
    if 'file' in attr.lower() or 'save' in attr.lower() or 'load' in attr.lower() or 'open' in attr.lower():
        print(f"  app.{attr}")

conn3.disconnect()
print("\nDone.")
