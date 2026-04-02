from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rsrf.commands.render import (
    exception_message,
    normalize_json_value,
    print_json,
    print_manifest_errors,
    summarize_response_definition,
)
from rsrf.models import BandSpec, SampledCurve


class NormalizeJsonValueTests(unittest.TestCase):
    def test_none_passthrough(self) -> None:
        self.assertIsNone(normalize_json_value(None))

    def test_nan_becomes_none(self) -> None:
        self.assertIsNone(normalize_json_value(float("nan")))

    def test_path_becomes_string(self) -> None:
        self.assertEqual(normalize_json_value(Path("/tmp/x")), "/tmp/x")

    def test_numpy_scalar(self) -> None:
        val = np.float64(3.14)
        result = normalize_json_value(val)
        self.assertAlmostEqual(result, 3.14)
        self.assertNotIsInstance(result, np.generic)

    def test_dict_values_normalized(self) -> None:
        result = normalize_json_value({"a": Path("/x"), "b": float("nan")})
        self.assertEqual(result, {"a": "/x", "b": None})

    def test_list_values_normalized(self) -> None:
        result = normalize_json_value([Path("/a"), None, 1])
        self.assertEqual(result, ["/a", None, 1])


class PrintJsonTests(unittest.TestCase):
    def test_prints_valid_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = print_json({"key": 42})
        self.assertEqual(ret, 0)
        self.assertIn('"key": 42', buf.getvalue())

    def test_nan_values_replaced(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_json({"x": float("nan")})
        self.assertIn("null", buf.getvalue())


class ExceptionMessageTests(unittest.TestCase):
    def test_extracts_message(self) -> None:
        self.assertEqual(exception_message(ValueError("bad")), "bad")

    def test_empty_args(self) -> None:
        exc = ValueError()
        msg = exception_message(exc)
        self.assertIsInstance(msg, str)


class PrintManifestErrorsTests(unittest.TestCase):
    def test_returns_nonzero(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = print_manifest_errors(Path("m.json"), ["err1", "err2"])
        self.assertEqual(ret, 1)
        self.assertIn("err1", buf.getvalue())
        self.assertIn("err2", buf.getvalue())


class SummarizeResponseDefinitionTests(unittest.TestCase):
    def test_sampled_curve_summary(self) -> None:
        curve = SampledCurve(
            band_id="B01",
            wavelength_nm=np.array([400.0, 500.0, 600.0]),
            response=np.array([0.0, 1.0, 0.0]),
            source_variant="test",
        )
        result = summarize_response_definition("sensor_a", "variant_a", curve)
        self.assertEqual(result["content_kind"], "sampled_curve")
        self.assertEqual(result["band_id"], "B01")
        self.assertEqual(result["sample_count"], 3)
        self.assertAlmostEqual(result["wavelength_min_nm"], 400.0)
        self.assertAlmostEqual(result["wavelength_max_nm"], 600.0)
        self.assertAlmostEqual(result["peak_response"], 1.0)

    def test_band_spec_summary(self) -> None:
        spec = BandSpec(
            band_id="B01",
            center_wavelength_nm=550.0,
            fwhm_nm=10.0,
            band_index=1,
            band_name="Green",
            band_status="nominal",
            published_shape_type="gaussian",
        )
        result = summarize_response_definition("sensor_a", "variant_a", spec)
        self.assertEqual(result["content_kind"], "band_spec")
        self.assertEqual(result["band_id"], "B01")
        self.assertAlmostEqual(result["center_wavelength_nm"], 550.0)


if __name__ == "__main__":
    unittest.main()
