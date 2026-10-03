"""Compile the local Core Text exporter and freeze SVG text into glyph paths."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def outline(requests):
    source = Path(__file__).with_name("outline-text.swift")
    cache = Path(tempfile.gettempdir()) / "xwtaidev-svg-text"
    cache.mkdir(exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    binary = cache / f"outline-text-{digest}"
    if not binary.exists():
        subprocess.run([
            "xcrun", "swiftc", "-O", "-module-cache-path", str(cache / "modules"),
            str(source), "-o", str(binary),
        ], check=True)
    result = subprocess.run([str(binary)], input=json.dumps(requests, ensure_ascii=False),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)
