//! `şəbəkə` — aşağı səviyyəli TCP/UDP (modullar/sebeke.py).
//!
//! Fərq: Rust icraçısı tək saplıdır. `TCPServer.başlat()` bağlantıları
//! fon sapında qəbul edir, amma idarəedici (Alqor funksiyası) icraçının
//! öz sapında — proqram şəbəkə əməliyyatında gözləyəndə (`al`,
//! `sətirAl`, `TCPBağlan`, `portAçıqdır`) — işlədilir. `dinlə()` isə
//! bağlantıları ardıcıl idarə edir.

use super::deyerler::*;
use super::elave::*;
use super::icraci::İcraçı;
use std::cell::RefCell;
use std::collections::VecDeque;
use std::io::{Read, Write};
use std::net::{Shutdown, SocketAddr, TcpListener, TcpStream, ToSocketAddrs, UdpSocket};
use std::rc::Rc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

/// Python `OSError.__str__` formasına yaxın: `[Errno 111] Connection refused`
pub fn os_xəta_mətni(e: &std::io::Error) -> String {
    let s = e.to_string();
    match e.raw_os_error() {
        Some(n) => {
            let m = s.split(" (os error").next().unwrap_or(&s).to_string();
            // Python Windows-da `[WinError N] mesaj` yazır (sonda nöqtəsiz)
            if cfg!(windows) {
                format!("[WinError {}] {}", n, m.trim_end().trim_end_matches('.'))
            } else {
                format!("[Errno {}] {}", n, m)
            }
        }
        None => {
            if s.contains("failed to lookup address") || s.contains("Name or service not known") {
                "[Errno -2] Name or service not known".into()
            } else {
                s
            }
        }
    }
}

fn vaxt_bitdi(e: &std::io::Error) -> bool {
    matches!(e.kind(), std::io::ErrorKind::TimedOut | std::io::ErrorKind::WouldBlock)
}

pub fn x_(e: &std::io::Error, nə: &str) -> Siqnal {
    if vaxt_bitdi(e) {
        return xəta("VaxtBitdiXətası", format!("{}: vaxt bitdi", nə), "ALQ-R011");
    }
    xəta("BağlantıXətası", format!("{}: {}", nə, os_xəta_mətni(e)), "ALQ-R010")
}

fn bayt_(x: &D) -> Nəticə<Vec<u8>> {
    match x {
        D::Bayt(b) => Ok(b.to_vec()),
        D::S(s) => Ok(s.as_bytes().to_vec()),
        _ => Err(xəta("TipXətası", format!("mətn və ya bayt gözlənilir, `{}` gəlib", tip_adı(x)), "ALQ-T001")),
    }
}

fn host_(h: &str) -> String {
    if h.is_ascii() {
        h.to_string()
    } else {
        #[cfg(feature = "http")]
        {
            idna::domain_to_ascii(h).unwrap_or_else(|_| h.to_string())
        }
        #[cfg(not(feature = "http"))]
        {
            h.to_string()
        }
    }
}

fn ünvanlar(host: &str, port: u16) -> std::io::Result<Vec<SocketAddr>> {
    (host_(host).as_str(), port).to_socket_addrs().map(|a| a.collect())
}

fn port_(d: &D) -> Nəticə<u16> {
    let p = py_int(d, "port")?;
    if !(0..=65535).contains(&p) {
        return Err(xəta("DəyərXətası", "port must be 0-65535.", "ALQ-R005"));
    }
    Ok(p as u16)
}

fn bağlan(host: &str, port: u16, vaxt: Option<Duration>) -> std::io::Result<TcpStream> {
    let mut son = std::io::Error::new(std::io::ErrorKind::Other, "getaddrinfo returns an empty list");
    for a in ünvanlar(host, port)? {
        let r = match vaxt {
            Some(v) => TcpStream::connect_timeout(&a, v),
            None => TcpStream::connect(a),
        };
        match r {
            Ok(s) => return Ok(s),
            Err(e) => son = e,
        }
    }
    Err(son)
}

// ── Gözləyən server bağlantıları (tək saplı icraçı üçün) ───────────────

struct ServerV {
    dinləyici: RefCell<Option<TcpListener>>,
    işləyici: D,
    xətalar: RefCell<Vec<String>>,
    növbə: Arc<Mutex<VecDeque<TcpStream>>>,
    dur: Arc<AtomicBool>,
    port: u16,
    işləyir: RefCell<bool>,
}

