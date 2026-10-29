#!/bin/bash
# Rebuilds every attack-data file the final engine reads (d4/*.npy): 13 board modes x 3 weak-point pairs
# x 2 aim settings x 3 stances, each with and without one re-roll (suffix _r1). Takes roughly 10-15 minutes.
# Usage: g++ -O2 -o cs5 cs5.cpp && bash regen_all.sh
mkdir -p d4
NB=25000; NR=15000
declare -A M=( [normal]="1 3 3 0 0 0 1 0" [daze]="1 3 1 0 0 0 1 0" [traps]="1 3 3 0 0 2 2 0.5" [dazetraps]="1 3 1 0 0 2 2 0.5"
 [thickhide]="1 3 3 0 1 0 1 0" [plate]="1 3 3 0 2 0 1 0" [jinx]="0 3 3 0 0 0 1 0" [pin]="1 2 3 0 0 0 1 0"
 [shieldwall]="1 3 3 311 0 0 1 0" [ironwall]="1 3 3 68 0 0 1 0" [gate678]="1 3 3 678 0 0 1 0" [cracked]="1 3 3 0 3 0 1 0" )
gen(){ # $1=file stem, $2=N, $3=reroll count, rest = cs5 args after the first 12
  f=$1; n=$2; rr=$3; shift 3
  [ -s $f.npy ] && return
  ./cs5 $n 0 0 layout_plus.txt 1 1000 0 3 1 0 6 9 "$@" $rr && python3 -c "import numpy as np;np.save('$f.npy',np.loadtxt('$f.txt').astype(np.int64))" && rm $f.txt
}
for suf in "" "_r1"; do
 if [ -z "$suf" ]; then N=$NB; RRN=0; else N=$NR; RRN=1; fi
 for m in "${!M[@]}"; do set -- ${M[$m]}; W=$1;R=$2;FM=$3;L=$4;PF=$5;NH=$6;HM=$7;EV=$8
  for p in "w311 0 6" "w410 1 5" "w59 2 6"; do set -- $p; pn=$1;C=$2;WR=$3
   for a in 0 1; do WV=$([ $a = 1 ] && echo 12 || echo 0); WV2=$([ $a = 1 ] && echo 24 || echo 0)
    for g in 0 1 2; do f=d4/${m}_${pn}_a${a}_g${g}${suf}
     gen $f $N $RRN $W $R 4 $FM 1 $L $PF 4 $g 3 $C $WR 2 $WV $NH 8 $f.txt $HM $EV 2 $WV2 1 2 0 2
 done; done; done; done
 # Exposed opening: the weak point sits 2 rows lower (rows 4/3/4 instead of 6/5/6)
 for p in "w311 0 4" "w410 1 3" "w59 2 4"; do set -- $p; pn=$1;C=$2;WR=$3
  for a in 0 1; do WV=$([ $a = 1 ] && echo 12 || echo 0); WV2=$([ $a = 1 ] && echo 24 || echo 0)
   for g in 0 1 2; do f=d4/exposed2_${pn}_a${a}_g${g}${suf}
    gen $f $N $RRN 1 3 4 3 1 0 0 4 $g 3 $C $WR 2 $WV 0 8 $f.txt 1 0 2 $WV2 1 2 0 2
 done; done; done
done
echo "done: $(ls d4/*.npy | wc -l) files (expect 468)"
