# -*- coding: utf-8 -*-
"""Explore ALL file-related methods on ZOSAPI Application and System."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\dell\zemax-zpl-automation")

from zpl_toolkit.connection import ZemaxConnection
from zpl_toolkit.types import ConnectionConfig

config = ConnectionConfig()
conn = ZemaxConnection(config)
conn.connect()

app = conn.application
system = conn.system

# Full list of app methods
print("=== Application methods ===")
methods = sorted([m for m in dir(app) if not m.startswith('_') and not m.startswith('get_') and not m.startswith('set_')])
for m in methods:
    print(f"  app.{m}")

print("\n=== System methods (file-related) ===")
for m in sorted(dir(system)):
    low = m.lower()
    if any(x in low for x in ['file', 'save', 'load', 'open', 'close', 'new', 'copy']):
        print(f"  system.{m}")

# Check if there's a way to attach to running instance
print("\n=== ZOSAPI_Connection methods ===")
# Need to get the connection object
import clr
clr.AddReference(r"C:\Program Files\Ansys Zemax OpticStudio 2025 R2.01\ZOSAPI_NetHelper.dll")
import ZOSAPI_NetHelper
zdir = ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory()
clr.AddReference(os.path.join(zdir, "ZOSAPI.dll"))
clr.AddReference(os.path.join(zdir, "ZOSAPI_Interfaces.dll"))
import ZOSAPI

conn2 = ZOSAPI.ZOSAPI_Connection()
print("ZOSAPI_Connection methods:")
for m in sorted(dir(conn2)):
    if not m.startswith('_'):
        print(f"  conn.{m}")

# Check if there's WaitForConnection or IsAlive
print("\n=== Checking for existing instance connection ===")
try:
    alive = conn2.IsAlive
    print(f"  IsAlive: {alive}")
except:
    print("  IsAlive: not available")
try:
    conn2.WaitForConnection(1000)
    print("  WaitForConnection: succeeded")
except Exception as e:
    print(f"  WaitForConnection: {e}")

conn.disconnect()
print("\nDone.")
