//! Ağac gəzən icraçı (icraci.py, deyerler.py, kitabxana.py).

pub mod cagiris;
pub mod deyerler;
pub mod eded;
pub mod format;
#[allow(clippy::module_inception)]
pub mod icraci;
pub mod kitabxana;
pub mod konsol;
pub mod metodlar;
pub mod modullar;
pub mod muhit;
pub mod platforma;
pub mod sinifler;

pub use deyerler::AlqorXəta;
pub use icraci::İcraçı;
