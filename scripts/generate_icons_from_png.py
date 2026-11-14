#!/usr/bin/env python3
"""Regenerate every app-icon target from ONE square master PNG.

The canonical generator (`scripts/generate_icons.py`) composes icons from the
brand SVGs. That only works while the brand mark lives as vector art. When the
mark only exists as a raster (a designer's PNG export), run this instead: it
takes that single square PNG and emits the full multi-platform icon set the
desktop app, the MSIX tiles and the bootstrap installer consume.

Usage (from the repo root):
    python scripts/generate_icons_from_png.py                 # uses apps/desktop/assets/icon.png
    python scripts/generate_icons_from_png.py --master path.png
    python scripts/generate_icons_from_png.py --check         # verify sizes, write nothing
    python scripts/generate_icons_from_png.py --out /tmp/icons

Outputs mirror the paths `electron-builder`, the MSIX manifest and Tauri read,
so a repack picks them up with no config change. Nothing outside the icon
targets is touched.

A single raster cannot carry an appearance variant, so the dark-appearance
targets (`icon-dark.*`, `*_altform-unplated`) are rendered from the same
artwork. Supply `--master-dark` to give them their own art.
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path

from PIL import Image

MASTER_SIZE = 1024

ICO_DESKTOP = [16, 24, 32, 48, 64, 128, 256]
ICO_TAURI = [16, 32, 64, 128, 256]
ICNS_FRAMES = [16, 32, 64, 128, 256, 512, 1024]

# Windows resolves each MSIX slot by resource qualifier; Search, Start and the
# taskbar draw `targetsize-*` at an exact bitmap per slot, so every size must
# exist or Windows synthesizes (and blurs) one.
APPX_SCALES = (100, 125, 150, 200, 400)
APPX_TARGET_SIZES = (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256)
APPX_LOGOS: dict[str, int | tuple[int, int]] = {
    "Square44x44Logo": 44,
    "Square150x150Logo": 150,
    "StoreLogo": 50,
    "Wide310x150Logo": (310, 150),
}
# The unqualified file is the light tile; `unplated` is what dark theme draws.
APPX_ALTFORMS = ("", "_altform-unplated", "_altform-lightunplated")

DEFAULT_MASTER = "apps/desktop/assets/icon.png"


def appx_scaled(base: int, scale: int) -> int:
    """Microsoft's tables round up (150 @ 125% = 188, 50 @ 125% = 63)."""
    return math.ceil(base * scale / 100 - 1e-9)


def _appx_targets() -> list[tuple[str, str, object]]:
    """(relpath, kind, arg) for every MSIX bitmap."""
    out: list[tuple[str, str, object]] = []
    for name, base in APPX_LOGOS.items():
        for scale in APPX_SCALES:
            qualifier = "" if scale == 100 else f".scale-{scale}"
            if isinstance(base, tuple):
                w, h = base
                arg: object = (appx_scaled(w, scale), appx_scaled(h, scale), appx_scaled(100, scale))
                out.append((f"apps/desktop/assets/appx/{name}{qualifier}.png", "wide", arg))
            else:
                out.append((f"apps/desktop/assets/appx/{name}{qualifier}.png", "png", appx_scaled(base, scale)))
    for size in APPX_TARGET_SIZES:
        for suffix in APPX_ALTFORMS:
            out.append((f"apps/desktop/assets/appx/Square44x44Logo.targetsize-{size}{suffix}.png", "png", size))
    return out


APPX_TARGETS = _appx_targets()

