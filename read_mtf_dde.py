# -*- coding: utf-8 -*-
"""Connect to RUNNING OpticStudio via DDE, set stop SemiDia=2mm, read MTF at 6 lp/mm."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pyzdde.zdde as pyz

LENS_FILE = r"C:\Users\dell\Desktop\Benz214-FOV9.16x3.42-LDA3.6-LOA0.8-VID3.8m-20260225-v1.zmx"
TARGET_FREQ = 6.0
STOP_SEMI_DIAMETER = 2.0

print("=" * 60)
print("PyZDDE DDE: Connect to RUNNING OpticStudio")
print("=" * 60)

link = pyz.PyZDDE()
status = link.zDDEInit()
if status != 0:
    print("ERROR: Cannot connect via DDE. Is OpticStudio running?")
    sys.exit(1)
print("Connected to running OpticStudio.")

# Check what's currently loaded
current = link.zGetFile()
print(f"Current file: {current}")

if os.path.basename(LENS_FILE) not in current:
    print(f"Loading: {os.path.basename(LENS_FILE)}...")
    link.zLoadFile(LENS_FILE)
    print("Loaded.")

n_surf = link.zGetNumSurf()
stop_surf = link.zGetStop()
print(f"Surfaces: {n_surf}, Stop: {stop_surf}")

old_semi = link.zGetSurfaceData(stop_surf, 13)
print(f"Current stop SemiDia: {old_semi}")

print(f"\nSetting stop SemiDia = {STOP_SEMI_DIAMETER} mm...")
link.zSetSurfaceData(stop_surf, 13, STOP_SEMI_DIAMETER)
link.zPushLens(1)
new_semi = link.zGetSurfaceData(stop_surf, 13)
print(f"Verified SemiDia: {new_semi}")

# Get fields
n_fields = link.zGetField(0)[0]
print(f"Fields: {n_fields}")
for i in range(1, n_fields + 1):
    fx, fy, fw = link.zGetField(i)
    print(f"  F{i}: x={fx:+.4f}, y={fy:+.4f}")

# Run MTF at 6 lp/mm via DDE
print(f"\n{'=' * 60}")
print(f"MTF at {TARGET_FREQ} lp/mm (Stop SemiDia = {STOP_SEMI_DIAMETER} mm)")
print(f"{'=' * 60}")

for field in range(1, n_fields + 1):
    fx, fy, fw = link.zGetField(field)
    mtf_tan = link.zGetMTF(1, 1, field, 0, TARGET_FREQ)
    mtf_sag = link.zGetMTF(1, 1, field, 1, TARGET_FREQ)
    mtf_avg = link.zGetMTF(1, 1, field, 2, TARGET_FREQ)
    print(f"F{field:2d} (x={fx:+.4f}, y={fy:+.4f}):  Tan={mtf_tan:.6f}  Sag={mtf_sag:.6f}  Avg={mtf_avg:.6f}")

# Compare with ZOS-API values
print(f"\n{'=' * 60}")
print("Comparison with previous ZOS-API (new instance) values:")
print(f"{'=' * 60}")
zosapi_vals = [0.784585, 0.780178, 0.775518, 0.777436, 0.786281, 0.783944, 0.792787, 0.790397, 0.790586]
for i, v in enumerate(zosapi_vals):
    print(f"  ZOS-API F{i+1}: {v:.6f}")

print("\nDone.")
