"""Optional remote preferences, without live network dependencies."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from proforma.__main__ import main
from proforma.config import PREFERENCE_ENDPOINT, load_config
from proforma.pipeline import write_run


class RemotePreferenceTests(unittest.TestCase):
    def setUp(self):
        self.local = load_config()
        self.weights = [list(pair) for pair in self.local.datasets["preferences"]["weights"]]
        self.weights[0][1] *= 2
        self.raw = json.dumps(self.weights).encode()

    def test_default_and_sample_alone_do_not_fetch(self):
        with patch("proforma.config.urlopen") as fetch:
            config = load_config(sample=100)
        fetch.assert_not_called()
        self.assertEqual(config.weights, self.local.weights)

    def test_fetch_url_weights_and_provenance(self):
        for sample, suffix in ((None, ""), (100, "?n=100")):
            with self.subTest(sample=sample), patch("proforma.config.urlopen", return_value=io.BytesIO(self.raw)) as fetch:
                config = load_config(fetch_pref_order=True, sample=sample)
            url = PREFERENCE_ENDPOINT + suffix
            fetch.assert_called_once_with(url, timeout=15)
            self.assertEqual(config.weights, dict(self.weights))
            self.assertEqual(config.source_hashes[url], hashlib.sha256(self.raw).hexdigest())
            self.assertEqual(len(config.source_hashes), 5)
            self.assertEqual(load_config().weights, self.local.weights)
            with tempfile.TemporaryDirectory() as directory:
                manifest = write_run({"optimization.json": {}}, config, command="test",
                                     output_dir=Path(directory) / "run")
                saved = json.loads(manifest.read_text())
                self.assertEqual(saved["resolved_configuration"]["datasets"]["preferences"]["weights"], self.weights)
                self.assertIn(url, saved["source_hashes"])

    def test_invalid_responses_fail(self):
        invalid = [b"not json", b"{}", b"[]", b'[["park", 1]]',
                   json.dumps(self.weights + [self.weights[0]]).encode(),
                   json.dumps([[name, -1] for name, _ in self.weights]).encode()]
        for raw in invalid:
            with self.subTest(raw=raw), patch("proforma.config.urlopen", return_value=io.BytesIO(raw)):
                with self.assertRaises(ValueError):
                    load_config(fetch_pref_order=True)

    def test_network_failure_and_invalid_sample(self):
        with patch("proforma.config.urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(ValueError, "Could not fetch preferences"):
                load_config(fetch_pref_order=True)
        for sample in (0, -1, 1.5, True):
            with patch("proforma.config.urlopen") as fetch, self.assertRaises(ValueError):
                load_config(fetch_pref_order=True, sample=sample)
            fetch.assert_not_called()

    def test_cli_flags(self):
        for flags, expected in (([], False), (["--sample=100"], False),
                                (["--fetch_pref_order", "--sample=100"], True)):
            with patch("proforma.__main__.load_config", side_effect=ValueError("stop")) as load:
                with patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit):
                    main(flags)
            self.assertEqual(load.call_args.kwargs,
                             {"fetch_pref_order": expected, "sample": 100 if flags else None})