# (relpath, kind, arg) — kinds are handled in target_bytes().
TARGETS: list[tuple[str, str, object]] = [
    ("apps/desktop/assets/icon.png", "png", 1024),
    ("apps/desktop/assets/icon.ico", "ico", ICO_DESKTOP),
    ("apps/desktop/assets/icon.icns", "icns", None),
    ("apps/desktop/assets/icon-dark.png", "png_dark", 1024),
    ("apps/desktop/assets/icon-dark.ico", "ico_dark", ICO_DESKTOP),
    ("apps/desktop/assets/icon-dark.icns", "icns_dark", None),
    ("apps/desktop/assets/icon-mac.png", "png_mac", 1024),
    ("apps/desktop/assets/icon.icon/Assets/art-light.png", "art_light", 1024),
    ("apps/desktop/assets/icon.icon/Assets/art-dark.png", "art_dark", 1024),
    ("apps/desktop/assets/icon.icon/Assets/mono.png", "mono", 1024),
    *APPX_TARGETS,
    ("apps/desktop/public/apple-touch-icon.png", "png", 1024),
    ("apps/desktop/public/nous-girl.png", "girl_light", 256),
    ("apps/desktop/public/nous-girl-dark.png", "girl_dark", 256),
    ("apps/bootstrap-installer/src-tauri/icons/32x32.png", "png", 32),
    ("apps/bootstrap-installer/src-tauri/icons/128x128.png", "png", 128),
    ("apps/bootstrap-installer/src-tauri/icons/128x128@2x.png", "png", 256),
    ("apps/bootstrap-installer/src-tauri/icons/icon.ico", "ico", ICO_TAURI),
    ("apps/bootstrap-installer/src-tauri/icons/icon.icns", "icns", None),
    ("apps/bootstrap-installer/src-tauri/icons/icon.icon/Assets/art-light.png", "art_light", 1024),
    ("apps/bootstrap-installer/src-tauri/icons/icon.icon/Assets/art-dark.png", "art_dark", 1024),
    ("apps/bootstrap-installer/src-tauri/icons/icon.icon/Assets/mono.png", "mono", 1024),
    ("apps/bootstrap-installer/public/nous-girl.png", "girl_light", 256),
    ("web/public/favicon.ico", "ico", [16, 32, 48]),
    ("website/static/img/favicon-16x16.png", "png", 16),
    ("website/static/img/favicon-32x32.png", "png", 32),
    ("website/static/img/apple-touch-icon.png", "png", 180),
    ("website/static/img/favicon.ico", "ico", [16, 32, 48]),
]


def load_master(path: Path) -> Image.Image:
    if not path.exists():
        raise SystemExit(f"master PNG not found: {path}")
    img = Image.open(path).convert("RGBA")
    if img.width != img.height:
        raise SystemExit(f"master must be square, got {img.size} — pad or crop it first")
    if img.width < MASTER_SIZE:
        print(f"  ! master is {img.width}px, below {MASTER_SIZE}; output will be upscaled")
    return img if img.width == MASTER_SIZE else img.resize((MASTER_SIZE, MASTER_SIZE), Image.LANCZOS)


def scaled(master: Image.Image, size: int) -> Image.Image:
    return master if size == MASTER_SIZE else master.resize((size, size), Image.LANCZOS)


def save_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    # Flat art quantizes losslessly to an 8-bit palette (tRNS keeps AA edges).
    quantized = img.quantize(colors=256, method=Image.FASTOCTREE, dither=Image.NONE)
    if quantized.convert("RGBA").tobytes() == img.tobytes():
        quantized.save(buf, "PNG", optimize=True)
    else:
        img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def mono_image(master: Image.Image) -> Image.Image:
    """Clear/Tinted material: luminance with the artwork's own alpha."""
    rgba = master.convert("RGBA")
    grey = rgba.convert("L")
    out = Image.new("RGBA", rgba.size)
    out.putalpha(rgba.getchannel("A"))
    out.paste(grey, (0, 0), rgba.getchannel("A"))
    return out


