#!/usr/bin/env python3
"""Axiom Hello-World (Python) — JOB-02 reference job."""
import platform
import datetime
import socket

print("=== Axiom Hello-World (Python) ===")
print(f"Host:    {socket.gethostname()}")
print(f"OS:      {platform.system()} {platform.release()}")
print(f"Python:  {platform.python_version()}")
print(f"Time:    {datetime.datetime.utcnow().isoformat()}Z")
print("=== PASS ===")
