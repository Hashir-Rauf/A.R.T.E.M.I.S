import sys,time,os; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
L=open("actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+m; print(s); L.write(s+"\n"); L.flush()
app = App("ua-04", 7944).start()
folder = make_user_folder(WORK / "ua-04" / "stuff", "notes")
# extra persona files
for n,t in {"thesis-ch2-draft.md":"# Chapter 2 draft\nClaim: sleep loss reduces working memory (Smith 2019, p.14). TODO: check Lee 2021 contradicts this.\n",
 "supervisor-meeting-2026-10-28.md":"# Meeting with Dr Anwar\nActions: rewrite section 2.3; run the regression again on cleaned data; send Ch2 by 15 Nov. She doubts the sample size in Lee 2021.\n",
 "reading-notes-smith2019.md":"# Smith 2019 notes\nN=48 students. Found working memory drop of 12% after 24h sleep deprivation (p.14). Limitation: only young adults.\n",
 "reading-notes-lee2021.md":"# Lee 2021 notes\nN=210. No significant effect on working memory, but effect on attention (p.7).\n"}.items():
    open(os.path.join(folder,n),"w",encoding="utf-8").write(t)
log(f"folder {folder}")
with sync_playwright() as pw:
    browser, page = browser_page(pw, app)
    page.get_by_role("tab",name="Folders").click()
    time.sleep(1); log("clicked Folders tab; visible: "+page.locator("main, body").first.inner_text()[:100].replace("\n"," | "))
    page.screenshot(path="f1.png")
    ins=page.locator("input:visible")
    for i in range(ins.count()): log(f"input {i} ph={ins.nth(i).get_attribute('placeholder')} type={ins.nth(i).get_attribute('type')}")
    btns=page.locator("button:visible")
    log("buttons: "+" | ".join(btns.nth(i).inner_text().strip() for i in range(btns.count())))
    browser.close()
app.stop()
