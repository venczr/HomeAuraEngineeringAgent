"""Make a clearly scoped visual review of the official D185 Native Editor state."""

from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / "homeaura-native-editor" / "examples" / "proposals"
FULL = PROPOSALS / "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185" / "HomeAura_Floor1_D185_Clean_View.png"
KITCHEN = PROPOSALS / "HA_TWO_FLOOR_R03_POINT3_ROUTES_183" / "HomeAura_Floor1_D183_R03_Clean_Zoom.png"
OUTPUT = ROOT / "output" / "pdf" / "HomeAura_D185_Floor1_Actual_Status_20260924.pdf"


def add_page(document, image_path, title, caption, foot_lines):
    page = document.new_page(width=1190, height=842)
    page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
    page.insert_text((45, 33), title, fontsize=15, color=(0.10, 0.20, 0.34))
    page.insert_text((45, 50), caption, fontsize=9, color=(0.60, 0.15, 0.14))
    page.insert_image(pymupdf.Rect(45, 61, 1145, 739), filename=str(image_path), keep_proportion=True)
    page.draw_line((45, 747), (1145, 747), color=(0.55, 0.55, 0.55), width=0.6)
    for index, line in enumerate(foot_lines):
        page.insert_text((50, 765 + 17 * index), line, fontsize=9, color=(0.17, 0.17, 0.17))


def main():
    document = pymupdf.open()
    add_page(
        document,
        FULL,
        "D185 / FLOOR 1 / CURRENT NATIVE EDITOR ROUTES",
        "14 loops reach bounded terminal grid. Collector-continuous routes: 0. Exact Eurocone tails absent.",
        [
            "Source: official D185 clean renderer. This is the Native Editor plan, not the source Test_01 PDF.",
            "BODY and Point3 routing have bounded validations; complete K1 and installation readiness remain false.",
        ],
    )
    add_page(
        document,
        KITCHEN,
        "D183 / KITCHEN-LIVING / C07-C09 ROUTE DETAIL",
        "Three loops reach K1 terminal grid through physical Point3 TRANSIT; both Eurocone tails remain unbuilt.",
        [
            "C07 K1 supply/return ports 12/13; C08 14/15; C09 16/17. Supply and return are separate routes.",
            "R80 lengths to bounded terminals: 71.237 / 70.616 / 71.819 m; BODY coverage 96.689%.",
            "No collector-continuous PASS is claimed. Context circuits are visible in the crop.",
        ],
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(OUTPUT), garbage=4, deflate=True)
    document.close()
    print(OUTPUT)


if __name__ == "__main__":
    main()
