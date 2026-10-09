"""
Python icraçısı ilə JS hədəfinin çıxışını müqayisə edir.

    python -m alqor.js.muqayise korpus.json [--node /yol/node] [-v]

Korpus: [{"kod", "giriş", "çıxış", "xəta"}] — `çıxış` və `xəta`
Python icraçısının nəticəsidir.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

from .derleyici import KompilyasiyaXətası, icra_mühiti, kompilyasiya


def node_tap() -> str | None:
    for n in (os.environ.get("ALQOR_NODE"), shutil.which("node"),
              "/opt/node22/bin/node"):
        if n and os.path.exists(n):
            return n
    return None


def _ağac(kod: str):
    from ..lekser import Lekser
    from ..menbe import Mənbə
    from ..parser import Parser
    from ..xeta import XətaToplayıcı
    x = XətaToplayıcı()
    s = Mənbə.mətndən(kod, "sınaq.alq", x)
    ağac = Parser(Lekser(s, x).leksə(), s, x).ayır()
    if not x.uğurludur():
        raise KompilyasiyaXətası("ayırma xətası")
    return ağac


_İŞLƏDİCİ = r"""
const nəticələr = [];
for (const [p, giriş] of $proqramlar) {
  const çıxış = []; const növbə = giriş.slice(); let xəta = null;
  if (p === null) { nəticələr.push(null); continue; }
  $.sıfırla();
  try {
    $.işlət(p, { yaz: s => çıxış.push(s), yazSətirsiz: s => çıxış.push(s),
                 yazXəta: () => {}, oxu: () => növbə.length ? növbə.shift() : "",
                 xəta: e => { xəta = e.tip; } });
  } catch (e) { xəta = "JS:" + String(e && e.stack || e); }
  nəticələr.push({ çıxış, xəta });
}
process.stdout.write(JSON.stringify(nəticələr));
"""


def js_işlət(nümunələr: list[dict], node: str) -> list[dict | None]:
    """Hər nümunəni kompilyasiya edib tək node prosesində işlədir."""
    hissələr = [icra_mühiti(), "const $proqramlar = [];"]
    kompilyasiya_xətaları: dict[int, str] = {}
    for i, n in enumerate(nümunələr):
        try:
            js = kompilyasiya(_ağac(n["kod"]))
            hissələr.append("$proqramlar.push([(function () {\n" + js +
                            "\nreturn $proqram;\n})(), " +
                            json.dumps(n.get("giriş") or [],
                                       ensure_ascii=False) + "]);")
        except KompilyasiyaXətası as x:
            kompilyasiya_xətaları[i] = str(x)
            hissələr.append("$proqramlar.push([null, []]);")
        except Exception as x:                      # noqa: BLE001
            kompilyasiya_xətaları[i] = f"KOMPİLYATOR: {type(x).__name__}: {x}"
            hissələr.append("$proqramlar.push([null, []]);")
    hissələr.append(_İŞLƏDİCİ)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write("\n".join(hissələr))
        yol = f.name
    try:
        p = subprocess.run([node, "--stack-size=4000", yol],
                           capture_output=True, text=True,
                           encoding="utf-8", timeout=600)
    finally:
        if not os.environ.get("ALQOR_JS_SAXLA"):
            os.unlink(yol)
        else:
            print("JS:", yol, file=sys.stderr)
    if p.returncode != 0 and not p.stdout:
        raise RuntimeError("node xətası:\n" + p.stderr[-4000:])
    nəticə = json.loads(p.stdout)
    for i, m in kompilyasiya_xətaları.items():
        nəticə[i] = {"çıxış": [], "xəta": "KOMPİLYASİYA: " + m}
    return nəticə


def müqayisə(nümunələr: list[dict], node: str) -> list[tuple[int, dict, dict]]:
    fərqlər = []
    for i, (n, j) in enumerate(zip(nümunələr, js_işlət(nümunələr, node))):
        if j["çıxış"] != n["çıxış"] or j["xəta"] != n["xəta"]:
            fərqlər.append((i, n, j))
    return fərqlər


def əsas(arq: list[str]) -> int:
    node = node_tap()
    if "--node" in arq:
        node = arq[arq.index("--node") + 1]
    if node is None:
        print("node tapılmadı", file=sys.stderr)
        return 2
    yol = [a for a in arq if not a.startswith("-") and a != node][0]
    nümunələr = json.load(open(yol, encoding="utf-8"))
    fərqlər = müqayisə(nümunələr, node)
    for i, n, j in fərqlər:
        print(f"── #{i} ──────────────────")
        if "-v" in arq:
            print(n["kod"])
        print("  python:", n["çıxış"][:8], n["xəta"])
        print("  js    :", j["çıxış"][:8], (j["xəta"] or "")[:600])
    print(f"{len(nümunələr) - len(fərqlər)}/{len(nümunələr)} uyğun")
    return 1 if fərqlər else 0


if __name__ == "__main__":
    sys.exit(əsas(sys.argv[1:]))
