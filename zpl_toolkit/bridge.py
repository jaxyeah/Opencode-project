"""High-level ZOS-API bridge for ZPL-equivalent operations.

Based on real ZOS-API patterns from OpticStudio 2025 official Python examples.
"""

import logging
from typing import Any

from zpl_toolkit.connection import ZemaxConnection

logger = logging.getLogger(__name__)


def _arr(arr) -> list:
    """Convert .NET array to Python list."""
    if arr is None:
        return []
    try:
        return list(arr)
    except Exception:
        return []


class ZOSAPIBridge:
    """Clean Python interfaces to ZOS-API analyses and system data."""

    def __init__(self, connection: ZemaxConnection):
        if not connection.is_connected:
            raise RuntimeError("Connection must be established first")
        self._conn = connection

    @property
    def system(self):
        return self._conn.system

    # ── Lens operations ─────────────────────────────────────────

    def load_lens(self, path: str) -> bool:
        self.system.LoadFile(path, False)
        logger.info("Lens loaded: %s", path)
        return True

    def get_system_data(self) -> dict[str, Any]:
        sd = self.system.SystemData
        data: dict[str, Any] = {
            "aperture_value": sd.Aperture.ApertureValue,
            "aperture_type": str(sd.Aperture.ApertureType),
            "num_fields": sd.Fields.NumberOfFields,
            "num_wavelengths": sd.Wavelengths.NumberOfWavelengths,
            "num_surfaces": self.system.LDE.NumberOfSurfaces,
        }
        for attr in ("EffectiveFocalLength", "ImageSpaceFNum", "LensUnits"):
            if hasattr(sd, attr):
                data[attr.lower()] = getattr(sd, attr)
        return data

    def get_surface_data(self, n: int) -> dict[str, Any]:
        lde = self.system.LDE
        if n < 1 or n > lde.NumberOfSurfaces:
            return {}
        s = lde.GetSurfaceAt(n)
        d = {"surface": n}
        for attr in ("Radius", "Thickness", "TypeName", "SemiDiameter",
                     "Conic", "Coating", "Material", "Comment"):
            if hasattr(s, attr):
                v = getattr(s, attr)
                d[attr.lower()] = v if v is not None else ""
        return d

    def get_field_data(self, i: int) -> dict[str, Any]:
        fields = self.system.SystemData.Fields
        if i < 1 or i > fields.NumberOfFields:
            return {}
        f = fields.GetField(i)
        return {"x": f.X, "y": f.Y, "weight": f.Weight}

    def get_wavelength_data(self, i: int) -> dict[str, Any]:
        wavs = self.system.SystemData.Wavelengths
        if i < 1 or i > wavs.NumberOfWavelengths:
            return {}
        w = wavs.GetWavelength(i)
        return {"wavelength": w.Wavelength, "weight": w.Weight}

    # ── Analyses ─────────────────────────────────────────────────

    def run_mtf(self, max_freq: float = 50.0) -> dict[str, Any]:
        """FFT MTF — returns per-field data series."""
        a = self.system.Analyses.New_FftMtf()
        s = a.GetSettings()
        try:
            s.MaximumFrequency = max_freq
        except Exception:
            pass
        a.ApplyAndWaitForCompletion()
        r = a.GetResults()
        series = []
        for i in range(r.NumberOfDataSeries):
            ds = r.GetDataSeries(i)
            series.append({"x": _arr(ds.XData.Data), "y": _arr(ds.YData.Data)})
        a.Close()
        return {"num_series": len(series), "series": series, "max_freq": max_freq}

    def run_spot(self) -> dict[str, Any]:
        """Standard spot diagram."""
        a = self.system.Analyses.New_StandardSpot()
        a.ApplyAndWaitForCompletion()
        r = a.GetResults()
        vals = []
        try:
            g = r.GetDataGrid(0)
            if g is not None:
                n = g.NumberOfRows * g.NumberOfColumns
                vals = [g.GetValue(i) for i in range(min(n, 20))]
        except Exception:
            pass
        a.Close()
        return {"grid_values": vals}

    def run_distortion(self) -> dict[str, Any]:
        """Field curvature + distortion."""
        a = self.system.Analyses.New_FieldCurvatureAndDistortion()
        a.ApplyAndWaitForCompletion()
        r = a.GetResults()
        d = {"series_count": r.NumberOfDataSeries}
        try:
            ds = r.GetDataSeries(1)
            d["x"] = _arr(ds.XData.Data)
            d["y"] = _arr(ds.YData.Data)
        except Exception:
            pass
        a.Close()
        return d

    def run_seidel(self) -> dict[str, Any]:
        """Seidel coefficients via text output."""
        a = self.system.Analyses.New_SeidelCoefficients()
        a.ApplyAndWaitForCompletion()
        r = a.GetResults()
        try:
            return {"text": r.GetTextFile()[:2000]}
        except Exception:
            return {"text": ""}

    def run_ray_fan(self) -> dict[str, Any]:
        """Ray fan plot data."""
        a = self.system.Analyses.New_RayFan()
        a.ApplyAndWaitForCompletion()
        r = a.GetResults()
        series = []
        for i in range(r.NumberOfDataSeries):
            ds = r.GetDataSeries(i)
            series.append({"x": _arr(ds.XData.Data), "y": _arr(ds.YData.Data)})
        a.Close()
        return {"num_series": len(series), "series": series}

    # ── Bulk dump ────────────────────────────────────────────────

    def dump_all(self) -> dict[str, Any]:
        return {
            "system": self.get_system_data(),
            "fields": [self.get_field_data(i) for i in range(1, self.system.SystemData.Fields.NumberOfFields + 1)],
            "surfaces": [self.get_surface_data(i) for i in range(1, min(self.system.LDE.NumberOfSurfaces, 15))],
        }
