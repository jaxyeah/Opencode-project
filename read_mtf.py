# -*- coding: utf-8 -*-
"""Read MTF @ 6 lp/mm via ZPL + FFT data series."""
import sys, os, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\Users\dell\zemax-zpl-automation")

from zpl_toolkit.connection import ZemaxConnection
from zpl_toolkit.types import ConnectionConfig

LENS_FILE = r"C:\Users\dell\Desktop\Benz214-FOV9.16x3.42-LDA3.6-LOA0.8-VID3.8m-20260225-v1.zmx"
TARGET_FREQ = 6.0

config = ConnectionConfig()
conn = ZemaxConnection(config)
conn.connect()
system = conn.system
app = conn.application
sd = system.SystemData

system.LoadFile(LENS_FILE, False)
ld = system.LDE
print(f"Surfaces: {ld.NumberOfSurfaces}, Stop: {ld.StopSurface}, SemiDia={ld.GetSurfaceAt(ld.StopSurface).SemiDiameter}")
print(f"Aperture: {sd.Aperture.ApertureType}={sd.Aperture.ApertureValue}")
print(f"Fields: {sd.Fields.NumberOfFields}, Waves: {sd.Wavelengths.NumberOfWavelengths}")

# Check if system might be afocal
print("Checking system type...")
for attr_name in sorted(dir(sd)):
    lo = attr_name.lower()
    if any(k in lo for k in ['afocal','focal','tele','infinite','mode','type']):
        if not attr_name.startswith('_'):
            try:
                v = getattr(sd, attr_name)
                if not callable(v):
                    print(f"  sd.{attr_name} = {v}")
            except: pass

# Also check image surf properties (non-crashing attributes)
img_surf_num = ld.NumberOfSurfaces
img = ld.GetSurfaceAt(img_surf_num)
print(f"Image surface ({img_surf_num}): {img.TypeName}")
for a in ['Thickness', 'Glass', 'Comment']:
    try:
        print(f"  {a}: {getattr(img, a)}")
    except: pass

# ═══ ZPL approach ═══
print(f"\n{'='*50}\nZPL GETMTF @ {TARGET_FREQ} lp/mm\n{'='*50}")
zpl = '\n'.join([
    f'OUTPUT "C:\\Users\\dell\\zemax-zpl-automation\\_o.txt"',
    'PRINT "START"',
    'FORMAT 10.6',
    'DECLARE i,INTEGER',
    'DECLARE fx,DOUBLE',
    'DECLARE fy,DOUBLE',
    'FOR i,1,NFLD(),1',
    '  fx=FLDX(i)',
    '  fy=FLDY(i)',
    f'  PRINT "F",i," TAN=",GETMTF(1,{TARGET_FREQ},1,i)',
    f'  PRINT "F",i," SAG=",GETMTF(1,{TARGET_FREQ},2,i)',
    'NEXT',
    'OUTPUT "CLOSE"',
])
zpl_path = r"C:\Users\dell\zemax-zpl-automation\_t.zpl"
with open(zpl_path,'w') as f: f.write(zpl)
app.RunCommand(f'RUNMACRO "{zpl_path}"')
time.sleep(1)
out_f = r"C:\Users\dell\zemax-zpl-automation\_o.txt"
if os.path.exists(out_f):
    print(open(out_f).read().strip())
    os.remove(out_f)
else:
    print("No output generated - ZPL may have failed")
os.remove(zpl_path)

# ═══ FFT MTF data series (for comparison) ═══
print(f"\n{'='*50}\nFFT MTF data series @ {TARGET_FREQ} lp/mm\n{'='*50}")
mtf = system.Analyses.New_FftMtf()
mtf.GetSettings().MaximumFrequency = TARGET_FREQ * 3
mtf.ApplyAndWaitForCompletion()
res = mtf.GetResults()
for i in range(res.NumberOfDataSeries):
    ds = res.GetDataSeries(i)
    xd = list(ds.XData.Data)
    yd = list(ds.YData.Data)
    idx = min(range(len(xd)), key=lambda j: abs(xd[j] - TARGET_FREQ))
    print(f"S{i}: @{xd[idx]:.4f} lp/mm -> MTF={yd[idx]:.8f}")
mtf.Close()

# ═══ Sampling test ═══
print(f"\n{'='*50}\nSampling variation test\n{'='*50}")
for samp_label, samp_val in [("32x32", 0), ("64x64", 1), ("128x128", 2), ("256x256", 3)]:
    mtf2 = system.Analyses.New_FftMtf()
    s = mtf2.GetSettings()
    s.MaximumFrequency = TARGET_FREQ * 3
    try:
        s.Sampling = samp_val
        mtf2.ApplyAndWaitForCompletion()
        res2 = mtf2.GetResults()
        ds0 = res2.GetDataSeries(0)
        xd2 = list(ds0.XData.Data)
        yd2 = list(ds0.YData.Data)
        idx2 = min(range(len(xd2)), key=lambda j: abs(xd2[j] - TARGET_FREQ))
        print(f"  {samp_label}: Series0 @{xd2[idx2]:.4f} -> MTF={yd2[idx2]:.8f}")
    except Exception as e:
        print(f"  {samp_label}: {e}")
    mtf2.Close()

conn.disconnect()
print("\nDone.")
