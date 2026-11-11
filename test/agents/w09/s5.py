import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open(r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/w09/actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s[:3000].encode("ascii","replace").decode()); LOG.write(s+"\n"); LOG.flush()
app = App("ua-09", 7949).start()
folder = make_user_folder(WORK / "ua-09" / "stuff", "messy")
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    time.sleep(2)
    page.get_by_role("tab",name="Folders").click(); time.sleep(1)
    inp=page.locator("input:visible").first
    inp.click(); page.keyboard.type(str(folder),delay=2)
    page.keyboard.press("Tab"); time.sleep(0.5); log("after Tab val=%r"%inp.input_value()[:25])
    page.keyboard.press("Tab"); time.sleep(0.3)
    log("focused: "+page.evaluate("document.activeElement.innerText"))
    page.keyboard.press("Enter"); time.sleep(4)
    log("RESULT: "+page.inner_text("body").replace(chr(10)," | ")[:420])
    shot(page,folder,"kbd")
    browser.close()
finally:
    app.stop()
