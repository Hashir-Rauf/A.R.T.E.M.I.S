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
    def vis(): return page.locator("body").inner_text()
    def flat(t): return t.replace("\n"," | ")
    tb=page.get_by_role("textbox")
    for i in range(tb.count()):
        try: log(f"textbox {i} visible={tb.nth(i).is_visible()} label={tb.nth(i).get_attribute('aria-label')} ph={tb.nth(i).get_attribute('placeholder')}")
        except Exception as e: pass
    vt=[tb.nth(i) for i in range(tb.count()) if tb.nth(i).is_visible()]
    vt[0].fill(str(folder)); log("typed folder path into first visible textbox")
    page.get_by_role("button",name="Add folder").click(); time.sleep(4)
    log("after Add folder: "+flat(vis().split("Keep it on this computer")[-1][:600]))
    page.screenshot(path="f2.png")
    page.get_by_role("tab",name="Work").click(); time.sleep(1)
    tas=page.locator("textarea:visible"); log(f"textareas {tas.count()}")
    def ask(q,wait=40):
        tas.first.fill(q); log("ASK: "+q)
        page.get_by_role("button",name="Ask",exact=True).click()
        time.sleep(wait)
        a=vis(); i=a.find("Clear conversation")
        log("SCREEN AFTER: "+flat(a[max(0,i-1800):i] if i>0 else a[-1500:]))
    def tail(n=1200):
        a=vis(); return flat(a[a.find("Undo last change"):][:n])
    ask("What did Lee 2021 say about the effect on attention, and what page? Also what did Jones 2020 find?")
    page.screenshot(path="w3.png")
    ask("Draft a short paragraph for section 2.3 comparing Smith 2019 and Lee 2021, with the source of each statement.",wait=50)
    page.screenshot(path="w4.png")
    page.get_by_role("button",name="Suggest a tidy-up").click(); time.sleep(30)
    log("TIDY: "+tail(1500)); page.screenshot(path="w5.png")
    page.get_by_role("tab",name="What it knows").click(); time.sleep(3)
    log("KNOWS: "+tail(2500)); page.screenshot(path="k1.png")
    page.get_by_role("tab",name="Settings").click(); time.sleep(3)
    log("SETTINGS: "+flat(vis().split("Settings | Settings")[-1][:3000])); page.screenshot(path="s1.png")
    browser.close()
app.stop()
