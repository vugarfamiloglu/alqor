"""
Alqor Studio — Alqor dili üçün masaüstü inkişaf mühiti.

Arxitektura `pəncərə` modulu ilə eynidir (Tauri modeli): Python
`127.0.0.1`-də HTTP JSON API qaldırır, əl ilə yazılmış HTML/CSS/JS
interfeysi isə Chrome/Edge/Brave `--app=` pəncərəsində (və ya
pywebview-da) açılır. Xarici asılılıq yoxdur, internet lazım deyil.

    python alqorc.py studio [qovluq]

Modullar:
    qurulus.py      mətnin quruluşu: kod/mətn/şərh xəritəsi, komponentlər
    skelet.py       iki klikdə vidjet kodu — Studio-nun əsas xüsusiyyəti
    klaviatura.py   ASCII → Azərbaycan hərfləri (açar söz + `;` tərkibi)
    diaqnostika.py  lekser + parser + tip yoxlayıcı → redaktor xətaları
    layihe.py       layihə qovluğu ilə məhdudlaşdırılmış fayl əməliyyatları
    icra.py         proqramı ayrıca prosesdə işlətmək, çıxış axını
    onbaxis.py      komponentin canlı önbaxışı (ayrıca proses)
    sablonlar.py    "yeni layihə" şablonları
    server.py       HTTP server, API, pəncərənin açılması
"""

from pathlib import Path

VERSIYA = "2.4.0"
QOVLUQ = Path(__file__).resolve().parent
STATİK = QOVLUQ / "statik"
ALQORC = QOVLUQ.parent / "alqorc.py"
