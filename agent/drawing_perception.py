"""Optional local perception adapters. No engineering-authority dependencies.

Whitespace components are observed image regions, not recognized rooms.
Repeated narrow components are opening candidates, not certified windows.
"""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from io import BytesIO

from agent.drawing_understanding import (
    AdjacencyCandidate, DrawingHypothesis, DrawingSource, Frame, Geometry, InteriorBoundaryEvidence,
    InteriorOpeningCandidate, Observation, ObservationArtifact, Point, SourceEvidence, WallCenterlineCandidate,
    ProvenRoomBoundaryMatch, RasterLineRecoveryDiagnostic, SustainedWallGap, digest,
)


def _components(image, *, include_runs=False):
    """Deterministic four-connected white-region labelling using scanline runs."""
    width, height = image.size
    raw = image.convert("L").point(lambda v: 1 if v >= 210 else 0).tobytes()
    parents, records, previous = [], [], []

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for y in range(height):
        current, cursor = [], 0
        for match in re.finditer(b"\x01+", raw[y*width:(y+1)*width]):
            x0, x1 = match.span()
            while cursor < len(previous) and previous[cursor][1] <= x0:
                cursor += 1
            overlaps, k = [], cursor
            while k < len(previous) and previous[k][0] < x1:
                overlaps.append(root(previous[k][2]))
                k += 1
            if overlaps:
                label = min(overlaps)
                for other in overlaps:
                    parents[root(other)] = label
            else:
                label = len(parents)
                parents.append(label)
            current.append((x0, x1, label))
            records.append((label, x0, x1, y))
        previous = current
    regions = {}
    for label, x0, x1, y in records:
        key = root(label)
        if key not in regions:
            regions[key] = [x0, y, x1, y+1, x1-x0]
        else:
            r = regions[key]
            r[0], r[1], r[2], r[3] = min(r[0], x0), min(r[1], y), max(r[2], x1), max(r[3], y+1)
            r[4] += x1-x0
    ordered = sorted(regions.items(), key=lambda item: (item[1][1], item[1][0], item[1][3], item[1][2]))
    if not include_runs:
        return [value for _, value in ordered]
    runs = {key: [] for key, _ in ordered}
    for label, x0, x1, y in records:
        key = root(label)
        if key in runs:
            runs[key].append((x0, x1, y))
    return [(value, tuple(runs[key])) for key, value in ordered]


def _outer_run_polygon(runs):
    """Deterministic outer scanline envelope in raster pixel-edge space."""
    rows = {}
    for x0, x1, y in runs:
        if y not in rows:
            rows[y] = [x0, x1]
        else:
            rows[y][0] = min(rows[y][0], x0); rows[y][1] = max(rows[y][1], x1)
    ordered = sorted(rows.items())
    if not ordered:
        return ()
    left = [(x0, y) for y, (x0, _) in ordered] + [(ordered[-1][1][0], ordered[-1][0]+1)]
    right = [(x1, y+1) for y, (_, x1) in reversed(ordered)] + [(ordered[0][1][1], ordered[0][0])]
    loop = left + right
    simplified = []
    for point in loop:
        simplified.append(point)
        while len(simplified) >= 3:
            a, b, c = simplified[-3:]
            if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
                simplified.pop(-2)
            else:
                break
    return tuple(simplified)

