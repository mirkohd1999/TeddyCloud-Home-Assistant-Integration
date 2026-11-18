import asyncio,json
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'www/teddycloud-homeassistant-card.js').read_text()
html='''<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{font:14px system-ui;margin:16px;background:#171717;color:#eee;--primary-text-color:#eee;--secondary-text-color:#bbb;--card-background-color:#242424;--divider-color:#555;--primary-color:#03a9f4;--text-primary-color:#fff}ha-card{display:block;box-sizing:border-box;background:#242424;max-width:850px;margin:auto}*{box-sizing:border-box}</style></head><body></body></html>'''
async def run():
 async with async_playwright() as p:
  browser=await p.chromium.launch()
  page=await browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
  errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
  requests=[]
  archive=BytesIO()
  with ZipFile(archive,'w') as zipfile:zipfile.writestr('library.json', '{}')
  archive_bytes=archive.getvalue()
  async def route(r):
   if '/api/' not in r.request.url:return await r.fulfill(status=200,content_type='text/html',body=html)
   requests.append((r.request.method,r.request.url))
   if r.request.method=='GET':return await r.fulfill(status=200,content_type='application/zip',body=archive_bytes)
   data={'token':'test-token','new':12,'existing':3,'conflicts':[{'audio_id':'100','title':'Benjamin Blümchen'}],'images':2} if 'action=preview' in r.request.url else {'imported':12}
   await r.fulfill(status=200,content_type='application/json',body=json.dumps(data))
  await page.route('http://teddycloud.test/**',route)
  await page.goto('http://teddycloud.test/')
  await page.add_script_tag(content=source)
  await page.evaluate('''() => {
   const card=document.createElement('teddycloud-tonie-library-card');
   card._entries=[];card.setConfig({});
   card.hass={user:{id:'admin',is_admin:true},language:'de',connection:{subscribeMessage:()=>Promise.resolve(()=>{})},fetchWithAuth:(url,init)=>fetch(url,init)};
   document.body.append(card);window.testCard=card;
  }''')
  await page.get_by_text('Bibliothek sichern und wiederherstellen',exact=True).click()
  async with page.expect_download() as downloaded:
   await page.get_by_role('button',name='Sicherung herunterladen',exact=True).click()
  download=await downloaded.value
  assert download.suggested_filename=='teddycloud-library.zip'
  assert Path(await download.path()).read_bytes()==archive_bytes
  await page.locator('#library-backup-file').set_input_files({'name':'library.zip','mimeType':'application/zip','buffer':b'test archive'})
  await page.get_by_text('Import-Vorschau',exact=True).wait_for()
  assert not any('action=import' in u for _,u in requests)
  assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  await page.screenshot(path='backup-mobile-qa.png',full_page=True)
  await page.locator('#backup-overwrite').check()
  await page.get_by_role('button',name='Import jetzt anwenden',exact=True).click()
  await page.get_by_text('Sicherung erfolgreich importiert',exact=True).wait_for()
  assert sum('action=import' in u for _,u in requests)==1
  await page.set_viewport_size({'width':1100,'height':850})
  await page.evaluate("window.testCard.hass={...window.testCard._hass,language:'en'}")
  await page.get_by_text('Back up and restore library',exact=True).wait_for()
  await page.screenshot(path='backup-desktop-qa.png',full_page=True)
  await page.evaluate("window.testCard.hass={...window.testCard._hass,user:{id:'user',is_admin:false}}")
  assert await page.locator('[data-backup-action]').count()==0
  assert errors==[],errors
  print('Chromium mobile/desktop: real upload event, preview, explicit import, English labels, role restriction and no horizontal overflow passed.')
  await browser.close()
asyncio.run(run())