thread_local! {
    static SERVERLƏR: RefCell<Vec<std::rc::Weak<ServerV>>> = RefCell::new(vec![]);
    static POMPADA: RefCell<bool> = RefCell::new(false);
}

impl ServerV {
    fn idarə_et(&self, i: &İcraçı, s: TcpStream) {
        let ad_ = s.peer_addr().map(|a| format!("{}:{}", a.ip(), a.port())).unwrap_or_default();
        let _ = s.set_nonblocking(false);
        let k = soket_obyekti(SoketV { s: Some(s), ad: ad_, bufer: vec![], vaxt: None });
        if let Err(Siqnal::Xəta(x)) = çağır(i, &self.işləyici, vec![k.clone()]) {
            self.xətalar.borrow_mut().push(format!("{}: {}", x.tip, x.mesaj));
        }
        if let Some(v) = veri::<RefCell<SoketV>>(&k) {
            v.borrow_mut().bağla();
        }
    }
}

/// Fon sapında qəbul edilmiş bağlantıların idarəedicilərini işlədir.
pub fn pompa(i: &İcraçı) -> bool {
    if POMPADA.with(|p| *p.borrow()) {
        return false;
    }
    let serverlər: Vec<Rc<ServerV>> = SERVERLƏR.with(|s| s.borrow().iter().filter_map(|w| w.upgrade()).collect());
    let mut nəsə = false;
    POMPADA.with(|p| *p.borrow_mut() = true);
    for sv in serverlər {
        loop {
            let s = sv.növbə.lock().unwrap().pop_front();
            match s {
                Some(s) => {
                    nəsə = true;
                    sv.idarə_et(i, s);
                }
                None => break,
            }
        }
    }
    POMPADA.with(|p| *p.borrow_mut() = false);
    nəsə
}

fn server_var() -> bool {
    SERVERLƏR.with(|s| s.borrow().iter().any(|w| w.upgrade().map(|v| *v.işləyir.borrow()).unwrap_or(false)))
}

// ── Soket ──────────────────────────────────────────────────────────────

pub struct SoketV {
    s: Option<TcpStream>,
    ad: String,
    bufer: Vec<u8>,
    vaxt: Option<Duration>,
}

impl SoketV {
    fn bağla(&mut self) {
        if let Some(s) = self.s.take() {
            let _ = s.shutdown(Shutdown::Both);
        }
    }
    /// Server pompası ilə oxuma: blok gözləmə əvəzinə qısa addımlar
    fn oxu(&mut self, i: &İcraçı, n: usize) -> Nəticə<Vec<u8>> {
        let ad_ = self.ad.clone();
        let vaxt = self.vaxt;
        let Some(s) = self.s.as_mut() else {
            return Err(x_(&std::io::Error::from_raw_os_error(9), &ad_));
        };
        let mut b = vec![0u8; n.max(1)];
        if !server_var() {
            let _ = s.set_read_timeout(vaxt);
            let k = s.read(&mut b).map_err(|e| x_(&e, &ad_))?;
            b.truncate(k);
            return Ok(b);
        }
        let başla = Instant::now();
        loop {
            pompa(i);
            let _ = s.set_read_timeout(Some(Duration::from_millis(20)));
            match s.read(&mut b) {
                Ok(k) => {
                    b.truncate(k);
                    let _ = s.set_read_timeout(vaxt);
                    return Ok(b);
                }
                Err(e) if vaxt_bitdi(&e) => {
                    if let Some(v) = vaxt {
                        if başla.elapsed() >= v {
                            let _ = s.set_read_timeout(vaxt);
                            return Err(x_(&e, &ad_));
                        }
                    }
                }
                Err(e) => return Err(x_(&e, &ad_)),
            }
        }
    }
    fn al(&mut self, i: &İcraçı, n: usize) -> Nəticə<Vec<u8>> {
        if !self.bufer.is_empty() {
            let k = n.min(self.bufer.len());
            return Ok(self.bufer.drain(..k).collect());
        }
        self.oxu(i, n)
    }
    fn sətir_al(&mut self, i: &İcraçı) -> Nəticə {
        let maks = 1 << 20;
        while !self.bufer.contains(&b'\n') {
            if self.bufer.len() > maks {
                return Err(xəta("DəyərXətası", "sətir çox uzundur", "ALQ-R010"));
            }
            let p = self.oxu(i, 4096)?;
            if p.is_empty() {
                if self.bufer.is_empty() {
                    return Ok(D::Boş);
                }
                let s = std::mem::take(&mut self.bufer);
                return Ok(D::str(String::from_utf8_lossy(&s).to_string()));
            }
            self.bufer.extend(p);
        }
        let k = self.bufer.iter().position(|b| *b == b'\n').unwrap();
        let mut s: Vec<u8> = self.bufer.drain(..=k).collect();
        s.pop();
        while s.last() == Some(&b'\r') {
            s.pop();
        }
        Ok(D::str(String::from_utf8_lossy(&s).to_string()))
    }
}

