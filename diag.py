# -*- coding: utf-8 -*-
"""Diagnose file loading and MTF reading."""
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\dell\zemax-zpl-automation")

from zpl_toolkit.connection import ZemaxConnection
from zpl_toolkit.types import ConnectionConfig

LENS_FILE = r"C:\Users\dell\Desktop\Benz214-FOV9.16x3.42-LDA3.6-LOA0.8-VID3.8m-20260225-v1.zmx"

print("=== DIAGNOSTIC: Check loaded file state ===")

config = ConnectionConfig()
conn = ZemaxConnection(config)
conn.connect()

system = conn.system

# BEFORE loading: check what's currently open
print("\n[Before LoadFile]")
ld = system.LDE
print(f"  Surfaces: {ld.NumberOfSurfaces}")
try:
    print(f"  Stop surface: {ld.StopSurface}")
    ss = ld.GetSurfaceAt(ld.StopSurface)
    print(f"  Stop type: {ss.TypeName}, SemiDia: {ss.SemiDiameter}")
except Exception as e:
    print(f"  Stop error: {e}")

try:
    sd = system.SystemData
    print(f"  Aperture: {sd.Aperture.ApertureValue} ({sd.Aperture.ApertureType})")
    print(f"  Fields: {sd.Fields.NumberOfFields}")
except Exception as e:
    print(f"  SystemData error: {e}")

# NOW try to load the file
print(f"\n[LoadFile] Loading: {os.path.basename(LENS_FILE)}")
print(f"  Calling system.LoadFile('{LENS_FILE}', False)...")
try:
    system.LoadFile(LENS_FILE, False)
    print("  LoadFile completed (no exception)")
except Exception as e:
    print(f"  LoadFile EXCEPTION: {e}")

# AFTER loading: verify
print("\n[After LoadFile]")
print(f"  Surfaces: {ld.NumberOfSurfaces}")
try:
    print(f"  Stop surface: {ld.StopSurface}")
    ss = ld.GetSurfaceAt(ld.StopSurface)
    print(f"  Stop type: {ss.TypeName}, SemiDia: {ss.SemiDiameter}")
except Exception as e:
    print(f"  Stop error: {e}")

try:
    sd = system.SystemData
    print(f"  Aperture: {sd.Aperture.ApertureValue} ({sd.Aperture.ApertureType})")
    print(f"  Fields: {sd.Fields.NumberOfFields}")
    print(f"  Waves: {sd.Wavelengths.NumberOfWavelengths}")
    # Check file path of loaded file
    try:
        print(f"  SystemFile: {system.SystemFile if hasattr(system, 'SystemFile') else 'N/A'}")
    except:
        pass
except Exception as e:
    print(f"  SystemData error: {e}")

# Try get current file name
try:
    tool = system.Tools
    print(f"  Tools.CurrentFile: {tool.CurrentFile if hasattr(tool, 'CurrentFile') else 'no attr'}")
except Exception as e:
    print(f"  CurrentFile error: {e}")

conn.disconnect()
print("\nDone.")
