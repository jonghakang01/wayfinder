import glob, json, os
from playwright.sync_api import sync_playwright
exe=glob.glob(os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome'))[0]
tok=next(t for t,v in json.load(open(os.path.expanduser('~/.appdata/sessions.json'))).items()
         if (v if isinstance(v,str) else v.get('user'))=='jongha.kang')
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=exe)
    ctx=b.new_context(viewport={'width':425,'height':900},is_mobile=True,has_touch=True)
    ctx.add_cookies([{'name':'session','value':tok,'url':'http://localhost:8080'}])
    pg=ctx.new_page(); pg.goto('http://localhost:8080/momentum?tab=tasks',wait_until='domcontentloaded')
    pg.wait_for_timeout(800); pg.click('.tk-row'); pg.wait_for_timeout(400)
    print(pg.evaluate("""()=>{
      const vis=s=>{const e=document.querySelector(s);
        return e?getComputedStyle(e).display!=='none':null;};
      const save=[...document.querySelectorAll('.tk-sheet-actions .btn')][0].getBoundingClientRect();
      return {pillVisible:vis('.wf-back'), toggleVisible:vis('.wf-theme-btn'),
              saveHit:document.elementFromPoint(save.left+save.width/2, save.top+save.height/2)?.textContent?.trim()};}"""))
    b.close()
