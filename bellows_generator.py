#!/usr/bin/env python3
"""
Large Format Camera Bellows Pattern Generator

Generates cutting patterns for conical camera bellows with trapezoidal 
top/bottom faces and rectangular side faces.

Author: Sylvain Ferrand
License: CC BY-NC 4.0
"""

import math
import argparse
import os
from xml.etree import ElementTree as ET

class ConicBellowsGenerator:
    """
    Generator for conical camera bellows patterns.

    Features:
    - Trapezoids (Top/Bottom): progression by PAIRS (same width in a pair)
    - Rectangles (Left/Right): CONTINUOUS progression
    - Always EVEN number of folds (complete pairs)
    """

    def __init__(self, front_w=96.0, front_h=96.0, rear_w=145.0, rear_h=145.0,
                 stiffener_height=12.0, gap_height=2.5, chamfer=1.5, 
                 face_gap=5.0, max_draw=300.0, margin=30.0,
                 stroke_width=1.0, stroke_color="black"):
        """
        Initialize the bellows generator with dimensions and parameters.

        Args:
            front_w: Front width in mm (camera front standard)
            front_h: Front height in mm
            rear_w: Rear width in mm (lens board side)
            rear_h: Rear height in mm
            stiffener_height: Height of each reinforcement strip in mm
            gap_height: Height of folding gaps in mm
            chamfer: Corner chamfer to avoid overlap in mm
            face_gap: Spacing between faces in pattern in mm
            max_draw: Maximum bellows extension in mm
            margin: Margin around pattern in mm
            stroke_width: Line thickness in mm
            stroke_color: Line color (black, red, blue, etc.)
        """
        self.front_w = front_w
        self.front_h = front_h
        self.rear_w = rear_w
        self.rear_h = rear_h

        self.stiffener_height = stiffener_height
        self.gap_height = gap_height
        self.chamfer = chamfer
        self.face_gap = face_gap

        self.max_draw = max_draw
        self.margin = margin

        self.stroke_width = stroke_width
        self.stroke_color = stroke_color

        # Calculate number of folds (must be even)
        self.fold_cycle = self.stiffener_height + self.gap_height
        self.num_folds = int(self.max_draw / self.fold_cycle)

        if self.num_folds % 2 != 0:
            self.num_folds -= 1

        self.total_length = self.num_folds * self.fold_cycle

    def get_pair_dimension(self, fold_index, dim_small, dim_large):
        """
        Calculate dimension for a PAIR of folds.
        Dimension changes every 2 folds.

        Args:
            fold_index: Current fold index (0-based)
            dim_small: Starting dimension
            dim_large: Ending dimension

        Returns:
            Interpolated dimension for this fold's pair
        """
        pair_index = fold_index // 2
        num_pairs = self.num_folds // 2
        ratio = pair_index / max(num_pairs - 1, 1)
        return dim_small + (dim_large - dim_small) * ratio

    def get_continuous_dimension(self, fold_index, dim_small, dim_large):
        """
        Calculate dimension with CONTINUOUS progression.
        Dimension changes at every fold.

        Args:
            fold_index: Current fold index (0-based)
            dim_small: Starting dimension
            dim_large: Ending dimension

        Returns:
            Interpolated dimension for this fold
        """
        ratio = fold_index / max(self.num_folds - 1, 1)
        return dim_small + (dim_large - dim_small) * ratio

    def create_trapezoid(self, fold_index, x_center):
        """
        Create a TRAPEZOID that alternates orientation.
        - Even folds (0,2,4...): narrow on top, wide on bottom (▽)
        - Odd folds (1,3,5...): wide on top, narrow on bottom (△)

        The 2 trapezoids in a pair have the same base width.

        Args:
            fold_index: Current fold index
            x_center: Horizontal center position

        Returns:
            List of 4 points [(x,y), ...] defining the trapezoid
        """
        # Width of this pair
        base_width = self.get_pair_dimension(fold_index, self.front_w, self.rear_w)
        current_pair = fold_index // 2
        num_pairs = self.num_folds // 2

        # Special handling for the last pair
        if current_pair == num_pairs - 1:
            # Last pair alternates between previous pair and rear_w
            prev_pair_width = self.get_pair_dimension((num_pairs - 2) * 2, self.front_w, self.rear_w)
            if fold_index % 2 == 0:
                width_top = prev_pair_width
                width_bottom = self.rear_w
            else:
                width_top = self.rear_w
                width_bottom = prev_pair_width
        else:
            # Normal pairs: alternate with next pair
            next_width = self.get_pair_dimension((current_pair + 1) * 2, self.front_w, self.rear_w)
            if fold_index % 2 == 0:
                width_top = base_width
                width_bottom = next_width
            else:
                width_top = next_width
                width_bottom = base_width

        # Calculate vertical positions
        y_top = self.margin + fold_index * self.fold_cycle
        y_bottom = y_top + self.stiffener_height

        # Half-widths
        hw_top = width_top / 2.0
        hw_bottom = width_bottom / 2.0

        # Create trapezoid points with chamfer
        points = [
            (x_center - hw_top + self.chamfer, y_top),
            (x_center + hw_top - self.chamfer, y_top),
            (x_center + hw_bottom - self.chamfer, y_bottom),
            (x_center - hw_bottom + self.chamfer, y_bottom)
        ]
        return points

    def create_rectangle(self, fold_index, x_center):
        """
        Create a RECTANGLE with continuous progression.

        Args:
            fold_index: Current fold index
            x_center: Horizontal center position

        Returns:
            List of 4 points [(x,y), ...] defining the rectangle
        """
        width = self.get_continuous_dimension(fold_index, self.front_h, self.rear_h)

        y_top = self.margin + fold_index * self.fold_cycle
        y_bottom = y_top + self.stiffener_height
        hw = width / 2.0

        points = [
            (x_center - hw + self.chamfer, y_top),
            (x_center + hw - self.chamfer, y_top),
            (x_center + hw - self.chamfer, y_bottom),
            (x_center - hw + self.chamfer, y_bottom)
        ]
        return points

    def points_to_path(self, points):
        """Convert points to SVG path string."""
        path = f"M {points[0][0]:.2f},{points[0][1]:.2f} "
        for p in points[1:]:
            path += f"L {p[0]:.2f},{p[1]:.2f} "
        path += "Z"
        return path

    def generate_svg(self, filename="bellows_pattern.svg", separate_faces=False):
        """
        Generate SVG pattern file(s).

        Args:
            filename: Output filename
            separate_faces: If True, generate 4 separate files (one per face)

        Returns:
            List of generated filenames
        """
        if separate_faces:
            return self._generate_separate_faces(filename)
        else:
            return self._generate_combined(filename)

    def _generate_combined(self, filename):
        """Generate pattern with all 4 faces side-by-side."""
        # Calculate face positions
        x_start = self.margin
        x_face1_center = x_start + self.rear_w / 2
        x_face2_center = x_face1_center + self.rear_w/2 + self.face_gap + self.rear_h/2
        x_face3_center = x_face2_center + self.rear_h/2 + self.face_gap + self.rear_w/2
        x_face4_center = x_face3_center + self.rear_w/2 + self.face_gap + self.rear_h/2

        total_width = (self.rear_w * 2 + self.rear_h * 2 + self.face_gap * 3)
        canvas_width = total_width + self.margin * 2
        canvas_height = self.total_length + self.margin * 2

        # Create SVG
        svg = self._create_svg_header(canvas_width, canvas_height)
        svg.append(f'  <g id="stiffeners" stroke="{self.stroke_color}" stroke-width="{self.stroke_width}" fill="none">\n')

        for i in range(self.num_folds):
            # Face 1: TOP (trapezoid)
            points1 = self.create_trapezoid(i, x_face1_center)
            svg.append(f'    <path d="{self.points_to_path(points1)}"/>\n')

            # Face 2: RIGHT (rectangle)
            points2 = self.create_rectangle(i, x_face2_center)
            svg.append(f'    <path d="{self.points_to_path(points2)}"/>\n')

            # Face 3: BOTTOM (trapezoid)
            points3 = self.create_trapezoid(i, x_face3_center)
            svg.append(f'    <path d="{self.points_to_path(points3)}"/>\n')

            # Face 4: LEFT (rectangle)
            points4 = self.create_rectangle(i, x_face4_center)
            svg.append(f'    <path d="{self.points_to_path(points4)}"/>\n')

        svg.append('  </g>\n')
        svg.append('</svg>')

        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(svg)

        return [filename]

    def _generate_separate_faces(self, base_filename):
        """Generate 4 separate SVG files, one per face."""
        files = []
        base = os.path.splitext(base_filename)[0]

        # Face 1: TOP (trapezoid)
        files.append(self._generate_single_face(
            f"{base}_face1_top.svg", "trapezoid", self.front_w, self.rear_w))

        # Face 2: RIGHT (rectangle)
        files.append(self._generate_single_face(
            f"{base}_face2_right.svg", "rectangle", self.front_h, self.rear_h))

        # Face 3: BOTTOM (trapezoid)
        files.append(self._generate_single_face(
            f"{base}_face3_bottom.svg", "trapezoid", self.front_w, self.rear_w))

        # Face 4: LEFT (rectangle)
        files.append(self._generate_single_face(
            f"{base}_face4_left.svg", "rectangle", self.front_h, self.rear_h))

        return files

    def _generate_single_face(self, filename, shape_type, dim_small, dim_large):
        """Generate a single face pattern."""
        max_width = dim_large
        canvas_width = max_width + self.margin * 2
        canvas_height = self.total_length + self.margin * 2
        x_center = self.margin + max_width / 2

        svg = self._create_svg_header(canvas_width, canvas_height)
        svg.append(f'  <g id="face" stroke="{self.stroke_color}" stroke-width="{self.stroke_width}" fill="none">\n')

        for i in range(self.num_folds):
            if shape_type == "trapezoid":
                points = self.create_trapezoid(i, x_center)
            else:
                points = self.create_rectangle(i, x_center)
            svg.append(f'    <path d="{self.points_to_path(points)}"/>\n')

        svg.append('  </g>\n')
        svg.append('</svg>')

        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(svg)

        return filename

    def _create_svg_header(self, width, height):
        """Create SVG header with proper dimensions."""
        return [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{width}mm" 
     height="{height}mm" 
     viewBox="0 0 {width} {height}">
''']

    def split_to_pages(self, svg_file, page_format="A4"):
        """
        Split SVG into multiple pages if it exceeds the page size.

        Args:
            svg_file: Input SVG file to split
            page_format: "A4" (210x297mm) or "A3" (297x420mm)

        Returns:
            List of generated page filenames
        """
        # Page sizes in mm
        page_sizes = {
            "A4": (210, 297),
            "A3": (297, 420)
        }

        if page_format not in page_sizes:
            print(f"Unsupported page format: {page_format}")
            return []

        page_w, page_h = page_sizes[page_format]

        # Read SVG dimensions
        tree = ET.parse(svg_file)
        root = tree.getroot()

        svg_width = float(root.get('width').replace('mm', ''))
        svg_height = float(root.get('height').replace('mm', ''))

        # Calculate required pages
        cols = math.ceil(svg_width / page_w)
        rows = math.ceil(svg_height / page_h)

        if cols == 1 and rows == 1:
            print(f"Pattern fits on a single {page_format} page")
            return [svg_file]

        print(f"Splitting into {cols}x{rows} = {cols*rows} {page_format} pages")

        base = os.path.splitext(svg_file)[0]
        pages = []

        for row in range(rows):
            for col in range(cols):
                page_file = f"{base}_page_{row+1}_{col+1}.svg"

                x_offset = col * page_w
                y_offset = row * page_h

                # Create page
                svg = []
                svg.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{page_w}mm" 
     height="{page_h}mm" 
     viewBox="{x_offset} {y_offset} {page_w} {page_h}">
''')

                # Copy content
                for child in root:
                    svg.append(ET.tostring(child, encoding='unicode'))

                svg.append('</svg>')

                with open(page_file, 'w', encoding='utf-8') as f:
                    f.writelines(svg)

                pages.append(page_file)

        return pages

