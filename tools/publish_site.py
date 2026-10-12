"""Publish Tradewind's generated content into the binarybeach.tech site (repo binarybeach-site, no build step).

python3 tools/publish_site.py --site ~/github-repos/binarybeach-site/public

Writes only generated files; the hand-written page /hardware/tradewind/index.html lives in the site repo.
  reports/tradewind-design-report/   report, switched to the site's shared letterhead.css + report.js viewer
  reports/tradewind-datasheet/       datasheet, with the same viewer bar (report.js)
  reports/datasheet.css              the datasheet format, shared like letterhead.css
  hardware/tradewind/media/          3D models, renders, figures, schematic sheets, recolored PCB layers, turntable
  hardware/tradewind/files/          downloads (PDFs, Gerbers, BOM, STEP)
"""
import argparse
import glob
import os
import re
import shutil
import subprocess

TW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NOTE = ("Tradewind is our own reference design, taken from concept to field pilot. Simulations, CAD and board files are real; "
        "bench and field figures are representative values from the reference build.")


def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def jpg(src, dst, w):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run(["convert", src, "-resize", "%dx" % w, "-strip", "-quality", "86", dst], check=True)


def copy_imgs(html, src_dir, dst_dir):
    shutil.rmtree(os.path.join(dst_dir, "img"), ignore_errors=True)
    for ref in sorted(set(re.findall(r'(?:src|href)="img/([^"]+)"', html))):
        cp(os.path.join(src_dir, "img", ref), os.path.join(dst_dir, "img", ref))


def head(title, desc, client, back, pdf, css):
    return (f'<meta name="description" content="{desc}">\n<meta name="robots" content="noindex">\n'
            f'<link rel="icon" href="/assets/logo-64.png">\n<link rel="stylesheet" href="{css}">\n'
            f'<script src="/reports/report.js" data-client="{client}" data-back="{back}" data-file="{pdf}" data-note="{NOTE}"></script>\n')


def report(site):
    src = os.path.join(TW, "docs", "report")
    dst = os.path.join(site, "reports", "tradewind-design-report")
    html = open(os.path.join(src, "index.html")).read()
    html = re.sub(r"<title>.*?</title>", "<title>Tradewind TW-1 engineering report · Binary Beach</title>", html)
    html = re.sub(r'<link rel="icon"[^>]*><link rel="stylesheet" href="letterhead.css">', "", html)
    html = re.sub(r"<script>\n\(function\(\)\{var embed.*?</script>", "", html, flags=re.S)
    html = html.replace("</title>", "</title>\n" + head(
        "", "Engineering design and test report for Tradewind TW-1, a solar LoRaWAN field sensor: simulation, schematic, layout, "
        "enclosure, bring-up, characterization and a 30-day field pilot.", "Tradewind", "/hardware/tradewind/",
        "Tradewind_TW-1_Engineering_Report_revB.pdf", "/reports/letterhead.css"), 1)
    html = html.replace('src="img/logo.png"', 'src="/assets/logo-256.png"')
    copy_imgs(html, src, dst)
    open(os.path.join(dst, "index.html"), "w").write(html)


def datasheet(site):
    src = os.path.join(TW, "docs", "datasheet")
    dst = os.path.join(site, "reports", "tradewind-datasheet")
    html = open(os.path.join(src, "index.html")).read()
    html = re.sub(r"<title>.*?</title>", "<title>Tradewind TW-1 datasheet · Binary Beach</title>", html)
    html = re.sub(r'<link rel="icon"[^>]*><link rel="stylesheet" href="datasheet.css">', "", html)
    html = re.sub(r"<script>\(function\(\)\{var q=.*?</script>", "", html, flags=re.S)
    html = re.sub(r'<div class="ds-bar-screen">.*?</div>\n', "", html, flags=re.S)
    html = html.replace("</title>", "</title>\n" + head(
        "", "Tradewind TW-1 product datasheet: specifications, typical characteristics, connector functions, drawings and "
        "ordering information.", "Tradewind", "/hardware/tradewind/", "Tradewind_TW-1_Datasheet_revB.pdf",
        "/reports/datasheet.css"), 1)
    html = html.replace('src="img/logo.png"', 'src="/assets/logo-256.png"')
    # report previews on the site read the document type and title from these
    html = html.replace('<div class="ds-body">', '<div class="ds-body"><div class="doctype" hidden>Product datasheet</div>'
                        '<h1 hidden>Tradewind TW-1 · Solar LoRaWAN field sensor</h1>', 1)
    copy_imgs(html, src, dst)
    open(os.path.join(dst, "index.html"), "w").write(html)
    # shared datasheet format + the PDF-viewer frame used by every example document
    css = open(os.path.join(src, "datasheet.css")).read()
    viewer = open(os.path.join(site, "reports", "letterhead.css")).read()
    m = re.search(r"/\* On screen, an example report sits in a PDF-viewer frame.*?@media print\{\.rp-bar,\.rp-note\{display:none!important\}\}", viewer, re.S)
    if m:
        block = re.sub(r"/\* An \"Example\" ribbon.*?\n\}\n", "", m.group(0), flags=re.S)
        css += "\n/* ---------- PDF-viewer frame (same as letterhead.css; bar added by /reports/report.js) ---------- */\n" + block + "\n"
        css += "html.viewer .ds-page{margin-top:0}\n"
    open(os.path.join(site, "reports", "datasheet.css"), "w").write(css)


