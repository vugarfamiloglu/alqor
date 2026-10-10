"""
`alqor yerləşdir` — proqramı internetə çıxarmaq üçün hazır paket.

İki növ var, layihəyə baxıb avtomatik seçilir:

  statik   `gətir veb` yoxdur → proqram JavaScript-ə çevrilir, nəticə
           sadə HTML qovluğudur. Server lazım deyil: GitHub Pages,
           Netlify, Cloudflare Pages, istənilən hostinq. İnterfeys
           proqramları (`gətir pəncərə`, komponentlər, `vidjet`) da
           statikdir: pəncərə səhifənin özündə göstərilir, hadisələr
           brauzerdə işləyir. `pəncərə` idxal edən proqramın `veb` budağı
           (`-- veb` arqumenti) statik saytda işləmir.

  server   `gətir veb` var (və `gətir pəncərə` yoxdur) → `Dockerfile` +
           `tetbiq.pyz`. Render, Fly.io,
           Railway, öz VPS-iniz — Docker işlədən hər yer. Port platformanın
           verdiyi `PORT` dəyişənindən götürülür (`veb.Server.dinlə`).

    alqor yerləşdir                 avtomatik
    alqor yerləşdir --statik        məcburi statik
    alqor yerləşdir --server        məcburi Docker
    alqor yerləşdir fayl.alq        layihəsiz tək fayl
    alqor yerləşdir --çıxış docs    GitHub Pages üçün `docs/` qovluğu

Nəticə qovluğunda `YERLESDIR.md` — seçilən platforma üçün addımlar.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path


class YerləşdirməXətası(RuntimeError):
    pass


@dataclass
class Nəticə:
    növ: str          # "statik" | "server"
    qovluq: Path
    təlimat: Path


def _mənbələr(layihə) -> list[Path]:
    q = layihə.kök / "mənbə"
    fayllar = [layihə.giriş]
    if q.is_dir():
        fayllar += [f for f in sorted(q.rglob("*.alq")) if f != layihə.giriş]
    return fayllar


def serverdirmi(layihə) -> bool:
    """`gətir veb` var, `gətir pəncərə` yoxdur → server tətbiqi.

    Hər ikisini idxal edən proqram (nümunə 08, 09) əsasən desktop
    interfeysidir: veb serveri yalnız `-- veb` arqumenti ilə qalxır,
    Docker paketi isə arqumentsiz işləyir — ona görə statik sayt olur.
    """
    veb = pəncərə = False
    for f in _mənbələr(layihə):
        try:
            m = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        veb = veb or bool(re.search(r"^\s*gətir\s+veb\b", m, re.M))
        pəncərə = pəncərə or bool(
            re.search(r"^\s*gətir\s+pəncərə\b", m, re.M))
    return veb and not pəncərə


_DOCKERFILE = """\
# {ad} — Alqor veb tətbiqi (alqor yerləşdir yaradıb)
FROM python:3.12-slim
WORKDIR /app
COPY tetbiq.pyz /app/tetbiq.pyz
ENV PYTHONIOENCODING=utf-8 \\
    PYTHONUNBUFFERED=1 \\
    ALQOR_HOST=0.0.0.0 \\
    PORT=8080 \\
    ALQOR_KES=/tmp/alqor
EXPOSE 8080
RUN useradd --create-home alqor
USER alqor
CMD ["python", "/app/tetbiq.pyz"]
"""

_SERVER_TƏLİMATI = """\
# {ad} — vebə yerləşdirmə (server tətbiqi)

Bu qovluqda hər şey hazırdır:

| Fayl | Nədir |
|---|---|
| `tetbiq.pyz` | Proqramınız və Alqor icra mühiti — tək fayl |
| `Dockerfile` | Konteyner təsviri (Python 3.12) |

Server portu platformanın verdiyi `PORT` dəyişənindən götürür, kodda
dəyişiklik lazım deyil.

## Yerli yoxlama

```
python tetbiq.pyz          # http://127.0.0.1:8080
```

Docker ilə:

```
docker build -t {sistem_adı} .
docker run -p 8080:8080 {sistem_adı}
```

## Render.com (pulsuz plan var)

1. Bu qovluğu GitHub-da yeni repoya yükləyin.
2. render.com → **New → Web Service** → reponu seçin.
3. **Runtime: Docker** seçilir (Dockerfile avtomatik tapılır) → **Create**.
4. Bir neçə dəqiqəyə `https://<ad>.onrender.com` ünvanı hazır olur.

## Fly.io

```
fly launch --now        # Dockerfile tapılır, port 8080
fly deploy              # sonrakı yeniləmələr
```

## Öz serveriniz (VPS)

```
scp -r . istifadəçi@server:/opt/{sistem_adı}
ssh istifadəçi@server
cd /opt/{sistem_adı}
docker build -t {sistem_adı} . && docker run -d --restart always -p 80:8080 {sistem_adı}
```

Docker olmadan: serverdə Python 3.12 qurun və
`ALQOR_HOST=0.0.0.0 PORT=80 python tetbiq.pyz` işlədin.

## Yeniləmək