def convert_svg_to_format(svg_file, output_format):
    """
    Convert SVG to PNG, JPEG, or PDF.
    Requires: pip install cairosvg pillow

    Args:
        svg_file: Input SVG file
        output_format: "png", "jpeg", "jpg", or "pdf"

    Returns:
        Output filename or None if conversion failed
    """
    base = os.path.splitext(svg_file)[0]

    if output_format == "png":
        output_file = f"{base}.png"
        try:
            import cairosvg
            cairosvg.svg2png(url=svg_file, write_to=output_file, dpi=300)
            print(f"  → Converted to PNG: {output_file}")
            return output_file
        except ImportError:
            print("  ⚠ cairosvg module required: pip install cairosvg")
            return None

    elif output_format in ["jpeg", "jpg"]:
        output_file = f"{base}.jpg"
        try:
            import cairosvg
            from PIL import Image
            import io

            # Convert SVG → PNG in memory
            png_data = cairosvg.svg2png(url=svg_file, dpi=300)

            # Convert PNG → JPEG
            img = Image.open(io.BytesIO(png_data))

            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img

            img.save(output_file, 'JPEG', quality=95)
            print(f"  → Converted to JPEG: {output_file}")
            return output_file
        except ImportError:
            print("  ⚠ Required modules: pip install cairosvg pillow")
            return None

    elif output_format == "pdf":
        output_file = f"{base}.pdf"
        try:
            import cairosvg
            cairosvg.svg2pdf(url=svg_file, write_to=output_file)
            print(f"  → Converted to PDF: {output_file}")
            return output_file
        except ImportError:
            print("  ⚠ cairosvg module required: pip install cairosvg")
            return None

    return None