fn n_(a: &[D], k: usize) -> Nəticə<usize> {
    match a.get(k) {
        Some(x) => Ok(py_int(x, "al")?.max(0) as usize),
        None => Ok(65536),
    }
}

fn soket_obyekti(s: SoketV) -> D {
    obyekt("soket", Rc::new(RefCell::new(s)), |s| format!("<soket {}>", s.borrow().ad), |w, v| {
        vec![
            ("göndər", metod(v, "göndər", 1, Some(1), |i, s, a, _| {
                let b = bayt_(&a[0])?;
                {
                    let mut s = s.borrow_mut();
                    let ad_ = s.ad.clone();
                    let Some(t) = s.s.as_mut() else { return Err(x_(&std::io::Error::from_raw_os_error(9), &ad_)) };
                    t.write_all(&b).map_err(|e| x_(&e, &ad_))?;
                }
                let _ = i;
                Ok(D::T(b.len() as i64))
            })),
            ("al", metod(v, "al", 0, Some(1), |i, s, a, _| {
                let n = n_(&a, 0)?;
                Ok(D::Bayt(Rc::new(s.borrow_mut().al(i, n)?)))
            })),
            ("alMətn", metod(v, "alMətn", 0, Some(1), |i, s, a, _| {
                let n = n_(&a, 0)?;
                Ok(D::str(String::from_utf8_lossy(&s.borrow_mut().al(i, n)?).to_string()))
            })),
            ("sətirAl", metod(v, "sətirAl", 0, Some(0), |i, s, _, _| s.borrow_mut().sətir_al(i))),
            ("vaxtLimiti", metod_ö(w, v, "vaxtLimiti", 1, Some(1), |_, s, ö, a, _| {
                let mut s = s.borrow_mut();
                s.vaxt = if a[0].boşdur() {
                    None
                } else {
                    let ms = py_int(&a[0], "vaxtLimiti")?;
                    if ms < 0 {
                        return Err(xəta("DəyərXətası", "Timeout value out of range", "ALQ-R005"));
                    }
                    Some(Duration::from_millis(ms as u64).max(Duration::from_nanos(1)))
                };
                let v = s.vaxt;
                if let Some(t) = s.s.as_ref() {
                    let _ = t.set_read_timeout(v.filter(|d| !d.is_zero()));
                    let _ = t.set_write_timeout(v.filter(|d| !d.is_zero()));
                }
                Ok(ö)
            })),
            ("ünvan", metod(v, "ünvan", 0, Some(0), |_, s, _, _| Ok(D::str(s.borrow().ad.clone())))),
            ("bağla", metod(v, "bağla", 0, Some(0), |_, s, _, _| {
                s.borrow_mut().bağla();
                Ok(D::Boş)
            })),
        ]
    })
}

fn tcp_bağlan(i: &İcraçı, a: &[Option<D>]) -> Nəticə {
    let host = py_s(&al(a, 0));
    let port_d = al(a, 1);
    let nə = format!("{}:{}", host, py_s(&port_d));
    let port = port_(&port_d)?;
    let ms = var(a, 2).map(|x| py_int(&x, "TCPBağlan")).transpose()?.unwrap_or(10000);
    let vaxt = Duration::from_millis(ms.max(1) as u64);
    pompa(i);
    let s = bağlan(&host, port, Some(vaxt)).map_err(|e| x_(&e, &nə))?;
    let _ = s.set_read_timeout(Some(vaxt));
    let _ = s.set_write_timeout(Some(vaxt));
    Ok(soket_obyekti(SoketV { s: Some(s), ad: nə, bufer: vec![], vaxt: Some(vaxt) }))
}

// ── TCPServer ──────────────────────────────────────────────────────────

