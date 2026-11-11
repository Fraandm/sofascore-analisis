"""Pruebas del cliente HTTP que no requieren red."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sofascore.client import (
    ClientConfig,
    RateLimiter,
    SofaScoreClient,
    _SessionPool,
    xrw_token,
)


class XrwTokenTests(unittest.TestCase):
    def test_token_is_stable_inside_half_hour_block(self):
        self.assertEqual(xrw_token(0), xrw_token(1799))
        self.assertEqual(xrw_token(1799), xrw_token(1800 - 1))

    def test_token_changes_with_block_and_is_hex(self):
        first = xrw_token(0)
        second = xrw_token(1800)
        self.assertNotEqual(first, second)
        self.assertEqual(len(first), 6)
        self.assertEqual(len(second), 6)
        int(first, 16)
        int(second, 16)

    def test_headers_include_ephemeral_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = SofaScoreClient(
                ClientConfig(use_cache=False, cache_dir=Path(tmp))
            )
            headers = client._headers()
        self.assertIn("X-Requested-With", headers)
        self.assertEqual(len(headers["X-Requested-With"]), 6)


class NetworkFamilyTests(unittest.TestCase):
    def test_ipv4_is_forced_by_default(self):
        pool = _SessionPool(ClientConfig(), RateLimiter(0))
        self.assertEqual(pool.interface(), "0.0.0.0")

    def test_ipv4_can_be_disabled(self):
        pool = _SessionPool(ClientConfig(force_ipv4=True), RateLimiter(0))
        pool.disable_ipv4()
        self.assertIsNone(pool.interface())

    def test_ipv4_can_be_configured_off(self):
        pool = _SessionPool(
            ClientConfig(force_ipv4=False), RateLimiter(0)
        )
        self.assertIsNone(pool.interface())


if __name__ == "__main__":
    unittest.main()
