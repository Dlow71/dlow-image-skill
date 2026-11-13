#!/usr/bin/env python3
"""Generate one image/GIF through the fixed DLow endpoint. Standard library only."""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import struct
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://www.dlowapi.me/v1/images/generations"


def inspect_image(data):
    if data.startswith((b"GIF87a", b"GIF89a")):
        width, height = struct.unpack_from("<HH", data, 6)
        pos = 13 + (3 * (2 ** ((data[10] & 7) + 1)) if data[10] & 128 else 0)
        frames = 0
        while pos < len(data):
            marker = data[pos]
            pos += 1
            if marker == 0x3B:
                break
            if marker == 0x21:
                pos += 1
            elif marker == 0x2C:
                packed = data[pos + 8]
                pos += 9
                if packed & 128:
                    pos += 3 * (2 ** ((packed & 7) + 1))
                pos += 1
                frames += 1
            else:
                raise ValueError("Invalid GIF block")
            while pos < len(data):
                length = data[pos]
                pos += 1
                if length == 0:
                    break
                pos += length
        return "gif", {"width": width, "height": height, "frames": frames, "animated": frames > 1}
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = struct.unpack_from(">II", data, 16)
        return "png", {"width": width, "height": height}
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg", {}
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp", {}
    raise ValueError("Response does not contain a recognized image file")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--format", choices=["png", "gif", "jpeg", "webp"], default="png")
    parser.add_argument("--out", required=True)
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", choices=["auto", "low", "medium", "high"], default="auto")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    key = os.environ.get("DLOW_API_KEY", "").strip()
    if not key and sys.stdin.isatty():
        key = getpass.getpass("DLow API key: ").strip()
    if not key:
        print("Missing DLOW_API_KEY. Ask the user for their DLow API key first.", file=sys.stderr)
        return 2
    try:
        # Refuse an existing target before making a potentially billable request.
        target = Path(args.out).expanduser().resolve().with_suffix("." + args.format)
        if target.exists():
            raise ValueError("Output file already exists; choose a different --out path")
        payload = {"model": "gpt-image-2.6", "prompt": args.prompt, "n": 1,
                   "size": args.size, "quality": args.quality, "output_format": args.format}
        request = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(), headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            result = json.load(response)
        item = result["data"][0]
        if item.get("b64_json"):
            data = base64.b64decode(item["b64_json"], validate=True)
        elif item.get("url"):
            # Do not forward the API key to an image download host.
            if not item["url"].startswith("https://"):
                raise ValueError("Only HTTPS image download URLs are supported")
            with urllib.request.urlopen(item["url"], timeout=args.timeout) as response:
                data = response.read()
        else:
            raise ValueError("No b64_json or image URL in response")
        fmt, info = inspect_image(data)
        path = target.with_suffix("." + fmt)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(data)
        print(json.dumps({"file": str(path), "format": fmt, "bytes": len(data), **info}, ensure_ascii=False))
        return 0
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").replace(key, "[REDACTED]")
        print(f"HTTP {error.code}: {detail[:2000]}", file=sys.stderr)
    except Exception as error:
        print(f"{type(error).__name__}: {str(error).replace(key, '[REDACTED]')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
