"""Paginate the report: flow each chapter across fixed US Letter pages, measured in headless Chrome.

The report is written as a list of page bodies. Here they become a flow:
- a body that starts with an <h2> (a chapter) starts a new page; so do the cover and any body whose first
  block carries data-break; everything else runs on after the previous body;
- the flow is cut into pages at top-level blocks, so a block is never split, and a heading (with its intro
  paragraph) never ends a page;
- a two-column block (.grid2) that holds a full-width chart is unwrapped, so the chart prints full width
  (a 6.8 in chart squeezed into half a column prints its text at about half size).

Chrome lays the pages out and reports which blocks land on which page; the HTML is then rebuilt from the
original blocks, so the output stays plain static pages.
"""
import json
import os
import re
import subprocess
import tempfile

TAG = re.compile(r"<!--.*?-->|<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>", re.S)
VOID = {"img", "br", "hr", "meta", "link", "input", "source", "col", "wbr"}


def blocks(html):
    """Top-level elements of an HTML fragment, as strings."""
    out, depth, start = [], 0, None
    for m in TAG.finditer(html):
        if m.group(0).startswith("<!--"):
            continue
        close, name, selfclose = m.group(1), m.group(2).lower(), m.group(3)
        if not close:
            if depth == 0:
                start = m.start()
            if name not in VOID and not selfclose:
                depth += 1
            elif depth == 0:
                out.append(html[start:m.end()])
        else:
            depth -= 1
            if depth == 0:
                out.append(html[start:m.end()])
    assert depth == 0, "unbalanced HTML in a page body"
    return out


def unwrap_charts(body, is_chart):
    """Replace each .grid2 whose figures include a full-width chart by its columns' contents, in order."""
    res = []
    for b in blocks(body):
        if b.startswith('<div class="grid2') and any(is_chart(s) for s in re.findall(r'src="img/([^"]+)"', b)):
            inner = b[b.index(">") + 1:b.rindex("</div>")]
            for col in blocks(inner):
                res += blocks(col[col.index(">") + 1:col.rindex("</div>")])
        else:
            res.append(b)
    return res


JS = r"""<script id="paginate">window.addEventListener("load",function(){
function prep(p){p.style.height="11in";p.style.minHeight="11in";p.style.width="8.5in";p.style.overflow="hidden";
  p.querySelector(".body").style.overflow="hidden"}
var pages=Array.from(document.querySelectorAll(".page"));pages.forEach(prep);
var shell=pages[0].cloneNode(true);shell.querySelector(".body").innerHTML="";
// 1. join every body into its chapter's flow
for(var k=pages.length-1;k>=2;k--){var b=pages[k].querySelector(".body"),f=b.firstElementChild;
  if(!f||f.tagName==="H2"||f.hasAttribute("data-break"))continue;
  var prev=pages[k-1].querySelector(".body");while(b.firstChild)prev.appendChild(b.firstChild);pages[k].remove()}
// 2. cut the flow into pages
function over(b){var cs=getComputedStyle(b),lim=b.getBoundingClientRect().bottom-parseFloat(cs.paddingBottom)+1;
  var c=b.children;for(var i=0;i<c.length;i++){var r=c[i].getBoundingClientRect(),mb=parseFloat(getComputedStyle(c[i]).marginBottom)||0;
    if(r.bottom+Math.min(mb,10)>lim)return i}return -1}
var p=document.querySelector(".page");
while(p){var b=p.querySelector(".body"),i=over(b);
  if(i>0){var c=b.children,isH=function(e){return /^H[1-4]$/.test(e.tagName)};
    while(i>0&&(isH(c[i-1])||(i>1&&c[i-1].tagName==="P"&&isH(c[i-2]))))i--;}
  if(i>0){var np=shell.cloneNode(true);var nb=np.querySelector(".body");
    while(b.children.length>i)nb.appendChild(b.children[i]);p.after(np)}
  p=p.nextElementSibling;while(p&&!p.classList.contains("page"))p=p.nextElementSibling}
var out=Array.from(document.querySelectorAll(".page")).map(function(p){
  return Array.from(p.querySelector(".body").children).map(function(c){return c.getAttribute("data-blk")})});
var tooBig=Array.from(document.querySelectorAll(".page")).map(function(p,k){return [k+1,over(p.querySelector(".body"))]}).filter(function(x){return x[1]>=0});
var wide=[];document.querySelectorAll(".page").forEach(function(p,k){p.querySelectorAll("table").forEach(function(t){
  if(t.getBoundingClientRect().right>t.parentElement.getBoundingClientRect().right+1)wide.push(k+1)})});
document.body.insertAdjacentHTML("beforeend","<pre id=plan>"+JSON.stringify({pages:out,overflow:tooBig,wide:wide})+"</pre>")})</script>"""


def paginate(page_bodies, render, is_chart, workdir):
    """page_bodies: list of body HTML strings. render(list_of_bodies) -> full HTML document.
    Returns the new list of page bodies."""
    flat, per_page = [], []
    for pi, body in enumerate(page_bodies):
        bl = unwrap_charts(body, is_chart) if pi else blocks(body)
        ids = []
        for b in bl:
            ids.append(len(flat))
            flat.append(b)
        per_page.append(ids)
    tagged = []
    for ids in per_page:
        tagged.append("\n".join(re.sub(r"^<([a-zA-Z0-9]+)", r'<\1 data-blk="%d"' % i, flat[i], count=1) for i in ids))
    html = render(tagged).replace("</body>", JS + "</body>")
    fd, tmp = tempfile.mkstemp(suffix=".html", dir=workdir)
    with os.fdopen(fd, "w") as fh:
        fh.write(html)
    try:
        dom = subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--virtual-time-budget=15000",
                              "--run-all-compositor-stages-before-draw", "--window-size=1400,1000", "--dump-dom",
                              "file://" + tmp + "?print=1"], capture_output=True, text=True).stdout
    finally:
        os.remove(tmp)
    m = re.search(r'<pre id="plan">(.*?)</pre>', dom, re.S)
    plan = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&"))
    if plan["overflow"]:
        print("paginate: blocks taller than a page on pages", [p for p, _ in plan["overflow"]])
    if plan["wide"]:
        print("paginate: tables wider than their column on pages", sorted(set(plan["wide"])))
    return ["\n".join(flat[int(i)] for i in ids) for ids in plan["pages"]]