fn tcp_server(i: &İcraçı, a: &[Option<D>]) -> Nəticə {
    let _ = i;
    let ünvan = var(a, 2).map(|x| py_s(&x)).unwrap_or("127.0.0.1".into());
    let port_d = al(a, 0);
    let port = port_(&port_d)?;
    let nə = format!("{}:{}", ünvan, py_s(&port_d));
    let l = TcpListener::bind((ünvan.as_str(), port)).map_err(|e| x_(&e, &nə))?;
    let port = l.local_addr().map(|a| a.port()).unwrap_or(port);
    let sv = Rc::new(ServerV {
        dinləyici: RefCell::new(Some(l)),
        işləyici: al(a, 1),
        xətalar: RefCell::new(vec![]),
        növbə: Arc::new(Mutex::new(VecDeque::new())),
        dur: Arc::new(AtomicBool::new(false)),
        port,
        işləyir: RefCell::new(false),
    });
    SERVERLƏR.with(|s| s.borrow_mut().push(Rc::downgrade(&sv)));
    Ok(obyekt("tcpServer", sv, |s| format!("<tcpServer {}>", s.port), |w, v| {
        vec![
            ("başlat", metod_ö(w, v, "başlat", 0, Some(0), |_, s, ö, _, _| {
                if *s.işləyir.borrow() {
                    return Ok(ö);
                }
                let l = s.dinləyici.borrow().as_ref().and_then(|l| l.try_clone().ok());
                if let Some(l) = l {
                    *s.işləyir.borrow_mut() = true;
                    let növbə = s.növbə.clone();
                    let dur = s.dur.clone();
                    std::thread::spawn(move || {
                        for b in l.incoming() {
                            if dur.load(Ordering::SeqCst) {
                                break;
                            }
                            if let Ok(b) = b {
                                növbə.lock().unwrap().push_back(b);
                            }
                        }
                    });
                }
                Ok(ö)
            })),
            ("dinlə", metod(v, "dinlə", 0, Some(0), |i, s, _, _| {
                i.boşalt();
                let l = s.dinləyici.borrow().as_ref().and_then(|l| l.try_clone().ok());
                if let Some(l) = l {
                    for b in l.incoming() {
                        if s.dur.load(Ordering::SeqCst) {
                            break;
                        }
                        if let Ok(b) = b {
                            s.idarə_et(i, b);
                        }
                    }
                }
                *s.dinləyici.borrow_mut() = None;
                Ok(D::Boş)
            })),
            ("dayandır", metod(v, "dayandır", 0, Some(0), |i, s, _, _| {
                pompa(i);
                s.dur.store(true, Ordering::SeqCst);
                *s.işləyir.borrow_mut() = false;
                // Bloklanmış `accept`-i oyadırıq
                let _ = TcpStream::connect_timeout(&SocketAddr::from(([127, 0, 0, 1], s.port)), Duration::from_millis(200));
                *s.dinləyici.borrow_mut() = None;
                Ok(D::Boş)
            })),
            ("port", metod(v, "port", 0, Some(0), |_, s, _, _| Ok(D::T(s.port as i64)))),
            ("xətalar", metod(v, "xətalar", 0, Some(0), |i, s, _, _| {
                pompa(i);
                Ok(D::siyahı(s.xətalar.borrow().iter().map(|x| D::str(x.clone())).collect()))
            })),
        ]
    }))
}

// ── UDP ────────────────────────────────────────────────────────────────

