#!/usr/bin/env python3
"""Convert PNG images to vector formats (SVG and AI).

Uses vtracer for bitmap-to-vector tracing and cairosvg for SVG-to-PDF conversion.
Modern .ai files are PDF-based, so we generate a PDF with Adobe Illustrator headers.
"""

import argparse
import os
import struct
import sys
import tempfile
from pathlib import Path

# Ensure homebrew libraries (cairo) are discoverable on macOS
_homebrew_lib = "/opt/homebrew/lib"
if sys.platform == "darwin" and os.path.isdir(_homebrew_lib):
    os.environ.setdefault("DYLD_FALLBACK_LIBRARY_PATH", _homebrew_lib)

try:
    import vtracer
except ImportError:
    print("Error: vtracer not installed. Run: uv sync", file=sys.stderr)
    sys.exit(1)

from svgpathtools import svg2paths2, wsvg, Line, CubicBezier, Path as SvgPath


def smooth_path(path: SvgPath, smoothness: float = 0.3) -> SvgPath:
    """Smooth a single SVG path by fitting cubic Bezier curves to line segments.

    Uses Catmull-Rom-style tangent estimation: for each vertex, the tangent
    direction is the vector from the previous point to the next point, scaled
    by `smoothness`.
    """
    # Collect segments that are lines vs already curves
    # We process runs of consecutive Line segments together
    result_segments = []
    line_run: list[Line] = []

    def flush_line_run():
        """Convert accumulated line segments into smooth Bezier curves."""
        if not line_run:
            return
        if len(line_run) == 1:
            # Single line — keep as is (no context to smooth)
            result_segments.extend(line_run)
            line_run.clear()
            return

        # Extract vertices from consecutive lines
        points = [line_run[0].start]
        for seg in line_run:
            points.append(seg.end)

        n = len(points)
        for i in range(n - 1):
            p0 = points[i]
            p1 = points[i + 1]

            # Tangent at p0 — uses (p_{i-1}, p_{i+1}) if available
            if i > 0:
                tangent0 = (points[i + 1] - points[i - 1]) * smoothness * 0.5
            else:
                tangent0 = (p1 - p0) * smoothness

            # Tangent at p1 — uses (p_i, p_{i+2}) if available
            if i + 2 < n:
                tangent1 = (points[i + 2] - points[i]) * smoothness * 0.5
            else:
                tangent1 = (p1 - p0) * smoothness

            ctrl1 = p0 + tangent0
            ctrl2 = p1 - tangent1

            result_segments.append(CubicBezier(p0, ctrl1, ctrl2, p1))

        line_run.clear()

    for seg in path:
        if isinstance(seg, Line):
            line_run.append(seg)
        else:
            flush_line_run()
            result_segments.append(seg)

    flush_line_run()

    smoothed = SvgPath(*result_segments)
    # Preserve closed-path status (vtracer paths may not be continuous)
    try:
        if path.isclosed():
            smoothed._closed = True
    except (AssertionError, ValueError):
        pass
    return smoothed


