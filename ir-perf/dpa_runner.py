#!/usr/bin/env python3
# Minimal DOCA Telemetry DPA integration layer
# This module provides a thin wrapper to sample instruction/cycle telemetry
# from NVIDIA BlueField/ConnectX DPA using the DOCA Telemetry DPA API.

import os
import re
import ctypes
import ctypes.util
from ctypes import c_int, c_uint64, c_char_p, c_void_p, c_size_t, c_uint32, POINTER, byref, create_string_buffer

# Fallback: allow running on hosts without DOCA installed
DOCA_AVAILABLE = False

class DPATelemetryError(Exception):
    pass

class DPATelemetryRunner:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._lib = None

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def _check_fwctl_loaded(self) -> bool:
        # As per NVIDIA docs, verify fwctl class exists
        return os.path.isdir('/sys/class/fwctl') and len(os.listdir('/sys/class/fwctl')) > 0

    def _load_library(self):
        # Try typical DOCA Telemetry DPA library names
        candidates = [
            'libdoca_telemetry_dpa.so',
            'libdoca_telemetry.so',
        ]
        for name in candidates:
            path = ctypes.util.find_library(name) or name
            try:
                lib = ctypes.CDLL(path)
                self._log(f"Loaded DOCA library: {path}")
                return lib
            except OSError:
                continue
        return None

    def _check_prereqs(self) -> bool:
        ok = True
        if not self._check_fwctl_loaded():
            print("✗ DOCA prerequisite: fwctl driver not loaded (/sys/class/fwctl missing or empty)")
            print("  See NVIDIA MLNX_OFED docs to install fwctl-dkms or fwctl-modules and load mlx5_fwctl.")
            ok = False
        self._lib = self._load_library()
        if self._lib is None:
            print("✗ DOCA library not found (libdoca_telemetry_dpa.so)")
            ok = False
        return ok

    def _select_device(self, device_hint: str | None) -> str | None:
        # Device selection is platform specific; as a placeholder, accept the hint or return None
        return device_hint or None

    def run(self, device: str | None, sample_ms: int = 1000, thread_filter: str | None = None) -> bool:
        """
        Minimal end-to-end sampling stub that validates the environment and prints
        a short status. Extend here to call actual DOCA Telemetry DPA APIs once headers
        and Python bindings are available in the environment.
        """
        if not self._check_prereqs():
            return False

        dev = self._select_device(device)
        if dev is None:
            print("✗ No DOCA device specified and auto-selection is not implemented yet")
            return False

        # Placeholder: demonstrate intended flow without crashing when DOCA symbols are not bound.
        self._log(f"Using device: {dev}")
        self._log(f"Sampling interval: {sample_ms} ms")
        if thread_filter:
            self._log(f"Thread filter: {thread_filter}")

        # In a fully integrated environment, here we would:
        # 1) ctx = doca_telemetry_dpa_create(dev)
        # 2) Check capabilities via doca_telemetry_dpa_cap_is_supported()
        # 3) Query processes/threads, then request cumulative and event tracer samples
        # 4) Convert samples into per-thread instructions and cycles deltas
        # 5) Print a brief summary (cycles, instructions) similar to CPU backend
        # For now, signal successful no-op so the pipeline is wired correctly.

        print("✓ DPA backend initialized (stub). Provide actual DOCA environment to collect data.")
        return True