fn udp_soket(a: &[Option<D>]) -> Nəticə {
    let port_d = var(a, 0).unwrap_or(D::T(0));
    let ünvan = var(a, 1).map(|x| py_s(&x)).unwrap_or("127.0.0.1".into());
    let port = port_(&port_d)?;
    let s = UdpSocket::bind((ünvan.as_str(), port)).map_err(|e| x_(&e, &format!("udp {}:{}", ünvan, py_s(&port_d))))?;
    let _ = s.set_read_timeout(Some(Duration::from_secs(10)));
    let ad_ = format!("{}:{}", ünvan, port);
    Ok(obyekt("udpSoket", Rc::new(RefCell::new(Some(s))), move |_| format!("<udpSoket {}>", ad_), |w, v| {
        vec![
            ("göndər", metod(v, "göndər", 3, Some(3), |_, s, a, _| {
                let h = py_s(&a[1]);
                let nə = format!("udp {}:{}", h, py_s(&a[2]));
                let b = bayt_(&a[0])?;
                let p = port_(&a[2])?;
                let s = s.borrow();
                let Some(s) = s.as_ref() else { return Err(x_(&std::io::Error::from_raw_os_error(9), &nə)) };
                let hədəf = ünvanlar(&h, p).map_err(|e| x_(&e, &nə))?;
                let hədəf = hədəf.iter().find(|a| a.is_ipv4()).or(hədəf.first()).copied();
                let Some(hədəf) = hədəf else { return Err(xəta("BağlantıXətası", format!("{}: getaddrinfo returns an empty list", nə), "ALQ-R010")) };
                let n = s.send_to(&b, hədəf).map_err(|e| x_(&e, &nə))?;
                Ok(D::T(n as i64))
            })),
            ("al", metod(v, "al", 0, Some(1), |_, s, a, _| {
                let n = n_(&a, 0)?;
                let s = s.borrow();
                let Some(s) = s.as_ref() else { return Err(x_(&std::io::Error::from_raw_os_error(9), "udp")) };
                let mut b = vec![0u8; n.max(1)];
                let (k, ü) = s.recv_from(&mut b).map_err(|e| x_(&e, "udp"))?;
                b.truncate(k);
                Ok(lüğət(vec![
                    ("verilən", D::Bayt(Rc::new(b))),
                    ("ünvan", D::str(ü.ip().to_string())),
                    ("port", D::T(ü.port() as i64)),
                ]))
            })),
            ("port", metod(v, "port", 0, Some(0), |_, s, _, _| {
                Ok(D::T(s.borrow().as_ref().and_then(|s| s.local_addr().ok()).map(|a| a.port() as i64).unwrap_or(0)))
            })),
            ("vaxtLimiti", metod_ö(w, v, "vaxtLimiti", 1, Some(1), |_, s, ö, a, _| {
                let v = if a[0].boşdur() { None } else { Some(Duration::from_millis(py_int(&a[0], "vaxtLimiti")?.max(1) as u64)) };
                if let Some(s) = s.borrow().as_ref() {
                    let _ = s.set_read_timeout(v);
                }
                Ok(ö)
            })),
            ("bağla", metod(v, "bağla", 0, Some(0), |_, s, _, _| {
                *s.borrow_mut() = None;
                Ok(D::Boş)
            })),
        ]
    }))
}

fn yerli_ip() -> String {
    let s = match UdpSocket::bind("0.0.0.0:0") {
        Ok(s) => s,
        Err(_) => return "127.0.0.1".into(),
    };
    if s.connect("10.255.255.255:1").is_err() {
        return "127.0.0.1".into();
    }
    s.local_addr().map(|a| a.ip().to_string()).unwrap_or("127.0.0.1".into())
}

pub fn qur() -> Rc<Modul> {
    Modul::yeni("şəbəkə", vec![
        ("TCPBağlan", f("TCPBağlan", 2, Some(3), |i, a, adlı| {
            let n = imza("TCPBağlan", a, adlı, &["host", "port", "vaxtLimiti"])?;
            tcp_bağlan(i, &n)
        })),
        ("TCPServer", f("TCPServer", 2, Some(3), |i, a, adlı| {
            let n = imza("TCPServer", a, adlı, &["p", "f", "ünvan"])?;
            tcp_server(i, &n)
        })),
        ("UDPSoket", f("UDPSoket", 0, Some(2), |_, a, adlı| {
            let n = imza("UDPSoket", a, adlı, &["port", "ünvan"])?;
            udp_soket(&n)
        })),
        ("ünvanTap", f("ünvanTap", 1, Some(1), |_, a, _| {
            let h = py_s(&a[0]);
            let mut v: Vec<String> = ünvanlar(&h, 0).map_err(|e| x_(&e, &h))?.iter().map(|a| a.ip().to_string()).collect();
            v.sort();
            v.dedup();
            Ok(D::siyahı(v.into_iter().map(D::str).collect()))
        })),
        ("portAçıqdır", f("portAçıqdır", 2, Some(3), |i, a, adlı| {
            let n = imza("portAçıqdır", a, adlı, &["host", "port", "ms"])?;
            let ms = var(&n, 2).map(|x| py_int(&x, "portAçıqdır")).transpose()?.unwrap_or(1000);
            let port = port_(&al(&n, 1))?;
            pompa(i);
            Ok(D::M(bağlan(&py_s(&al(&n, 0)), port, Some(Duration::from_millis(ms.max(1) as u64))).is_ok()))
        })),
        ("yerliIP", f("yerliIP", 0, Some(0), |_, _, _| Ok(D::str(yerli_ip())))),
        ("hostAdı", f("hostAdı", 0, Some(0), |_, _, _| Ok(D::str(super::platforma::host_adı())))),
    ])
}
