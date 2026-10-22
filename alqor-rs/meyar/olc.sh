#!/bin/sh
# İstifadə: sh meyar/olc.sh   (alqor-rs qovluğundan)
B=./target/release/alqor-rs
for f in meyar/*.alq; do
  for rejim in yox hə; do
    s=$(date +%s%N); ALQOR_VM=$([ $rejim = hə ] && echo 1 || echo 0) $B işlət $f >/dev/null; e=$(date +%s%N)
    printf "%-22s vm=%-3s %6d ms\n" "$f" "$rejim" $(( (e - s) / 1000000 ))
  done
done
