from common import *
app = App("ua-11", 7951).start()
folder = make_user_folder(WORK / "ua-11" / "stuff", "messy")
(folder/"AML_policy_review_notes.txt").write_text("Invented notes: review of AML transaction monitoring thresholds. Action: escalate 3 alerts by Friday. Owner: Naveed.\n")
(folder/"audit_findings_Q3.txt").write_text("Invented: Finding 4 - access recertification overdue for 12 accounts. Due date 30 Nov.\n")
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.wait_for_timeout(2000)
    for t in ["Settings","What it knows","Folders"]:
        tab(page,t); log(f"clicked tab {t}; visible: "+vis(page)[:2500]); shot(page,folder,"tab_"+t.replace(" ","_"))
    browser.close()
app.stop()