class LocalDrawingPerceptionBackend:
    backend_id = "HOMEAURA_LOCAL_REGION_PERCEPTION"
    backend_version = "1.0"

    def perceive(self, source: DrawingSource, content: bytes) -> ObservationArtifact:
        from PIL import Image

        if hashlib.sha256(content).hexdigest() != source.source_hash:
            raise ValueError("DRAWING_CONTENT_HASH_MISMATCH")
        texts, vector_summary = [], None
        if source.source_kind == "PDF":
            import pymupdf
            expected = Frame(frame_id=source.coordinate_frame.frame_id, space="DRAWING_SPACE", unit="pt", axes="X_RIGHT_Y_DOWN")
            if source.coordinate_frame != expected:
                raise ValueError("PDF_PAGE_FRAME_MUST_USE_PAPER_POINTS")
            with pymupdf.open(stream=content, filetype="pdf") as document:
                page = document[source.page_or_frame]
                if page.rect.x0 != 0 or page.rect.y0 != 0:
                    raise ValueError("NONZERO_PAGE_ORIGIN_REQUIRES_EXPLICIT_TRANSFORM")
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                vector_summary = {"path_count": len(page.get_drawings()), "extractable_text_characters": len(page.get_text())}
                for block in page.get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            texts.append((span["text"], span["bbox"]))
                factor = Decimal(2)
        else:
            if source.coordinate_frame.space != "IMAGE_SPACE" or source.coordinate_frame.axes != "X_RIGHT_Y_DOWN":
                raise ValueError("RASTER_FRAME_MUST_USE_IMAGE_PIXELS")
            with Image.open(BytesIO(content)) as original:
                original.seek(source.page_or_frame)
                image = original.convert("RGB")
            factor = Decimal(1)
        width, height = image.size
        if width * height > 16_000_000:
            raise ValueError("PERCEPTION_IMAGE_PIXEL_BUDGET_EXCEEDED")
        observations = []
        evidence = SourceEvidence(source_id=source.source_id, source_hash=source.source_hash,
            reference=source.provenance.reference+f"; page/frame {source.page_or_frame}",
            method=self.backend_id+"/"+self.backend_version,
            authority="PROJECT_DOCUMENT_OBSERVATION")

        def geometry(bounds, divisor=factor):
            x0, y0, x1, y1 = bounds[:4]
            return Geometry(frame=source.coordinate_frame, kind="BBOX", points=(
                Point(x=Decimal(str(x0))/divisor, y=Decimal(str(y0))/divisor),
                Point(x=Decimal(str(x1))/divisor, y=Decimal(str(y1))/divisor)))

        def stable_add(kind, box=None, text=None, attributes=None, quality="LOW", limitation="Candidate extraction only"):
            key = digest({"kind": kind, "geometry": box.model_dump(mode="json") if box else None,
                          "text": text, "attributes": attributes})
            observations.append(Observation(observation_id=source.source_id+":"+key[:16], kind=kind,
                evidence=evidence, geometry=box, text=text, attributes=attributes or {}, quality=quality, limitation=limitation))

        stable_add("PAGE", geometry((0, 0, width, height)), quality="HIGH",
            attributes={"raster_width_px": width, "raster_height_px": height,
                        "pixels_per_frame_unit": str(factor)}, limitation="Page extent is not a building contour")
        if vector_summary is not None:
            stable_add("VECTOR_SUMMARY", attributes=vector_summary, quality="HIGH", limitation="Vector paths may encode text outlines")
        for text, bbox in texts:
            stable_add("TEXT", geometry(bbox, Decimal(1)), text=text, quality="MEDIUM",
                limitation="PDF text extraction is an observation, not authority")
        if source.floor_hint:
            stable_add("FLOOR_TITLE", text=source.floor_hint, quality="MEDIUM",
                limitation="Source metadata floor hint; project-storey identity still requires reconciliation")
        if source.known_scale_denominator is not None:
            stable_add("SCALE_ANNOTATION", text="1:"+str(source.known_scale_denominator),
                attributes={"denominator": str(source.known_scale_denominator)}, quality="MEDIUM",
                limitation="Source metadata declaration; dimensions must corroborate scale")
        component_details = _components(image, include_runs=True)
        regions = [region for region, _ in component_details]
        strips = []
        for r, runs in component_details:
            x0, y0, x1, y1, area = r
            w, h = x1-x0, y1-y0
            if x0 == 0 or y0 == 0 or x1 == width or y1 == height:
                continue
            fraction = Decimal(area) / Decimal(width*height)
            fill = Decimal(area) / Decimal(w*h)
            aspect = Decimal(max(w, h)) / Decimal(min(w, h))
            # Declared software segmentation policy in image space, no physical defaults.
            if Decimal("0.0025") <= fraction <= Decimal("0.25") and aspect <= 5 and fill >= Decimal("0.45"):
                polygon_pixels = _outer_run_polygon(runs)
                polygon = Geometry(frame=source.coordinate_frame, kind="POLYGON", points=tuple(
                    Point(x=Decimal(x)/factor, y=Decimal(y)/factor) for x, y in polygon_pixels))
                bbox_area = Decimal(w*h)
                polygon_area = abs(sum(polygon.points[i].x*polygon.points[(i+1)%len(polygon.points)].y -
                    polygon.points[(i+1)%len(polygon.points)].x*polygon.points[i].y
                    for i in range(len(polygon.points)))) / Decimal(2)
                stable_add("ENCLOSED_REGION", polygon, attributes={
                    "white_pixel_area": area, "bbox_fill_ratio": str(fill.quantize(Decimal("0.01"))),
                    "geometry_semantics": "CONNECTED_WHITE_REGION_OUTER_PIXEL_CONTOUR",
                    "raster_to_drawing_scale": str(Decimal(1)/factor),
                    "source_raster_unit": "px", "target_drawing_unit": source.coordinate_frame.unit,
                    "closed": True, "gap_count": 0, "vertex_count": len(polygon.points),
                    "contour_to_bbox_area_ratio": str((polygon_area/(bbox_area/(factor*factor))).quantize(Decimal("0.0001"))),
                    "simplification_error_drawing_units": str(Decimal("0.5")/factor)},
                    limitation="Connected white-space outer contour; holes, wall centerlines and opening semantics remain unresolved")
            if max(w, h) >= 20*factor and min(w, h) <= 6*factor and aspect >= 4 and fill >= Decimal("0.7"):
                strips.append(r)
        used = set()
        for i, a in enumerate(strips):
            aw, ah = a[2]-a[0], a[3]-a[1]
            horizontal = aw > ah
            for j in range(i+1, len(strips)):
                b = strips[j]
                bw, bh = b[2]-b[0], b[3]-b[1]
                if horizontal != (bw > bh):
                    continue
                length = max(aw, ah)
                aligned = (abs(a[0]-b[0])+abs(a[2]-b[2]) if horizontal else abs(a[1]-b[1])+abs(a[3]-b[3])) <= length*Decimal("0.15")
                twice_separation = abs((a[1]+a[3])-(b[1]+b[3])) if horizontal else abs((a[0]+a[2])-(b[0]+b[2]))
                if aligned and twice_separation <= 12*factor and (i, j) not in used:
                    used.add((i, j))
                    box = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
                    stable_add("PARALLEL_STRIP", geometry(box), attributes={"symbol_evidence": "TWO_NEARBY_PARALLEL_ENCLOSED_STRIPS"},
                        limitation="Window/door/stair/detail discrimination and boundary association require semantic perception")
        diagnostics = ["ROOM_AND_SYMBOL_SEMANTIC_REVIEW_REQUIRED", "NO_AUTOMATIC_PHYSICAL_SCALE_BINDING"]
        if not texts:
            diagnostics.append("OCR_OR_VISUAL_TEXT_BACKEND_REQUIRED")
        raw_digest = digest({"source_hash": source.source_hash, "page": source.page_or_frame,
            "pixel_hash": hashlib.sha256(image.tobytes()).hexdigest(), "regions": regions,
            "text": [[t, list(b)] for t, b in texts], "backend_version": self.backend_version})
        return ObservationArtifact(source=source, backend_id=self.backend_id, backend_version=self.backend_version,
            raw_perception_digest=raw_digest, observations=tuple(observations), diagnostics=tuple(diagnostics)).with_normalization_digest()


