#!/bin/sh
# Alqor icraçısını WebAssembly-yə qurur: alqor-rs/wasm/alqor.wasm
#
#   ./wasm/qur.sh          (alqor-rs qovluğundan və ya istənilən yerdən)
#
# Tələb: rustup target add wasm32-unknown-unknown
set -e
KOK="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KOK"
# Dərin rekursiya üçün 32 MB stek (Alqor stek həddi 1000 çağırışdır)
RUSTFLAGS="-C link-arg=-zstack-size=33554432" \
  cargo rustc --lib --crate-type cdylib --target wasm32-unknown-unknown --profile wasm
cp target/wasm32-unknown-unknown/wasm/deps/alqor.wasm wasm/alqor.wasm
echo "wasm/alqor.wasm: $(wc -c < wasm/alqor.wasm) bayt"
