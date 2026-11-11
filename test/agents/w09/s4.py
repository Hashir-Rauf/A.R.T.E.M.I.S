import sys,time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open(r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/w09/actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s[:3000].encode("ascii","replace").decode()); LOG.write(s+"\n"); LOG.flush()
app = App("ua-09", 7949).start()
folder = make_user_folder(WORK / "ua-09" / "stuff", "messy")
(folder/"Client_Rana_Traders_2025_sales.csv").write_text("date,item,amount\n2025-07-01,rice,12000\n2025-07-02,oil,8500\n")
(folder/"Rana_Traders_tax_notes.txt").write_text("Rana Traders NTN 1234567-8. Sales tax return due 15 Dec. Missing receipts for August; client to send scans. Owes advance tax PKR 45,000.\n")
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    time.sleep(2)
    page.get_by_role("tab",name="Folders").click(); time.sleep(1)
    tb=page.get_by_role("textbox"); log("textboxes "+str(tb.count()))
    page.locator("input[type=text]:visible, input:not([type]):visible").first.click(); page.keyboard.type(str(folder),delay=5); log("typed value: "+page.locator("input:visible").first.input_value())
    inp=page.locator("input:visible").first
    log("before click value: "+inp.input_value())
    page.keyboard.press("Enter"); time.sleep(1)
    log("after enter value: "+repr(inp.input_value())+" msg: "+page.inner_text("body")[330:480].replace(chr(10)," | "))
    log("ENTER result: "+page.inner_text("body").replace(chr(10)," | ")[150:420])
    page.wait_for_timeout(1500)
    inp.dispatch_event("input"); inp.dispatch_event("change")
    page.evaluate("document.querySelector('button.primary, button.lg.primary').scrollIntoView()")
    btn=page.get_by_role("button",name="Add folder"); box=btn.bounding_box(); page.mouse.move(box["x"]+5,box["y"]+5); page.mouse.down(); page.mouse.up(); time.sleep(4)
    log("AFTER ADD: "+page.inner_text("body").replace("\n"," | ")[:300]+" ... "+page.inner_text("body").replace("\n"," | ")[500:2500])
    shot(page,folder,"folders2")
    log("input value: "+page.locator("input:visible").first.input_value())
    browser.close()
finally:
    app.stop()
