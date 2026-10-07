"""
README ekran şəkillərini (qaranlıq tema) yenidən çəkir.

    python sened/ekranlar/yarat.py        # Playwright + Chromium lazımdır
"""
import shutil
import sys
import tempfile
import time
from pathlib import Path

KÖK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KÖK / "alqorc"))
from studio.server import Studio
from playwright.sync_api import sync_playwright
ç = Path(__file__).resolve().parent
q = Path(tempfile.mkdtemp(prefix="alqor-ekran-"))
shutil.copy(ç / "idarə-paneli.alqor", q)
shutil.copy(KÖK / "numuneler" / "09-tapsiriqlar.alqor", q)
s = Studio(q).fonda_başlat()

def gözlə_çərçivə(p, seçici, müddət=25):
    son = time.monotonic() + müddət
    while time.monotonic() < son:
        try:
            if p.frame_locator("#onbaxis-cercive").locator(seçici).count():
                return
        except Exception:
            pass
        p.wait_for_timeout(200)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={"width": 1440, "height": 860}, color_scheme="dark",
                   device_scale_factor=1)
    p.goto(s.ünvan()); p.wait_for_selector(".düyün")
    while p.get_attribute("html", "data-tema") != "qaranlıq":
        p.click("#dym-tema"); p.wait_for_timeout(150)
    p.click('.düyün[data-yol="idarə-paneli.alqor"]'); p.wait_for_selector(".tab.aktiv")
    p.click('[data-panel="palet"]'); p.wait_for_timeout(300)
    p.click("#dym-onbaxis")
    gözlə_çərçivə(p, ".v-qrafik")
    p.wait_for_timeout(800)
    p.screenshot(path=str(ç / "studio-qaranliq.png"))
    # Xüsusiyyətlər paneli
    p.locator(".fayl-elementi", has_text="düymə").first.click()
    p.wait_for_selector("#xus-forma:not([hidden]) .xüs-başlıq")
    p.fill('[data-xus="üslub.fon"]', "#16a34a")
    p.wait_for_timeout(2500)
    gözlə_çərçivə(p, "button.v-düymə[style*='16a34a']")
    p.wait_for_timeout(600)
    p.screenshot(path=str(ç / "studio-xususiyyetler.png"))
    # 09 nümunəsi — tapşırıq meneceri
    p.click('[data-panel="layihe"]')
    p.click('.düyün[data-yol="09-tapsiriqlar.alqor"]'); p.wait_for_timeout(500)
    gözlə_çərçivə(p, ".v-düymə")
    p.wait_for_timeout(1200)
    p.screenshot(path=str(ç / "studio-tapsiriqlar.png"))
    b.close()
s.dayandır()
shutil.rmtree(q, ignore_errors=True)
