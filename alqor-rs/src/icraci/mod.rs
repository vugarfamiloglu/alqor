//! Ağac gəzən icraçı (icraci.py, deyerler.py, kitabxana.py).

pub mod aktyor;
pub mod cagiris;
pub mod vahid;
pub mod deyerler;
pub mod eded;
pub mod elave;
pub mod format;
#[allow(clippy::module_inception)]
pub mod icraci;
pub mod kitabxana;
pub mod konsol;
pub mod metodlar;
pub mod modullar;
pub mod mod_csv;
#[cfg(all(feature = "http", not(target_arch = "wasm32")))]
pub mod mod_http;
pub mod mod_kodlasdirma;
#[cfg(not(target_arch = "wasm32"))]
pub mod mod_sebeke;
pub mod mod_sifre;
pub mod mod_sixma;
pub mod mod_sablon;
pub mod mod_toml;
#[cfg(not(target_arch = "wasm32"))]
pub mod mod_veb;
pub mod mod_veb_ortaq;
pub mod mod_xml;
#[cfg(all(feature = "sqlite", not(target_arch = "wasm32")))]
pub mod mod_verilenler;
pub mod muhit;
pub mod platforma;
pub mod sinifler;

pub use deyerler::AlqorXəta;
pub use icraci::İcraçı;
