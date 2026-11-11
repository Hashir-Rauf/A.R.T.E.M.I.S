import sys, time, os, io, contextlib, traceback
sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=open(r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/w06/actions.log","a",encoding="utf-8")
def log(m):
    s=time.strftime("%H:%M:%S ")+str(m); print(s); LOG.write(s+"\n"); LOG.flush()
app = App("ua-06", 7946).start()
folder = make_user_folder(WORK / "ua-06" / "stuff", "project")
log(f"app started, folder={folder}")
pw = sync_playwright().start()
browser, page = browser_page(pw, app)
G=dict(globals())
D=r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/w06/"
n=0
while True:
    f=D+f"cmd_{n}.py"
    if os.path.exists(f):
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf):
            try: exec(open(f,encoding="utf-8").read(),G)
            except Exception: traceback.print_exc(file=sys.stdout)
        open(D+f"out_{n}.txt","w",encoding="utf-8").write(buf.getvalue())
        n+=1
        if G.get("QUIT"): break
    time.sleep(0.5)
app.stop(); browser.close(); pw.stop()
open(D+"done.txt","w").write("ok")