LAYER_COLORS = {"F_Cu": "#d9a441", "In1_Cu": "#3fa36b", "In2_Cu": "#e07a2e", "B_Cu": "#4d86d1",
                "F_Silkscreen": "#f4f4ef"}


def media(site):
    M = os.path.join(site, "hardware", "tradewind", "media")
    F = os.path.join(site, "hardware", "tradewind", "files")
    for f in ("assembly", "exploded", "enclosure_only"):
        cp(os.path.join(TW, "mechanical", "out", "web", f + ".glb"), os.path.join(M, "3d", f + ".glb"))
    cp(os.path.join(TW, "hardware", "fab", "3d", "tradewind_revB_web.glb"), os.path.join(M, "3d", "board.glb"))
    renders = glob.glob(os.path.join(TW, "render", "out", "*.png")) or glob.glob(os.path.join(TW, "render", "out", "jpg", "*.jpg"))
    for r in renders:
        name = os.path.splitext(os.path.basename(r))[0]
        jpg(r, os.path.join(M, "renders", name + ".jpg"), 1800)
    for k in glob.glob(os.path.join(TW, "render", "out", "kicad", "*.png")):
        jpg(k, os.path.join(M, "renders", "kicad_" + os.path.basename(k).replace(".png", ".jpg")), 1800)
    for fig in ("sim_thermal_enclosure", "sim_solar_iv", "test_s11", "test_field_battery", "test_bringup_sleep",
                "block_diagram", "mech_ga_enclosure"):
        cp(os.path.join(TW, "docs", "figures", fig + ".png"), os.path.join(M, "fig", fig + ".png"))
    for s in glob.glob(os.path.join(TW, "docs", "schematic", "*.svg")):
        cp(s, os.path.join(M, "sch", os.path.basename(s).replace("tradewind-", "").replace("tradewind.svg", "Root.svg")))
    os.makedirs(os.path.join(M, "layers"), exist_ok=True)
    for name, color in LAYER_COLORS.items():
        s = open(os.path.join(TW, "hardware", "fab", "svg", name + ".svg")).read()
        for c in set(re.findall(r"#[0-9A-Fa-f]{6}", s)):
            u = c.upper()
            s = s.replace(c, {"#000000": c, "#FFFFFF": "#0e1316", "#D0D2CD": "#8f9aa0"}.get(u, color))
        open(os.path.join(M, "layers", name + ".svg"), "w").write(re.sub(r"<title>.*?</title>", "<title>%s</title>" % name, s))
    mp4 = os.path.join(TW, "render", "out", "turntable.mp4")
    if os.path.exists(mp4):
        cp(mp4, os.path.join(M, "turntable.mp4"))
    for src, dst in (("docs/Tradewind_TW-1_Engineering_Report_revB.pdf", "Tradewind_TW-1_Engineering_Report_revB.pdf"),
                     ("docs/Tradewind_TW-1_Datasheet_revB.pdf", "Tradewind_TW-1_Datasheet_revB.pdf"),
                     ("hardware/fab/tradewind_revB_gerbers.zip", "tradewind_revB_gerbers.zip"),
                     ("hardware/fab/BOM_tradewind_revB.csv", "BOM_tradewind_revB.csv"),
                     ("hardware/fab/3d/tradewind_revB.step", "tradewind_revB_board.step"),
                     ("docs/schematic/tradewind_schematic.pdf", "tradewind_revB_schematic.pdf")):
        cp(os.path.join(TW, src), os.path.join(F, dst))
    z = os.path.join(F, "tradewind_enclosure_step_stl.zip")
    if os.path.exists(z):
        os.remove(z)
    subprocess.run(["zip", "-q", "-j", z, os.path.join(TW, "mechanical", "out", "tradewind_assembly.step")]
                   + glob.glob(os.path.join(TW, "mechanical", "out", "stl", "*.stl")), check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="path to binarybeach-site/public")
    a = ap.parse_args()
    site = os.path.abspath(os.path.expanduser(a.site))
    report(site)
    datasheet(site)
    media(site)
    print("published to", site)
