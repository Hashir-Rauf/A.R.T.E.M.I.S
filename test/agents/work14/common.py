import sys, time; sys.path.insert(0, r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/tests/agents")
from harness import *
from playwright.sync_api import sync_playwright
LOG=r"E:/Education/FAST-NUCES/Final Year Project/A.R.T.E.M.I.S/test/agents/work14/actions.log"
def log(m):
    s=time.strftime("%H:%M:%S")+" "+m; print(s.encode("ascii","replace").decode()); open(LOG,"a",encoding="utf-8").write(s+"\n")
