"""
`şifrə` — kriptoqrafiya (§ 10.14).

    gətir şifrə

    şifrə.heş("mətn")                         // sha256, hex
    şifrə.heş("mətn", "sha512")
    dəyişən h = şifrə.parolHeş("gizli123")    // "$scrypt$…" — bazada saxlanır
    şifrə.parolYoxla("gizli123", h)           // doğru

    dəyişən açar = şifrə.açarYarat()          // 32 bayt
    dəyişən ş = şifrə.şifrələ("məxfi mətn", açar)      // AES-256-GCM
    yaz(şifrə.şifrəAçMətn(ş, açar))

    dəyişən t = şifrə.tokenYarat({"id": 5}, "gizli", müddət: 3600)   // JWT (HS256)
    dəyişən v = şifrə.tokenOxu(t, "gizli")    // imza və `exp` yoxlanılır

Asılılıqsızdır. Parol heşi: scrypt (Python-un standart kitabxanasında
Argon2 yoxdur; scrypt da yaddaşa davamlı funksiyadır, OWASP-ın tövsiyə
etdiyi alternativdir). AES bu faylda yazılıb və NIST test vektorları
ilə yoxlanılır (`sinaq/test_modullar.py`). Bütün müqayisələr sabit
zamanlıdır (`hmac.compare_digest`).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Any

from ..deyerler import AlqorXəta, Daxili, Nümunə, tip_adı


def _xəta(mesaj: str, tip: str = "ŞifrələməXətası") -> AlqorXəta:
    return AlqorXəta(tip, mesaj, None, "ALQ-R005")


def _bayt(x: Any, ad: str) -> bytes:
    if isinstance(x, bytes):
        return x
    if isinstance(x, str):
        return x.encode("utf-8")
    raise AlqorXəta("TipXətası",
                    f"`{ad}` mətn və ya bayt gözləyir, `{tip_adı(x)}` gəlib",
                    None, "ALQ-T001")


# ═══════════════════════════════════════════════════════════════════════
#  AES (FIPS-197) — yalnız şifrələmə istiqaməti lazımdır (GCM/CTR)
# ═══════════════════════════════════════════════════════════════════════

def _sbox() -> list[int]:
    s = [0] * 256
    p = q = 1
    while True:
        # p — 3-ün qüvvətləri, q — onun tərsi (GF(2^8))
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q = (q ^ (q << 1)) & 0xFF
        q = (q ^ (q << 2)) & 0xFF
        q = (q ^ (q << 4)) & 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q ^ (q << 1 | q >> 7) ^ (q << 2 | q >> 6) ^ \
            (q << 3 | q >> 5) ^ (q << 4 | q >> 4)
        s[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break
    s[0] = 0x63
    return s


_S = _sbox()


def _xtime(a: int) -> int:
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else a << 1


# T-cədvəlləri: SubBytes + ShiftRows + MixColumns bir addımda
_T0 = []
for _a in _S:
    _b = _xtime(_a)
    _T0.append((_b << 24) | (_a << 16) | (_a << 8) | (_a ^ _b))
_T1 = [((t >> 8) | (t << 24)) & 0xFFFFFFFF for t in _T0]
_T2 = [((t >> 16) | (t << 16)) & 0xFFFFFFFF for t in _T0]
_T3 = [((t >> 24) | (t << 8)) & 0xFFFFFFFF for t in _T0]


class _AES:
    def __init__(self, açar: bytes):
        if len(açar) not in (16, 24, 32):
            raise _xəta("AES açarı 16, 24 və ya 32 bayt olmalıdır "
                        f"({len(açar)} bayt verilib)")
        nk = len(açar) // 4
        self.nr = nk + 6
        w = [int.from_bytes(açar[4 * i:4 * i + 4], "big") for i in range(nk)]
        rcon = 1
        for i in range(nk, 4 * (self.nr + 1)):
            t = w[i - 1]
            if i % nk == 0:
                t = ((t << 8) | (t >> 24)) & 0xFFFFFFFF
                t = (_S[t >> 24] << 24 | _S[(t >> 16) & 0xFF] << 16 |
                     _S[(t >> 8) & 0xFF] << 8 | _S[t & 0xFF])
                t ^= rcon << 24
                rcon = _xtime(rcon)
            elif nk > 6 and i % nk == 4:
                t = (_S[t >> 24] << 24 | _S[(t >> 16) & 0xFF] << 16 |
                     _S[(t >> 8) & 0xFF] << 8 | _S[t & 0xFF])
            w.append(w[i - nk] ^ t)
        self.w = w

    def blok(self, b: bytes) -> bytes:
        w = self.w
        s0, s1, s2, s3 = (int.from_bytes(b[i:i + 4], "big") ^ w[i // 4]
                          for i in range(0, 16, 4))
        k = 4
        for _ in range(self.nr - 1):
            t0 = (_T0[s0 >> 24] ^ _T1[(s1 >> 16) & 0xFF] ^
                  _T2[(s2 >> 8) & 0xFF] ^ _T3[s3 & 0xFF] ^ w[k])
            t1 = (_T0[s1 >> 24] ^ _T1[(s2 >> 16) & 0xFF] ^
                  _T2[(s3 >> 8) & 0xFF] ^ _T3[s0 & 0xFF] ^ w[k + 1])
            t2 = (_T0[s2 >> 24] ^ _T1[(s3 >> 16) & 0xFF] ^
                  _T2[(s0 >> 8) & 0xFF] ^ _T3[s1 & 0xFF] ^ w[k + 2])
            t3 = (_T0[s3 >> 24] ^ _T1[(s0 >> 16) & 0xFF] ^
                  _T2[(s1 >> 8) & 0xFF] ^ _T3[s2 & 0xFF] ^ w[k + 3])
            s0, s1, s2, s3 = t0, t1, t2, t3
            k += 4

        def son(a, b_, c, d, kw):
            return ((_S[a >> 24] << 24 | _S[(b_ >> 16) & 0xFF] << 16 |
                     _S[(c >> 8) & 0xFF] << 8 | _S[d & 0xFF]) ^ kw)
        r = (son(s0, s1, s2, s3, w[k]), son(s1, s2, s3, s0, w[k + 1]),
             son(s2, s3, s0, s1, w[k + 2]), son(s3, s0, s1, s2, w[k + 3]))
        return b"".join(x.to_bytes(4, "big") for x in r)


# ── GCM (NIST SP 800-38D) ─────────────────────────────────────────────

_R = 0xE1 << 120


def _gf_vur(x: int, y: int) -> int:
    z = 0
    v = y
    for i in range(127, -1, -1):
        if (x >> i) & 1:
            z ^= v
        v = (v >> 1) ^ _R if v & 1 else v >> 1
    return z


class _GHASH:
    """H-ə vurma — 4 bitlik cədvəllə (sadə bitbəbit vurmadan ~30x tez)."""

    def __init__(self, h: int):
        # M[i][n] = n * x^(4i) * H  — sağdan sola nibble mövqeləri
        self.c = []
        for i in range(32):
            sətir = [0] * 16
            for n in range(16):
                sətir[n] = _gf_vur(n << (4 * i), h) if n else 0
            self.c.append(sətir)

    def vur(self, x: int) -> int:
        z = 0
        c = self.c
        for i in range(32):
            z ^= c[i][(x >> (4 * i)) & 0xF]
        return z


def _ghash(g: _GHASH, a: bytes, c: bytes) -> int:
    y = 0
    for verilən in (a, c):
        for i in range(0, len(verilən), 16):
            blok = verilən[i:i + 16].ljust(16, b"\0")
            y = g.vur(y ^ int.from_bytes(blok, "big"))
    uzunluqlar = ((len(a) * 8) << 64) | (len(c) * 8)
    return g.vur(y ^ uzunluqlar)


def _ctr(aes: _AES, j: int, verilən: bytes) -> bytes:
    n = bytearray()
    sayğac = j
    for i in range(0, len(verilən), 16):
        sayğac = (sayğac & ~0xFFFFFFFF) | ((sayğac + 1) & 0xFFFFFFFF)
        axın = aes.blok(sayğac.to_bytes(16, "big"))
        hissə = verilən[i:i + 16]
        n.extend(a ^ b for a, b in zip(hissə, axın))
    return bytes(n)


def gcm_şifrələ(açar: bytes, nonce: bytes, açıq: bytes,
                əlavə: bytes = b"") -> tuple[bytes, bytes]:
    aes = _AES(açar)
    h = int.from_bytes(aes.blok(b"\0" * 16), "big")
    g = _GHASH(h)
    if len(nonce) == 12:
        j0 = int.from_bytes(nonce + b"\0\0\0\1", "big")
    else:
        j0 = _ghash(g, b"", nonce)
    şifrəli = _ctr(aes, j0, açıq)
    s = _ghash(g, əlavə, şifrəli)
    etiket = bytes(a ^ b for a, b in zip(
        aes.blok(j0.to_bytes(16, "big")), s.to_bytes(16, "big")))
    return şifrəli, etiket


def gcm_aç(açar: bytes, nonce: bytes, şifrəli: bytes, etiket: bytes,
           əlavə: bytes = b"") -> bytes:
    aes = _AES(açar)
    h = int.from_bytes(aes.blok(b"\0" * 16), "big")
    g = _GHASH(h)
    if len(nonce) == 12:
        j0 = int.from_bytes(nonce + b"\0\0\0\1", "big")
    else:
        j0 = _ghash(g, b"", nonce)
    s = _ghash(g, əlavə, şifrəli)
    gözlənilən = bytes(a ^ b for a, b in zip(
        aes.blok(j0.to_bytes(16, "big")), s.to_bytes(16, "big")))
    if not hmac.compare_digest(gözlənilən, etiket[:16]):
        raise _xəta("şifrəli məlumat dəyişdirilib və ya açar yanlışdır")
    return _ctr(aes, j0, şifrəli)


# ═══════════════════════════════════════════════════════════════════════
#  Alqor funksiyaları
# ═══════════════════════════════════════════════════════════════════════

ALQORİTMLƏR = ("md5", "sha1", "sha224", "sha256", "sha384", "sha512",
               "sha3_256", "sha3_512", "blake2b", "blake2s")
VERSİYA = b"\x01"                 # şifrəli məlumatın formatı: 1|nonce|ş|etiket


def heş(x: Any, alqoritm: str = "sha256") -> str:
    alqoritm = str(alqoritm).lower().replace("-", "")
    alqoritm = {"sha3256": "sha3_256", "sha3512": "sha3_512"}.get(
        alqoritm, alqoritm)
    if alqoritm not in ALQORİTMLƏR:
        raise AlqorXəta("DəyərXətası", f"`{alqoritm}` tanınmır — "
                        f"{', '.join(ALQORİTMLƏR)}", None, "ALQ-T001")
    return hashlib.new(alqoritm, _bayt(x, "heş")).hexdigest()


def hmac_(mesaj: Any, açar: Any, alqoritm: str = "sha256") -> str:
    return hmac.new(_bayt(açar, "HMAC"), _bayt(mesaj, "HMAC"),
                    str(alqoritm).lower()).hexdigest()


# scrypt parametrləri: N=2^15, r=8, p=1 — ~32 MB, ~0.1 s (OWASP minimumu)
_N, _RR, _P = 1 << 15, 8, 1


def parol_heş(parol: Any) -> str:
    duz = secrets.token_bytes(16)
    h = hashlib.scrypt(_bayt(parol, "parolHeş"), salt=duz, n=_N, r=_RR,
                       p=_P, maxmem=128 * 1024 * 1024, dklen=32)
    b = lambda x: base64.b64encode(x).decode().rstrip("=")   # noqa: E731
    return f"$scrypt$ln={_N.bit_length() - 1},r={_RR},p={_P}${b(duz)}${b(h)}"


def parol_yoxla(parol: Any, saxlanmış: str) -> bool:
    try:
        _, ad, param, duz64, h64 = str(saxlanmış).split("$")
        if ad != "scrypt":
            return False
        p = dict(x.split("=") for x in param.split(","))
        ln, r, pp = int(p["ln"]), int(p["r"]), int(p["p"])
        if not (1 <= ln <= 22 and 1 <= r <= 32 and 1 <= pp <= 16):
            return False
        aç = lambda s: base64.b64decode(s + "=" * (-len(s) % 4))  # noqa
        duz, h = aç(duz64), aç(h64)
    except (ValueError, KeyError):
        return False
    yeni = hashlib.scrypt(_bayt(parol, "parolYoxla"), salt=duz, n=1 << ln,
                          r=r, p=pp, maxmem=256 * 1024 * 1024, dklen=len(h))
    return hmac.compare_digest(yeni, h)


def parol_açarı(parol: Any, duz: Any) -> bytes:
    """Paroldan 32 baytlıq AES açarı (scrypt). `duz` təsadüfi və
    açıq saxlanan dəyərdir — hər istifadəçi/fayl üçün fərqli."""
    return hashlib.scrypt(_bayt(parol, "parolAçarı"),
                          salt=_bayt(duz, "parolAçarı"), n=_N, r=_RR, p=_P,
                          maxmem=128 * 1024 * 1024, dklen=32)


def _açar(a: Any) -> bytes:
    if isinstance(a, bytes):
        if len(a) != 32:
            raise _xəta(f"açar 32 bayt olmalıdır ({len(a)} bayt verilib) — "
                        "`şifrə.açarYarat()` işlədin")
        return a
    if isinstance(a, str):
        raise _xəta("açar mətn ola bilməz — `şifrə.açarYarat()` və ya "
                    "paroldan: `şifrə.parolAçarı(parol, duz)`")
    raise AlqorXəta("TipXətası", f"açar bayt olmalıdır, `{tip_adı(a)}` "
                    "gəlib", None, "ALQ-T001")


def şifrələ(verilən: Any, açar: Any, əlavə: Any = b"") -> bytes:
    nonce = secrets.token_bytes(12)
    ş, etiket = gcm_şifrələ(_açar(açar), nonce, _bayt(verilən, "şifrələ"),
                            _bayt(əlavə, "şifrələ"))
    return VERSİYA + nonce + ş + etiket


def şifrə_aç(verilən: Any, açar: Any, əlavə: Any = b"") -> bytes:
    b = _bayt(verilən, "şifrəAç") if not isinstance(verilən, str) else \
        _b64(verilən)
    if len(b) < 29 or b[:1] != VERSİYA:
        raise _xəta("bu, `şifrə.şifrələ` ilə şifrələnmiş məlumat deyil")
    return gcm_aç(_açar(açar), b[1:13], b[13:-16], b[-16:],
                  _bayt(əlavə, "şifrəAç"))


def _b64(m: str) -> bytes:
    try:
        return base64.b64decode(m + "=" * (-len(m) % 4))
    except ValueError:
        raise _xəta("şifrəli mətn base64 deyil")


# ── JWT (HS256 / HS384 / HS512) ───────────────────────────────────────

def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64url_aç(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _json(x: Any) -> Any:
    if isinstance(x, Nümunə):
        return {a: _json(d) for a, d in x.sahələr.items()}
    if isinstance(x, dict):
        return {str(a): _json(d) for a, d in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json(d) for d in x]
    return x


def jwt_yarat(verilənlər: Any, açar: Any, müddət: int | None = None,
              alqoritm: str = "HS256") -> str:
    if alqoritm not in ("HS256", "HS384", "HS512"):
        raise AlqorXəta("DəyərXətası", "alqoritm HS256, HS384 və ya HS512 "
                        "olmalıdır", None, "ALQ-T001")
    yük = _json(verilənlər)
    if not isinstance(yük, dict):
        raise AlqorXəta("TipXətası", "JWT verilənləri lüğət olmalıdır",
                        None, "ALQ-T001")
    if müddət is not None:
        yük = {**yük, "iat": int(time.time()),
               "exp": int(time.time()) + int(müddət)}
    baş = _b64url(json.dumps({"alg": alqoritm, "typ": "JWT"},
                             separators=(",", ":")).encode())
    gövdə = _b64url(json.dumps(yük, separators=(",", ":"),
                               ensure_ascii=False).encode())
    imza = hmac.new(_bayt(açar, "JWTYarat"), f"{baş}.{gövdə}".encode(),
                    "sha" + alqoritm[2:]).digest()
    return f"{baş}.{gövdə}.{_b64url(imza)}"


def jwt_oxu(token: str, açar: Any, sürüşmə: int = 0) -> dict:
    try:
        baş, gövdə, imza = str(token).split(".")
        başlıq = json.loads(_b64url_aç(baş))
        alq = başlıq.get("alg")
    except (ValueError, UnicodeDecodeError):
        raise _xəta("JWT formatı pozulub", "JWTXətası")
    # `alg: none` və asimmetrik alqoritmlər qəbul edilmir
    if alq not in ("HS256", "HS384", "HS512"):
        raise _xəta(f"JWT alqoritmi qəbul edilmir: {alq!r}", "JWTXətası")
    gözlənilən = hmac.new(_bayt(açar, "JWTOxu"), f"{baş}.{gövdə}".encode(),
                          "sha" + alq[2:]).digest()
    try:
        verilən_imza = _b64url_aç(imza)
    except ValueError:
        raise _xəta("JWT imzası pozulub", "JWTXətası")
    if not hmac.compare_digest(gözlənilən, verilən_imza):
        raise _xəta("JWT imzası yanlışdır", "JWTXətası")
    try:
        yük = json.loads(_b64url_aç(gövdə))
    except (ValueError, UnicodeDecodeError):
        raise _xəta("JWT verilənləri pozulub", "JWTXətası")
    indi = time.time()
    if isinstance(yük.get("exp"), (int, float)) and \
            indi > yük["exp"] + sürüşmə:
        raise _xəta("JWT-nin müddəti bitib", "JWTXətası")
    if isinstance(yük.get("nbf"), (int, float)) and \
            indi + sürüşmə < yük["nbf"]:
        raise _xəta("JWT hələ qüvvədə deyil", "JWTXətası")
    return yük


def qur(icraçı) -> dict[str, Any]:
    def D(ad, f, mn=0, mx=None):
        return Daxili(ad, f, mn, mx)

    def mətnə(b: bytes) -> str:
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            raise _xəta("açılan məlumat UTF-8 mətn deyil — `şifrəAç` "
                        "işlədin")

    return {
        "heş": D("heş", heş, 1, 2),
        "HMAC": D("HMAC", hmac_, 2, 3),
        "parolHeş": D("parolHeş", parol_heş, 1, 1),
        "parolYoxla": D("parolYoxla", parol_yoxla, 2, 2),
        "parolAçarı": D("parolAçarı", parol_açarı, 2, 2),
        "açarYarat": D("açarYarat", lambda: secrets.token_bytes(32)),
        "şifrələ": D("şifrələ", şifrələ, 2, 3),
        "şifrəAç": D("şifrəAç", şifrə_aç, 2, 3),
        "şifrəAçMətn": D("şifrəAçMətn",
                         lambda v, a, e=b"": mətnə(şifrə_aç(v, a, e)), 2, 3),
        "təsadüfiBayt": D("təsadüfiBayt",
                          lambda n=32: secrets.token_bytes(n), 0, 1),
        "təsadüfiMətn": D("təsadüfiMətn",
                          lambda n=32: secrets.token_urlsafe(n)[:n], 0, 1),
        "UUID": D("UUID", lambda: str(uuid.uuid4())),
        "bərabərdir": D("bərabərdir", lambda a, b: hmac.compare_digest(
            _bayt(a, "bərabərdir"), _bayt(b, "bərabərdir")), 2, 2),
        "tokenYarat": D("tokenYarat", jwt_yarat, 2, 2),
        "tokenOxu": D("tokenOxu", jwt_oxu, 2, 2),
        "alqoritmlər": list(ALQORİTMLƏR),
    }


def tiplər() -> dict:
    from .. import tipler as T
    from ..tipyoxlayici import F, Fsərbəst
    m, e, b, i, mt = T.MƏTN, T.İSTƏNİLƏN, T.BAYT, T.TAM, T.MƏNTİQ
    return {
        "heş": F(e, m, qaytarır=m, standart=1),
        "HMAC": F(e, e, m, qaytarır=m, standart=1),
        "parolHeş": F(e, qaytarır=m), "parolYoxla": F(e, m, qaytarır=mt),
        "parolAçarı": F(e, e, qaytarır=b), "açarYarat": F(qaytarır=b),
        "şifrələ": F(e, b, e, qaytarır=b, standart=1),
        "şifrəAç": F(e, b, e, qaytarır=b, standart=1),
        "şifrəAçMətn": F(e, b, e, qaytarır=m, standart=1),
        "təsadüfiBayt": F(i, qaytarır=b, standart=1),
        "təsadüfiMətn": F(i, qaytarır=m, standart=1),
        "UUID": F(qaytarır=m), "bərabərdir": F(e, e, qaytarır=mt),
        "tokenYarat": Fsərbəst(m), "tokenOxu": Fsərbəst(T.Lüğət(m, e)),
        "alqoritmlər": T.Siyahı(m),
    }
