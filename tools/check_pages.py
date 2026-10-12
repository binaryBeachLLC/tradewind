"""Report pages whose content overflows a US Letter sheet (headless Chrome, print geometry)."""
import re
import subprocess
import sys

JS = """<script>window.addEventListener("load",function(){
var out=[];document.querySelectorAll(".page,.ds-page").forEach(function(p,i){p.style.height="11in";p.style.minHeight="11in";p.style.width="8.5in";p.style.overflow="hidden";
var b=p.querySelector(".body,.ds-body");b.style.overflow="hidden";out.push((i+1)+":"+(b.scrollHeight-b.clientHeight))});
document.body.insertAdjacentHTML("beforeend","<pre id=overflow>"+out.join(" ")+"</pre>")})</script>"""


def check(path):
    import os
    path = os.path.abspath(path)
    html = open(path).read()
    tmp = path.replace(".html", ".chk.html")
    open(tmp, "w").write(html.replace("</body>", JS + "</body>"))
    dom = subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--virtual-time-budget=10000", "--run-all-compositor-stages-before-draw", "--window-size=1400,1000",
                          "--dump-dom", "file://" + tmp], capture_output=True, text=True).stdout
    m = re.search(r'<pre id="overflow">([^<]*)</pre>', dom)
    res = [tuple(map(int, x.split(":"))) for x in m.group(1).split()] if m else []
    bad = [(p, o) for p, o in res if o > 2]
    print(path.split("/")[-2], "pages:", len(res), "overflowing:", bad if bad else "none")
    import os
    os.remove(tmp)
    return bad


if __name__ == "__main__":
    for p in sys.argv[1:]:
        check(p)
