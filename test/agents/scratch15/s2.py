import sys, time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open(r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/scratch15/actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s.encode("ascii","replace").decode()); LOG.write(s+"\n"); LOG.flush()
app = App("ua-15", 7955).start()
folder = make_user_folder(WORK / "ua-15" / "stuff", "notes")
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(2000)
    try: page.get_by_label("Voice is on").uncheck(timeout=3000); log("unticked voice")
    except Exception as e: log("voice untick fail")
    els=page.eval_on_selector_all("button,[role=tab],input,textarea,select","e=>e.map(x=>x.tagName+'|'+(x.id||'')+'|'+(x.getAttribute('role')||'')+'|'+(x.innerText||x.placeholder||'').slice(0,40)+'|'+(x.offsetParent?'vis':'hid'))")
    log("ELEMENTS "+"\n".join(els))
    log("files in folder: "+str(sorted(p.name for p in folder.rglob('*'))))
    browser.close()
finally:
    app.stop()
