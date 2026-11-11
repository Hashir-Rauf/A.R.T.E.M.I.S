import sys,time,os; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
L=open("actions.log","a",encoding="utf-8"); sys.stdout.reconfigure(encoding="utf-8")
def log(m):
    s=f"[{time.strftime('%H:%M:%S')}] {m}"; print(s); L.write(s+"\n"); L.flush()
app = App("ua-11", 7951).start()
folder = make_user_folder(WORK / "ua-11" / "stuff", "messy")
(folder/"AML_policy_review_notes.txt").write_text("Invented notes: review of AML transaction monitoring thresholds. Action: escalate 3 alerts by Friday. Owner: Naveed.\n")
(folder/"audit_findings_Q3.txt").write_text("Invented: Finding 4 - access recertification overdue for 12 accounts. Due date 30 Nov.\n")
log(f"started app; folder {folder}; files: {sorted(os.listdir(folder))}")
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(2000)
    page.locator("text=Folders >> visible=true").first.click(); page.wait_for_timeout(1000)
    log("Folders tab:\n"+page.inner_text("body")[900:3500])
    ins=[(i.get_attribute("placeholder"),i.is_visible()) for i in page.query_selector_all("input,textarea")]
    log(f"inputs {ins}")
    shot(page, folder, "folders")
    browser.close()
app.stop()