def target_bytes(master: Image.Image, dark: Image.Image, kind: str, arg: object) -> bytes:
    buf = io.BytesIO()
    if kind == "png":
        return save_png(scaled(master, int(arg)))  # type: ignore[arg-type]
    if kind == "png_dark":
        return save_png(scaled(dark, int(arg)))  # type: ignore[arg-type]
    if kind in ("png_mac", "art_light"):
        return save_png(scaled(master, int(arg)))  # type: ignore[arg-type]
    if kind == "art_dark":
        return save_png(scaled(dark, int(arg)))  # type: ignore[arg-type]
    if kind in ("girl_light",):
        return save_png(scaled(master, int(arg)))  # type: ignore[arg-type]
    if kind in ("girl_dark",):
        return save_png(scaled(dark, int(arg)))  # type: ignore[arg-type]
    if kind == "mono":
        return save_png(mono_image(scaled(master, int(arg))))  # type: ignore[arg-type]
    if kind in ("ico", "ico_dark"):
        base = master if kind == "ico" else dark
        sizes = [int(s) for s in arg]  # type: ignore[union-attr]
        base.save(buf, format="ICO", sizes=[(s, s) for s in sizes])
        return buf.getvalue()
    if kind in ("icns", "icns_dark"):
        base = master if kind == "icns" else dark
        frames = [base.resize((s, s), Image.LANCZOS) for s in ICNS_FRAMES]
        base.save(buf, format="ICNS", append_images=frames[1:])
        return buf.getvalue()
    if kind == "wide":
        # The wide tile keeps its 100px squircle centered on a transparent canvas.
        w, h, tile = arg  # type: ignore[misc]
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        art = master.resize((tile, tile), Image.LANCZOS)
        canvas.alpha_composite(art, ((w - tile) // 2, (h - tile) // 2))
        canvas.save(buf, "PNG")
        return buf.getvalue()
    raise ValueError(f"unknown kind {kind!r}")


def ico_frame_sizes(path: Path) -> list[int]:
    data = path.read_bytes()
    count = int.from_bytes(data[4:6], "little")
    sizes = []
    for i in range(count):
        entry = data[6 + i * 16 : 6 + (i + 1) * 16]
        sizes.append(entry[0] or 256)
    return sorted(set(sizes))


def expected_size(rel: str, kind: str, arg: object) -> tuple[int, int] | None:
    if kind == "wide":
        w, h, _tile = arg  # type: ignore[misc]
        return (w, h)
    if kind in ("png", "png_dark", "png_mac", "art_light", "art_dark", "girl_light", "girl_dark", "mono"):
        s = int(arg)  # type: ignore[arg-type]
        return (s, s)
    return None


def cmd_write(source: Path, out: Path, master_path: Path, dark_path: Path | None) -> int:
    master = load_master(master_path)
    dark = load_master(dark_path) if dark_path else master
    if dark_path is None:
        print("[note] no --master-dark: dark-appearance targets reuse the light artwork")

    written = failures = 0
    for rel, kind, arg in TARGETS:
        path = out / rel
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(target_bytes(master, dark, kind, arg))
            written += 1
        except Exception as exc:
            failures += 1
            print(f"  !! {rel}: FAILED ({exc})")

    print(f"[write] wrote {written}/{len(TARGETS)} files into {out}")
    return 0 if failures == 0 else 1


def cmd_check(out: Path) -> int:
    problems: list[str] = []
    for rel, kind, arg in TARGETS:
        path = out / rel
        if not path.exists():
            problems.append(f"{rel}: MISSING")
            continue
        try:
            if kind in ("ico", "ico_dark"):
                want = sorted({int(s) for s in arg})  # type: ignore[union-attr]
                got = ico_frame_sizes(path)
                if got != want:
                    problems.append(f"{rel}: ICO frames {got}, expected {want}")
                continue
            im = Image.open(path)
            want_size = expected_size(rel, kind, arg)
            if want_size and im.size != want_size:
                problems.append(f"{rel}: {im.size}, expected {want_size}")
            if im.mode not in ("RGBA", "P", "RGB"):
                problems.append(f"{rel}: unexpected mode {im.mode}")
        except Exception as exc:
            problems.append(f"{rel}: UNREADABLE ({exc})")

    if not problems:
        print(f"[ok] all {len(TARGETS)} targets present and correctly sized")
        return 0
    print(f"[check] {len(problems)} problem(s):")
    for line in problems:
        print(f"  - {line}")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--out", type=Path, help="Output root (defaults to --source)")
    parser.add_argument("--master", type=Path, help=f"Square master PNG (defaults to {DEFAULT_MASTER})")
    parser.add_argument("--master-dark", type=Path, help="Optional separate artwork for dark-appearance targets")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    out = (args.out or source).resolve()
    master_path = (args.master or source / DEFAULT_MASTER).resolve()
    if args.check:
        sys.exit(cmd_check(out))
    sys.exit(cmd_write(source, out, master_path, args.master_dark.resolve() if args.master_dark else None))


if __name__ == "__main__":
    main()