Kodu dəyişdikdən sonra layihə qovluğunda yenidən `alqor yerləşdir`
işlədin və bu qovluğu təzədən yükləyin.
"""

_STATİK_TƏLİMATI = """\
# {ad} — vebə yerləşdirmə (statik sayt)

Proqramınız JavaScript-ə çevrilib: `index.html` brauzerdə işləyir, server
lazım deyil. Əvvəlcə yoxlayın — `index.html`-i iki dəfə klikləyib açın.

Desktop interfeysi (`pəncərə`, komponentlər, vidjetlər) səhifənin özündə
göstərilir. Dialoqlar brauzerin `confirm`/`prompt` pəncərələri ilə açılır;
fayl dialoqları və fayl sistemi brauzerdə yoxdur (icra xətası verir).

## Netlify Drop — ən asan yol (1 dəqiqə)

1. https://app.netlify.com/drop açın (pulsuz hesab).
2. **Bu qovluğu** səhifəyə sürükləyib buraxın.
3. `https://<təsadüfi-ad>.netlify.app` ünvanı dərhal hazırdır.

## GitHub Pages

1. Layihədə `alqor yerləşdir --çıxış docs` işlədin və `docs/` qovluğunu
   commit edin.
2. GitHub → repo → **Settings → Pages** → *Branch: main*, *Folder: /docs*.
3. Ünvan: `https://<istifadəçi>.github.io/<repo>/`.

## Cloudflare Pages

dash.cloudflare.com → **Workers & Pages → Create → Pages → Upload
assets** → bu qovluğu yükləyin.

## Öz hostinqiniz

Bu qovluğun məzmununu (FTP, cPanel) saytın kök qovluğuna (`public_html`)
köçürün.

## Yeniləmək

Kodu dəyişdikdən sonra yenidən `alqor yerləşdir` işlədin və qovluğu
təzədən yükləyin.
"""


def _sistem_adı(ad: str) -> str:
    a = ad.translate(str.maketrans("əıöüğşçƏİÖÜĞŞÇ", "eiougscEIOUGSC")).lower()
    return re.sub(r"[^a-z0-9-]+", "-", a).strip("-") or "alqor-tetbiq"


def statik(layihə, çıxış: Path) -> Nəticə:
    from .js import KompilyasiyaXətası, veb_səhifəsi
    from .lekser import Lekser
    from .menbe import Mənbə
    from .parser import Parser
    from .xeta import XətaToplayıcı
    x = XətaToplayıcı()
    m = Mənbə.fayldan(layihə.giriş, x)
    if m is None:
        raise YerləşdirməXətası(f"oxunmadı: {layihə.giriş}")
    ağac = Parser(Lekser(m, x).leksə(), m, x).ayır()
    if not x.uğurludur():
        raise YerləşdirməXətası("proqramda xəta var:\n\n" + x.hesabat())
    try:
        səhifə = veb_səhifəsi(ağac, layihə.ad, layihə.giriş.resolve())
    except KompilyasiyaXətası as e:
        raise YerləşdirməXətası(
            f"statik sayta çevrilmədi: {e}\n"
            "  (server tətbiqi üçün: alqor yerləşdir --server)")
    if çıxış.exists():
        shutil.rmtree(çıxış)
    çıxış.mkdir(parents=True)
    (çıxış / "index.html").write_text(səhifə, encoding="utf-8")
    (çıxış / "404.html").write_text(səhifə, encoding="utf-8")
    (çıxış / ".nojekyll").write_text("")
    t = çıxış / "YERLESDIR.md"
    t.write_text(_STATİK_TƏLİMATI.format(ad=layihə.ad), encoding="utf-8")
    return Nəticə("statik", çıxış, t)


def server(layihə, çıxış: Path, alqorc_kökü: Path) -> Nəticə:
    from . import qurucu
    from .exe_qurucu import QurmaXətası, sintaksisi_yoxla
    try:
        sintaksisi_yoxla(layihə)
    except QurmaXətası as e:
        raise YerləşdirməXətası(str(e))
    n = qurucu.qur(layihə, alqorc_kökü)
    if çıxış.exists():
        shutil.rmtree(çıxış)
    çıxış.mkdir(parents=True)
    shutil.copyfile(n.yol, çıxış / "tetbiq.pyz")
    sa = _sistem_adı(layihə.ad)
    (çıxış / "Dockerfile").write_text(_DOCKERFILE.format(ad=layihə.ad),
                                      encoding="utf-8")
    (çıxış / ".dockerignore").write_text("YERLESDIR.md\n", encoding="utf-8")
    t = çıxış / "YERLESDIR.md"
    t.write_text(_SERVER_TƏLİMATI.format(ad=layihə.ad, sistem_adı=sa),
                 encoding="utf-8")
    return Nəticə("server", çıxış, t)


def yerləşdir(layihə, alqorc_kökü: Path, növ: str | None = None,
              çıxış: Path | None = None) -> Nəticə:
    növ = növ or ("server" if serverdirmi(layihə) else "statik")
    çıxış = çıxış or layihə.çıxış / "yerləşdir"
    if növ == "server":
        return server(layihə, çıxış, alqorc_kökü)
    return statik(layihə, çıxış)
