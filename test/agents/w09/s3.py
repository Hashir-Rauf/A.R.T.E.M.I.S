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
(folder/"receipt_scan_001.jpg").write_bytes(b"x")
try:
  with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    time.sleep(2)
    page.get_by_role("tab",name="Folders").click(); time.sleep(1)
    page.locator("input:visible").first.fill(str(folder)); page.get_by_role("button",name="Add folder").click(); time.sleep(3)
    log("ADDED FOLDER; text: "+page.inner_text("body").replace("\n"," | ")[500:2500])
    shot(page,folder,"folders")
    page.get_by_role("tab",name="Work").click(); time.sleep(1.5)
    ta=page.locator("textarea:visible, input[type=text]:visible"); log("work inputs "+str(ta.count()))
    def ask(q,wait=40):
        box=ta.first; box.fill(q); page.get_by_role("button",name="Ask",exact=True).click(); log("ASKED: "+q)
        time.sleep(wait); log("SCREEN: "+page.inner_text("body").replace("\n"," | ")[-2200:]); shot(page,folder,"ask"+str(abs(hash(q))%999))
    ask("What is in this folder? Which files are about Rana Traders?")
    ask("Does anything leave my computer when you read these files? Who is responsible if you get something wrong?",35)
    browser.close()
finally:
    app.stop()