def smooth_svg(input_svg: Path, output_svg: Path, smoothness: float = 0.3) -> int:
    """Smooth all paths in an SVG file. Returns the number of paths smoothed."""
    paths, attributes, svg_attributes = svg2paths2(str(input_svg))

    smoothed_paths = []
    count = 0
    for path in paths:
        # Only smooth paths that have line segments
        has_lines = any(isinstance(seg, Line) for seg in path)
        if has_lines and len(path) > 2:
            smoothed_paths.append(smooth_path(path, smoothness))
            count += 1
        else:
            smoothed_paths.append(path)

    wsvg(smoothed_paths, attributes=attributes, svg_attributes=svg_attributes,
         filename=str(output_svg))
    return count


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read PNG width and height from the IHDR chunk."""
    with open(path, "rb") as f:
        f.read(16)  # skip signature (8) + IHDR length (4) + chunk type (4)
        w, h = struct.unpack(">II", f.read(8))
    return w, h


def trace_to_svg(input_path: Path, output_path: Path, **kwargs) -> None:
    """Trace a PNG image to SVG using vtracer."""
    vtracer.convert_image_to_svg_py(
        image_path=str(input_path),
        out_path=str(output_path),
        colormode=kwargs.get("colormode", "color"),
        filter_speckle=kwargs.get("filter_speckle", 4),
        color_precision=kwargs.get("color_precision", 6),
        layer_difference=kwargs.get("layer_difference", 16),
        corner_threshold=kwargs.get("corner_threshold", 60),
        length_threshold=kwargs.get("length_threshold", 4.0),
        max_iterations=kwargs.get("max_iterations", 10),
        splice_threshold=kwargs.get("splice_threshold", 45),
        path_precision=kwargs.get("path_precision", 3),
    )


def svg_to_ai(svg_path: Path, ai_path: Path, width: int, height: int) -> None:
    """Convert SVG to AI format (PDF-based with Adobe Illustrator header)."""
    try:
        import cairosvg
    except ImportError:
        print("Error: cairosvg not installed. Run: uv sync", file=sys.stderr)
        sys.exit(1)

    # Convert SVG to PDF first
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_pdf = Path(tmp.name)

    cairosvg.svg2pdf(url=str(svg_path), write_to=str(tmp_pdf))

    pdf_bytes = tmp_pdf.read_bytes()
    tmp_pdf.unlink()

    # AI file header — tells Adobe Illustrator this is a valid AI file
    ai_header = (
        f"%!PS-Adobe-3.0\n"
        f"%%Creator: png-to-vector skill\n"
        f"%%Title: {ai_path.stem}\n"
        f"%%BoundingBox: 0 0 {width} {height}\n"
        f"%%HiResBoundingBox: 0 0 {width} {height}\n"
        f"%%DocumentProcessColors: Cyan Magenta Yellow Black\n"
        f"%%Pages: 1\n"
        f"%%EndComments\n"
    ).encode("ascii")

    with open(ai_path, "wb") as f:
        f.write(ai_header)
        f.write(pdf_bytes)


def main():
    parser = argparse.ArgumentParser(description="Convert PNG to vector (SVG/AI)")
    parser.add_argument("input", help="Input PNG file path")
    parser.add_argument("-o", "--output-dir", help="Output directory (default: same as input)")
    parser.add_argument(
        "-f",
        "--format",
        choices=["svg", "ai", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--colormode",
        choices=["color", "binary"],
        default="color",
        help="Tracing color mode (default: color)",
    )
    parser.add_argument(
        "--filter-speckle",
        type=int,
        default=4,
        help="Filter speckle size (default: 4)",
    )
    parser.add_argument(
        "--color-precision",
        type=int,
        default=6,
        help="Color quantization precision 1-8 (default: 6)",
    )
    parser.add_argument(
        "--detail",
        choices=["low", "medium", "high"],
        default="medium",
        help="Detail level preset (default: medium)",
    )
    parser.add_argument(
        "--smooth",
        action="store_true",
        default=False,
        help="Smooth jagged edges by fitting Bezier curves (default: off)",
    )
    parser.add_argument(
        "--smoothness",
        type=float,
        default=0.3,
        help="Smoothing strength 0.0-1.0 (default: 0.3)",
    )
    parser.add_argument(
        "--upscale",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help="Upscale image before tracing: 2x/3x/4x (default: 1, no upscale)",
    )

    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    if input_path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
        print(f"Warning: {input_path.suffix} may not be supported, trying anyway...", file=sys.stderr)

    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        output_dir = input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = input_path.stem

    # Detail presets
    detail_presets = {
        "low": {"filter_speckle": 10, "color_precision": 4, "layer_difference": 32},
        "medium": {"filter_speckle": 4, "color_precision": 6, "layer_difference": 16},
        "high": {"filter_speckle": 2, "color_precision": 8, "layer_difference": 8},
    }
    preset = detail_presets[args.detail]

    trace_kwargs = {
        "colormode": args.colormode,
        "filter_speckle": args.filter_speckle if args.filter_speckle != 4 else preset["filter_speckle"],
        "color_precision": args.color_precision if args.color_precision != 6 else preset["color_precision"],
        "layer_difference": preset["layer_difference"],
    }

    # Step 0.5: Upscale if requested
    trace_input = input_path
    if args.upscale > 1:
        from PIL import Image
        print(f"Upscaling {args.upscale}x (Nearest Neighbor)...")
        img = Image.open(input_path)
        new_size = (img.width * args.upscale, img.height * args.upscale)
        img_up = img.resize(new_size, Image.NEAREST)
        upscaled_path = output_dir / f"{stem}_{args.upscale}x.png"
        img_up.save(upscaled_path)
        print(f"  ✓ {img.width}x{img.height} → {new_size[0]}x{new_size[1]}")
        trace_input = upscaled_path

    # Step 1: Trace PNG to SVG
    svg_path = output_dir / f"{stem}.svg"
    print(f"Tracing {trace_input.name} → SVG (detail: {args.detail}, mode: {args.colormode})...")
    trace_to_svg(trace_input, svg_path, **trace_kwargs)
    print(f"  ✓ SVG saved: {svg_path}")

    # Step 1.5: Smooth paths if requested
    if args.smooth:
        print(f"Smoothing paths (strength: {args.smoothness})...")
        smoothed_svg = output_dir / f"{stem}_smoothed.svg"
        n = smooth_svg(svg_path, smoothed_svg, smoothness=args.smoothness)
        print(f"  ✓ Smoothed {n} paths → {smoothed_svg}")
        # Use smoothed version for AI conversion
        svg_path = smoothed_svg

    # Step 2: Convert to AI if requested
    if args.format in ("ai", "both"):
        ai_path = output_dir / f"{stem}.ai"
        print(f"Converting SVG → AI...")
        try:
            w, h = png_dimensions(input_path)
        except Exception:
            w, h = 800, 600  # fallback
        svg_to_ai(svg_path, ai_path, w, h)
        print(f"  ✓ AI saved: {ai_path}")

    # Clean up SVG if only AI was requested
    if args.format == "ai" and svg_path.exists():
        svg_path.unlink()

    print("\nDone!")


if __name__ == "__main__":
    main()