def main():
    parser = argparse.ArgumentParser(
        description='Large Format Camera Bellows Pattern Generator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog='For more information: https://github.com/yourusername/bellows-pattern-generator'
    )

    # Dimensions
    dim_group = parser.add_argument_group('dimensions')
    dim_group.add_argument('--front-w', type=float, default=96.0, 
                          help='Front width in mm')
    dim_group.add_argument('--front-h', type=float, default=96.0, 
                          help='Front height in mm')
    dim_group.add_argument('--rear-w', type=float, default=145.0, 
                          help='Rear width in mm')
    dim_group.add_argument('--rear-h', type=float, default=145.0, 
                          help='Rear height in mm')

    # Construction parameters
    const_group = parser.add_argument_group('construction')
    const_group.add_argument('--stiffener-height', type=float, default=12.0, 
                            help='Stiffener height in mm')
    const_group.add_argument('--gap-height', type=float, default=2.5, 
                            help='Folding gap height in mm')
    const_group.add_argument('--chamfer', type=float, default=1.5, 
                            help='Corner chamfer in mm')
    const_group.add_argument('--face-gap', type=float, default=5.0, 
                            help='Gap between faces in pattern in mm')
    const_group.add_argument('--max-draw', type=float, default=300.0, 
                            help='Maximum bellows extension in mm')

    # Rendering
    render_group = parser.add_argument_group('rendering')
    render_group.add_argument('--margin', type=float, default=30.0, 
                             help='Margin around pattern in mm')
    render_group.add_argument('--stroke-width', type=float, default=1.0, 
                             help='Line thickness in mm')
    render_group.add_argument('--stroke-color', type=str, default='black', 
                             help='Line color')

    # Generation options
    gen_group = parser.add_argument_group('generation options')
    gen_group.add_argument('--separate-faces', action='store_true', 
                          help='Generate 4 separate files (one per face)')

    # Export options
    export_group = parser.add_argument_group('export options')
    export_group.add_argument('--format', type=str, 
                             choices=['svg', 'png', 'jpeg', 'jpg', 'pdf'], 
                             default='svg', help='Output format')

    # Page splitting
    split_group = parser.add_argument_group('page splitting')
    split_group.add_argument('--split-a4', action='store_true', 
                            help='Split into A4 pages if needed')
    split_group.add_argument('--split-a3', action='store_true', 
                            help='Split into A3 pages if needed')

    # Output
    parser.add_argument('-o', '--output', type=str, default='bellows_pattern.svg', 
                       help='Output filename')

    args = parser.parse_args()

    # Create generator
    generator = ConicBellowsGenerator(
        front_w=args.front_w, front_h=args.front_h,
        rear_w=args.rear_w, rear_h=args.rear_h,
        stiffener_height=args.stiffener_height, gap_height=args.gap_height,
        chamfer=args.chamfer, face_gap=args.face_gap,
        max_draw=args.max_draw, margin=args.margin,
        stroke_width=args.stroke_width, stroke_color=args.stroke_color
    )

    print(f"Configuration:")
    print(f"  • Dimensions: {generator.front_w}×{generator.front_h} → {generator.rear_w}×{generator.rear_h} mm")
    print(f"  • Folds: {generator.num_folds} ({generator.num_folds//2} pairs)")
    print(f"  • Length: {generator.total_length} mm")
    print()

    # Generate SVG files
    svg_files = generator.generate_svg(args.output, separate_faces=args.separate_faces)

    if args.separate_faces:
        print(f"✓ Generated 4 separate faces:")
        for f in svg_files:
            print(f"  • {f}")
    else:
        print(f"✓ Pattern generated: {svg_files[0]}")

    # Split into pages if requested
    if args.split_a4 or args.split_a3:
        page_format = "A3" if args.split_a3 else "A4"
        all_pages = []

        for svg_file in svg_files:
            pages = generator.split_to_pages(svg_file, page_format)
            all_pages.extend(pages)

        if len(all_pages) > len(svg_files):
            print(f"\n✓ Split into {len(all_pages)} {page_format} pages")
            svg_files = all_pages

    # Convert format if requested
    if args.format != 'svg':
        print(f"\nConverting to {args.format.upper()}:")
        for svg_file in svg_files:
            convert_svg_to_format(svg_file, args.format)

if __name__ == "__main__":
    main()