def analyze_interior_boundary_raster(source: DrawingSource, content: bytes,
        hypotheses: tuple[DrawingHypothesis, ...], adjacencies: tuple[AdjacencyCandidate, ...], *,
        maximum_gap_ink_fraction: Decimal = Decimal("0.05"),
        minimum_gap_width_drawing_units: Decimal = Decimal("12"),
        diagnostic_interruption_width_drawing_units: Decimal = Decimal("2.5")) -> tuple[tuple[InteriorBoundaryEvidence, ...], tuple[InteriorOpeningCandidate, ...]]:
    """Measure sustained ink interruptions inside candidate wall corridors.

    The output deliberately calls every interruption UNKNOWN_OPENING. Door arcs or
    passage symbols need separate evidence; a raster gap alone only supports
    geometric connectivity.
    """
    from PIL import Image
    if source.source_kind != "PDF" or source.coordinate_frame.unit != "pt":
        raise ValueError("PDF_DRAWING_SPACE_REQUIRED_FOR_BOUNDARY_RASTER_ANALYSIS")
    if hashlib.sha256(content).hexdigest() != source.source_hash:
        raise ValueError("DRAWING_CONTENT_HASH_MISMATCH")
    import pymupdf
    with pymupdf.open(stream=content, filetype="pdf") as document:
        pix = document[source.page_or_frame].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    factor = Decimal(2)
    by_id = {h.hypothesis_id: h for h in hypotheses}
    boundaries, openings = [], []
    for adjacency in sorted((a for a in adjacencies if a.frame == source.coordinate_frame),
                            key=lambda a: (a.left_hypothesis_id, a.right_hypothesis_id)):
        def bounds(h):
            points = by_id[h].geometry.points
            return min(p.x for p in points), min(p.y for p in points), max(p.x for p in points), max(p.y for p in points)
        left, right = bounds(adjacency.left_hypothesis_id), bounds(adjacency.right_hypothesis_id)
        vertical = adjacency.orientation == "VERTICAL_BOUNDARY"
        if vertical:
            x0, x1 = min(left[2], right[2]), max(left[0], right[0])
            start, stop = max(left[1], right[1]), min(left[3], right[3])
        else:
            x0, x1 = min(left[3], right[3]), max(left[1], right[1])
            start, stop = max(left[0], right[0]), min(left[2], right[2])
        profiles = []
        for position_px in range(round(float(start*factor)), round(float(stop*factor))):
            lo, hi = round(float(x0*factor)), round(float(x1*factor))
            pixels = ((image.getpixel((cross, position_px)) for cross in range(lo, hi)) if vertical else
                      (image.getpixel((position_px, cross)) for cross in range(lo, hi)))
            values = list(pixels)
            profiles.append(Decimal(sum(value < 210 for value in values))/Decimal(max(1, len(values))))
        ordered = sorted(profiles)
        median = ordered[len(ordered)//2] if ordered else Decimal(1)
        minimum_run_px = max(1, round(float(diagnostic_interruption_width_drawing_units*factor)))
        runs, run_start = [], None
        for index, value in enumerate(profiles + [Decimal(1)]):
            if value <= maximum_gap_ink_fraction and run_start is None:
                run_start = index
            elif value > maximum_gap_ink_fraction and run_start is not None:
                if index-run_start >= minimum_run_px:
                    a, b = start+Decimal(run_start)/factor, start+Decimal(index)/factor
                    points = ((Point(x=x0, y=a), Point(x=x1, y=b)) if vertical else
                              (Point(x=a, y=x0), Point(x=b, y=x1)))
                    runs.append(Geometry(frame=source.coordinate_frame, kind="BBOX", points=points))
                run_start = None
        boundary_id = source.source_id+":"+digest({"adjacency": adjacency.model_dump(mode="json")})[:16]+":BOUNDARY"
        boundary_geometry = Geometry(frame=source.coordinate_frame, kind="BBOX", points=(
            (Point(x=x0, y=start), Point(x=x1, y=stop)) if vertical else
            (Point(x=start, y=x0), Point(x=stop, y=x1))))
        qualified_runs = tuple(run for run in runs if
            ((run.points[1].y-run.points[0].y) if vertical else (run.points[1].x-run.points[0].x))
            >= minimum_gap_width_drawing_units)
        classification = ("WALL_WITH_GAP" if qualified_runs else
            "WALL_WITH_SHORT_INTERRUPTION" if runs else "SOLID_WALL")
        boundaries.append(InteriorBoundaryEvidence(boundary_id=boundary_id, adjacency=adjacency,
            geometry=boundary_geometry, median_ink_fraction=median, gap_runs=tuple(runs),
            classification=classification,
            source_dependencies={source.source_id: source.source_hash}))
        for run in qualified_runs:
            p, q = run.points
            width = (q.y-p.y) if vertical else (q.x-p.x)
            opening_id = boundary_id+":"+digest(run)[:12]+":OPENING"
            openings.append(InteriorOpeningCandidate(opening_id=opening_id, boundary_id=boundary_id,
                frame=source.coordinate_frame, geometry=run,
                connected_room_hypothesis_ids=(adjacency.left_hypothesis_id, adjacency.right_hypothesis_id),
                width_drawing_units_candidate=width))
    return tuple(boundaries), tuple(openings)


def extract_raster_wall_centerlines(source: DrawingSource, content: bytes,
        suppression_geometries: tuple[Geometry, ...] = (), *,
        outer_contour: Geometry | None = None,
        minimum_line_length_drawing_units: Decimal = Decimal("20")) -> tuple[WallCenterlineCandidate, ...]:
    """Extract long orthogonal ink bands after deterministic semantic masking."""
    from PIL import Image, ImageDraw
    if source.source_kind != "PDF" or source.coordinate_frame.unit != "pt":
        raise ValueError("PDF_DRAWING_SPACE_REQUIRED_FOR_WALL_EXTRACTION")
    if hashlib.sha256(content).hexdigest() != source.source_hash:
        raise ValueError("DRAWING_CONTENT_HASH_MISMATCH")
    import pymupdf
    factor = Decimal(2)
    with pymupdf.open(stream=content, filetype="pdf") as document:
        page = document[source.page_or_frame]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
        text_boxes = [span["bbox"] for block in page.get_text("dict")["blocks"]
                      for line in block.get("lines", ()) for span in line.get("spans", ())]
    draw = ImageDraw.Draw(image)
    pad = 1
    for x0, y0, x1, y1 in text_boxes:
        draw.rectangle((int(x0*2)-pad, int(y0*2)-pad, int(x1*2)+pad, int(y1*2)+pad), fill=255)
    for geometry in suppression_geometries:
        if geometry.frame != source.coordinate_frame:
            continue
        x0, x1 = min(p.x for p in geometry.points), max(p.x for p in geometry.points)
        y0, y1 = min(p.y for p in geometry.points), max(p.y for p in geometry.points)
        draw.rectangle((int(x0*2), int(y0*2), int(x1*2), int(y1*2)), fill=255)
    raw, width, height = image.tobytes(), image.width, image.height
    minimum_px = max(1, round(float(minimum_line_length_drawing_units*factor)))

    def scan(horizontal):
        records = []
        count = height if horizontal else width
        span = width if horizontal else height
        for axis in range(count):
            values = (raw[axis*width:(axis+1)*width] if horizontal else
                      bytes(raw[y*width+axis] for y in range(height)))
            for match in re.finditer(b"[\\x00-\\xb4]+", values):
                if match.end()-match.start() >= minimum_px:
                    records.append((axis, match.start(), match.end()))
        groups = []
        for axis, start, stop in records:
            candidates = [g for g in groups if g[3] == axis-1 and
                          min(stop, g[2])-max(start, g[1]) >= Decimal("0.8")*min(stop-start, g[2]-g[1])]
            if candidates:
                g = max(candidates, key=lambda item: min(stop,item[2])-max(start,item[1]))
                g[1], g[2], g[3] = min(g[1],start), max(g[2],stop), axis
            else:
                groups.append([axis,start,stop,axis])
        return groups

    result = []
    for horizontal, orientation in ((True,"HORIZONTAL"),(False,"VERTICAL")):
        for axis0, start, stop, axis1 in scan(horizontal):
            thickness = Decimal(axis1-axis0+1)/factor
            length = Decimal(stop-start)/factor
            # Single-pixel dimension/extension strokes are not wall bands.
            if thickness < Decimal("0.75"):
                continue
            if horizontal:
                band_points=(Point(x=Decimal(start)/factor,y=Decimal(axis0)/factor),Point(x=Decimal(stop)/factor,y=Decimal(axis1+1)/factor))
                center=(Decimal(axis0+axis1+1)/(factor*2))
                line_points=(Point(x=Decimal(start)/factor,y=center),Point(x=Decimal(stop)/factor,y=center))
            else:
                band_points=(Point(x=Decimal(axis0)/factor,y=Decimal(start)/factor),Point(x=Decimal(axis1+1)/factor,y=Decimal(stop)/factor))
                center=(Decimal(axis0+axis1+1)/(factor*2))
                line_points=(Point(x=center,y=Decimal(start)/factor),Point(x=center,y=Decimal(stop)/factor))
            band=Geometry(frame=source.coordinate_frame,kind="BBOX",points=band_points)
            if outer_contour is not None:
                if outer_contour.frame != source.coordinate_frame:
                    raise ValueError("OUTER_CONTOUR_FRAME_MISMATCH")
                ox0, ox1 = min(p.x for p in outer_contour.points), max(p.x for p in outer_contour.points)
                oy0, oy1 = min(p.y for p in outer_contour.points), max(p.y for p in outer_contour.points)
                a, b = band_points
                if a.x < ox0-2 or b.x > ox1+2 or a.y < oy0-2 or b.y > oy1+2:
                    continue
            line=Geometry(frame=source.coordinate_frame,kind="POLYLINE",points=line_points)
            wall_id=source.source_id+":"+digest({"orientation":orientation,"band":band.model_dump(mode="json")})[:16]+":WALL"
            result.append(WallCenterlineCandidate(wall_id=wall_id,frame=source.coordinate_frame,
                orientation=orientation,band_geometry=band,centerline_geometry=line,
                length_drawing_units=length,thickness_drawing_units=thickness,
                source_dependencies={source.source_id:source.source_hash},
                suppression_applied=("PDF_TEXT_SPANS","SUPPLIED_SYMBOL_REGIONS","SUB_PIXEL_DIMENSION_STROKES")))
    return tuple(sorted(result,key=lambda w:w.wall_id))


def recover_targeted_raster_wall_lines(source: DrawingSource, content: bytes,
        unmatched_boundaries: tuple[ProvenRoomBoundaryMatch, ...],
        protected_gaps: tuple[SustainedWallGap, ...], *, corridor_drawing_units: Decimal = Decimal("4"),
        minimum_continuity: Decimal = Decimal("0.92"), minimum_length_drawing_units: Decimal = Decimal("20"),
        suppression_geometries: tuple[Geometry, ...] = ()) -> tuple[tuple[WallCenterlineCandidate, ...], tuple[RasterLineRecoveryDiagnostic, ...]]:
    """Recover source ink in narrow corridors supplied by independently proven rooms.

    The boundary is search geometry only. A candidate is emitted only when the
    raw raster contains a continuous orthogonal stroke, and never across a
    protected opening. Rooms absent from ``unmatched_boundaries`` cannot affect
    this pass.
    """
    from PIL import Image, ImageDraw
    import pymupdf
    if hashlib.sha256(content).hexdigest() != source.source_hash:
        raise ValueError("DRAWING_CONTENT_HASH_MISMATCH")
    factor = Decimal(2)
    with pymupdf.open(stream=content, filetype="pdf") as document:
        page = document[source.page_or_frame]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        raw_image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
        text_boxes = [span["bbox"] for block in page.get_text("dict")["blocks"]
                      for line in block.get("lines", ()) for span in line.get("spans", ())]
    masked_image = raw_image.copy(); draw = ImageDraw.Draw(masked_image); pad = 1
    for x0,y0,x1,y1 in text_boxes:
        draw.rectangle((int(x0*2)-pad,int(y0*2)-pad,int(x1*2)+pad,int(y1*2)+pad),fill=255)
    for geometry in suppression_geometries:
        if geometry.frame != source.coordinate_frame: continue
        xs=[p.x for p in geometry.points];ys=[p.y for p in geometry.points]
        draw.rectangle((int(min(xs)*2),int(min(ys)*2),int(max(xs)*2),int(max(ys)*2)),fill=255)
    raw=raw_image.load(); masked=masked_image.load(); radius=max(1,int(corridor_drawing_units*factor))
    recovered=[]; diagnostics=[]

    def overlaps_gap(edge: Geometry) -> bool:
        a,b=edge.points;horizontal=a.y==b.y; axis=a.y if horizontal else a.x
        lo,hi=sorted((a.x,b.x)) if horizontal else sorted((a.y,b.y))
        for gap in protected_gaps:
            if gap.frame!=edge.frame: continue
            p,q=gap.geometry.points; gh=p.y==q.y
            if gh!=horizontal: continue
            gaxis=p.y if gh else p.x;glo,ghi=sorted((p.x,q.x)) if gh else sorted((p.y,q.y))
            if abs(gaxis-axis)<=corridor_drawing_units and max(lo,glo)<min(hi,ghi): return True
        return False

    for match in sorted(unmatched_boundaries,key=lambda m:m.match_id):
        edge=match.polygon_edge
        if edge.frame!=source.coordinate_frame or match.status!="UNMATCHED_POLYGON_EDGE" or match.edge_length_drawing_units<minimum_length_drawing_units: continue
        a,b=edge.points;horizontal=a.y==b.y
        lo,hi=sorted((a.x,b.x)) if horizontal else sorted((a.y,b.y)); expected_px=max(1,int((hi-lo)*factor))
        expected_axis=int(round(float((a.y if horizontal else a.x)*factor)))
        start=int(round(float(lo*factor))); stop=int(round(float(hi*factor)))
        def profile(image):
            best=None
            for axis in range(expected_axis-radius,expected_axis+radius+1):
                runs=[]
                for pos in range(start,stop):
                    if horizontal:
                        ink=0<=pos<raw_image.width and 0<=axis<raw_image.height and image[pos,axis]<=180
                    else:
                        ink=0<=axis<raw_image.width and 0<=pos<raw_image.height and image[axis,pos]<=180
                    runs.append(ink)
                continuity=Decimal(sum(runs))/Decimal(max(1,len(runs)))
                if best is None or continuity>best[0]:best=(continuity,axis,runs)
            return best
        raw_best=profile(raw); masked_best=profile(masked)
        raw_cont,axis,runs=raw_best;masked_cont=masked_best[0]
        thickness=[]
        for pos,ink in zip(range(start,stop),runs):
            if not ink:continue
            count=1
            for direction in (-1,1):
                cursor=axis+direction
                while abs(cursor-axis)<=radius:
                    value=(raw[pos,cursor] if horizontal else raw[cursor,pos]) if (0<=cursor<(raw_image.height if horizontal else raw_image.width) and 0<=pos<(raw_image.width if horizontal else raw_image.height)) else 255
                    if value>180:break
                    count+=1;cursor+=direction
            thickness.append(count)
        median_px=sorted(thickness)[len(thickness)//2] if thickness else 0
        median=Decimal(median_px)/factor
        conflict=overlaps_gap(edge)
        recovered_ok=raw_cont>=minimum_continuity and not conflict
        if masked_cont+Decimal("0.05")<raw_cont: reason="MASKED_AS_TEXT"
        elif median<Decimal("0.75"): reason="THICKNESS_OUTSIDE_POLICY"
        elif raw_cont<minimum_continuity and raw_cont>=Decimal("0.70"): reason="BROKEN_BY_ANTIALIASING"
        elif raw_cont<Decimal("0.70"): reason="LOW_INK_CONTINUITY"
        else: reason="OTHER_EXTRACTOR_MISS"
        wall=None
        if recovered_ok:
            axis_d=Decimal(axis)/factor
            points=((Point(x=lo,y=axis_d),Point(x=hi,y=axis_d)) if horizontal else (Point(x=axis_d,y=lo),Point(x=axis_d,y=hi)))
            half=max(Decimal("0.25"),median/2)
            band_points=((Point(x=lo,y=axis_d-half),Point(x=hi,y=axis_d+half)) if horizontal else (Point(x=axis_d-half,y=lo),Point(x=axis_d+half,y=hi)))
            body={"boundary":match.match_id,"axis":str(axis_d),"raw_continuity":str(raw_cont)}
            wall_id=source.source_id+":"+digest(body)[:16]+":RECOVERED_WALL"
            wall=WallCenterlineCandidate(wall_id=wall_id,frame=source.coordinate_frame,orientation="HORIZONTAL" if horizontal else "VERTICAL",
                band_geometry=Geometry(frame=source.coordinate_frame,kind="BBOX",points=band_points),centerline_geometry=Geometry(frame=source.coordinate_frame,kind="POLYLINE",points=points),
                length_drawing_units=hi-lo,thickness_drawing_units=max(Decimal("0.5"),median),source_dependencies={source.source_id:source.source_hash},
                suppression_applied=("TARGETED_RAW_RASTER_CORRIDOR_V1","INDEPENDENT_PROVEN_ROOM_BOUNDARY_SEARCH","RECOVERED_THROUGH_MASK" if reason=="MASKED_AS_TEXT" else "NO_MASK_BRIDGE"))
            recovered.append(wall)
        diagnostics.append(RasterLineRecoveryDiagnostic(boundary_id=match.match_id,room_hypothesis_id=match.room_hypothesis_id,
            frame=edge.frame,expected_geometry=edge,expected_length_drawing_units=match.edge_length_drawing_units,miss_reason=reason,
            recovered_raster_evidence=recovered_ok,recovered_wall_id=wall.wall_id if wall else None,
            recovered_length_drawing_units=(hi-lo if wall else Decimal(0)),raw_ink_continuity=raw_cont,masked_ink_continuity=masked_cont,
            median_thickness_drawing_units=median,protected_gap_conflict=conflict,
            final_status="REJECTED_OPENING_CONFLICT" if conflict else "RECOVERED_RASTER_WALL_CANDIDATE" if wall else "INSUFFICIENT_RASTER_EVIDENCE",
            source_dependencies={source.source_id:source.source_hash}))
    return tuple(recovered),tuple(diagnostics)


class FrozenObservationBackend:
    """Replay a validated observation artifact; source bytes are still verified."""
    def __init__(self, artifact: ObservationArtifact):
        self.artifact = artifact

    def perceive(self, source: DrawingSource, content: bytes) -> ObservationArtifact:
        if source != self.artifact.source or hashlib.sha256(content).hexdigest() != source.source_hash:
            raise ValueError("STALE_FROZEN_PERCEPTION")
        return self.artifact


def merge_reviewed_observations(artifact: ObservationArtifact, observations: tuple[Observation, ...]) -> ObservationArtifact:
    """Caller supplies actual source-bound review/OCR observations, never parser constants."""
    return ObservationArtifact(source=artifact.source, backend_id=artifact.backend_id+"+REVIEWED_OBSERVATIONS",
        backend_version=artifact.backend_version,
        backend_model=artifact.backend_model, backend_metadata=artifact.backend_metadata,
        raw_perception_digest=digest({"backend_raw_digest": artifact.raw_perception_digest,
                                     "review": [o.model_dump(mode="json") for o in observations]}),
        observations=artifact.observations+observations, diagnostics=artifact.diagnostics).with_normalization_digest()

