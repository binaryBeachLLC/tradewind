"""Collect figures, renders, schematic and layer images into docs/report/img and docs/datasheet/img,
then print the report and datasheet to PDF with headless Chrome.

python3 tools/build_docs.py [--pdf]
"""
import glob
import re
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIG = os.path.join(ROOT, "docs", "figures")
DOCS = [os.path.join(ROOT, "docs", "report"), os.path.join(ROOT, "docs", "datasheet")]
LOGO = os.path.join(ROOT, "docs", "brand", "logo-256.png")


def sh(*a):
    subprocess.run(a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def png(svg, out, width):
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(svg):
        sh("inkscape", svg, "--export-type=png", "--export-width=%d" % width, "--export-background=white",
           "--export-background-opacity=1", "-o", out)


def jpg(src, out, width):
    """Renders go in as JPEG (quality 88) to keep the pages light."""
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        sh("convert", src, "-resize", "%dx" % width, "-strip", "-quality", "88", out)


def collect():
    tmp = os.path.join(ROOT, ".scratch", "docimg")
    os.makedirs(tmp, exist_ok=True)
    # schematic sheets and PCB layers
    for svg in glob.glob(os.path.join(ROOT, "docs", "schematic", "*.svg")):
        name = os.path.basename(svg).replace("tradewind-", "sch_").replace("tradewind.svg", "sch_Root.svg")
        png(svg, os.path.join(tmp, name.replace(".svg", ".png")), 2600)
    for svg in glob.glob(os.path.join(ROOT, "hardware", "fab", "svg", "*.svg")):
        png(svg, os.path.join(tmp, "layer_" + os.path.basename(svg).replace(".svg", ".png")), 1400)
    for f in glob.glob(os.path.join(ROOT, "render", "out", "*.png")) + glob.glob(os.path.join(ROOT, "render", "out", "kicad", "*.png")):
        jpg(f, os.path.join(tmp, "r_" + os.path.basename(f).replace(".png", ".jpg")), 1800)
    layers = [os.path.join(tmp, "layer_%s.png" % l) for l in ("F_Cu", "In1_Cu", "In2_Cu", "B_Cu")]
    if all(os.path.exists(l) for l in layers):
        sh("convert", *layers, "-resize", "700x", "-bordercolor", "white", "-border", "8", "+append", os.path.join(tmp, "layer_strip.png"))
    for d in DOCS:
        img = os.path.join(d, "img")
        os.makedirs(img, exist_ok=True)
        for f in glob.glob(os.path.join(FIG, "*.png")) + glob.glob(os.path.join(tmp, "*")):
            shutil.copy2(f, img)
        if os.path.exists(LOGO):
            shutil.copy2(LOGO, os.path.join(img, "logo.png"))
    print("images collected:", len(os.listdir(os.path.join(DOCS[0], "img"))))


def pdf():
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    jobs = [(os.path.join(ROOT, "docs", "report", "index.html"), os.path.join(ROOT, "docs", "Tradewind_TW-1_Engineering_Report_revB.pdf")),
            (os.path.join(ROOT, "docs", "datasheet", "index.html"), os.path.join(ROOT, "docs", "Tradewind_TW-1_Datasheet_revB.pdf"))]
    for src, out in jobs:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                        "--print-to-pdf=" + out, "file://" + src + "?print=1"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("pdf:", out)


def prune():
    """Drop images a document no longer references."""
    for d in DOCS:
        html = open(os.path.join(d, "index.html")).read()
        used = set(re.findall(r'(?:src|href)="img/([^"]+)"', html))
        for f in os.listdir(os.path.join(d, "img")):
            if f not in used:
                os.remove(os.path.join(d, "img", f))


if __name__ == "__main__":
    collect()
    if "--pdf" in sys.argv:
        pdf()
        prune()
