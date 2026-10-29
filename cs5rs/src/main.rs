//! One Sheet Wonder attack-board simulator: a Rust port of cs5.cpp.
//!
//! Plays one attack on the 9-column board many times with the greedy bot and dumps one line per attack (the "CONT 6"
//! mode the engine's d4/ data is built from). Output is byte-identical to the C++ built with GCC/libstdc++: the
//! Mersenne Twister, the dice method (libstdc++'s 128-bit "nearly divisionless" uniform_int_distribution) and the
//! decimal method (generate_canonical) are written out explicitly, so the data is identical on every platform.
//! (A C++ build with clang/libc++, the macOS default, draws dice differently and does not reproduce the data.)
//!
//! Arguments are positional and identical to cs5.cpp, including the keyword extensions:
//!   argv[39] Lock column mask, argv[40] Grapple column mask, argv[41..49] custom damage per column.

use std::collections::HashMap;
use std::hash::{BuildHasherDefault, Hasher};
use std::io::{BufWriter, Write};

const NC: usize = 9;
const HMAX: usize = 13;              // tallest grid: 13 rows (levels 5-6)

// ---------------------------------------------------------------------------------------------------------------
// Random numbers, matching libstdc++ exactly

/// std::mt19937_64
struct Mt64 { mt: [u64; 312], i: usize }
impl Mt64 {
    fn new(seed: u64) -> Self {
        let mut mt = [0u64; 312];
        mt[0] = seed;
        for i in 1..312 { mt[i] = 6364136223846793005u64.wrapping_mul(mt[i - 1] ^ (mt[i - 1] >> 62)).wrapping_add(i as u64); }
        Mt64 { mt, i: 312 }
    }
    fn next(&mut self) -> u64 {
        const UM: u64 = 0xFFFF_FFFF_8000_0000; const LM: u64 = 0x7FFF_FFFF; const A: u64 = 0xB502_6F5A_A966_19E9;
        if self.i >= 312 {
            for k in 0..312 {
                let x = (self.mt[k] & UM) | (self.mt[(k + 1) % 312] & LM);
                let mut xa = x >> 1;
                if x & 1 != 0 { xa ^= A; }
                self.mt[k] = self.mt[(k + 156) % 312] ^ xa;
            }
            self.i = 0;
        }
        let mut x = self.mt[self.i]; self.i += 1;
        x ^= (x >> 29) & 0x5555_5555_5555_5555;
        x ^= (x << 17) & 0x71D6_7FFF_EDA6_0000;
        x ^= (x << 37) & 0xFFF7_EEE0_0000_0000;
        x ^ (x >> 43)
    }
    /// uniform_int_distribution<int>(1,6): libstdc++ _S_nd<unsigned __int128> (Lemire's method)
    fn d6(&mut self) -> i32 {
        let range: u64 = 6;
        let mut product = (self.next() as u128) * (range as u128);
        let mut low = product as u64;
        if low < range {
            let threshold = range.wrapping_neg() % range;
            while low < threshold { product = (self.next() as u128) * (range as u128); low = product as u64; }
        }
        (product >> 64) as i32 + 1
    }
    /// uniform_real_distribution<double>(0,1): libstdc++ generate_canonical<double, 53> with a 64-bit engine
    fn uniform01(&mut self) -> f64 {
        let r = (self.next() as f64) / 18446744073709551616.0;
        if r >= 1.0 { f64::from_bits(1.0f64.to_bits() - 1) } else { r }
    }
}

// Small, fast hasher for the u32 state keys (the cache is hot).
#[derive(Default)]
struct Fx(u64);
impl Hasher for Fx {
    fn finish(&self) -> u64 { self.0 }
    fn write(&mut self, bytes: &[u8]) { for &b in bytes { self.0 = (self.0.rotate_left(5) ^ b as u64).wrapping_mul(0x517c_c1b7_2722_0a95); } }
    fn write_u32(&mut self, i: u32) { self.0 = (self.0.rotate_left(5) ^ i as u64).wrapping_mul(0x517c_c1b7_2722_0a95); }
}

// ---------------------------------------------------------------------------------------------------------------
// Board state and settings

#[derive(Clone, Copy)]
struct St { h: [i8; NC], run: u16, placed: i8, reff: i8, beast: i8, pounced: i8 }

#[derive(Clone, Copy)]
struct Opt { s: St, g: f64 }

#[derive(Default, Clone)]
struct RunRes {
    h: [i32; NC], guard: i32, weak: i32, hzhit: i32, evaded: i32, trapped: i32, topcol: i32, rrused: i32,
    mask: i64, rolls: i32, dmg: i32, bonus: [i32; 7], maxbonus: i32, busts: i32, throws: i32, fumble: i32, danger: i32,
    stopped: i32, ucount: i32, runners: i32, reserve: i32, keep: i32, keepc: i32, ts: i32,
}

struct Sim {
    // settings (names follow cs5.cpp)
    h_max: i32, maxm: [i32; NC], dmg: [i32; NC], guard: i32, gw: f64, wkt: i32, wkc: usize, wkr: i32, wmult: f64, wval: f64,
    nhz: i32, hv: f64, hzmode: i32, free: i32, fat: i32, fatmode: i32, fattrig: i32, combo: f64, bval: [f64; 7],
    sumcol: [i32; 13], r: i32, maxrun: i32, bonus: [[i32; HMAX + 1]; NC], commonwild: bool, policy: i32, strikes: i32,
    rollcap: i32, safe: i32, lockm: u32, grapm: u32, rr_max: i32, wmult2: f64, wval2: f64, evade: f64, wcol: i32,
    wcolm: f64, wflat: i32, wsteps: i32,
    // class mechanics (named options)
    sqadd: [[i32; HMAX + 1]; NC], stop: bool, stop_bonus: f64, counter: f64, pfumble: f64, charge: i32,
    bloodlust: bool, unstop: bool, pack: bool, ext: bool, stop_guardx: f64, pack_wild: bool, reserve: i32, col_extra: [f64; NC], stop_val: f64, stop_keep: f64, head: i32, head_c: i32, head_col: i32, timestop: i32, ts_used: bool, ts_left: i32, ts_bank: i32, ts_plus: i32, ts_ending: bool, charge_extra: bool, pack_plus: bool, pack_free: bool, pack_with: bool, pack_norm: bool, pack12: bool, pack_once: bool, pack_cap: bool, pack_max: i32, lance2: i32, lance_c: i32,
    // per-run scratch
    hz: [[i32; HMAX + 1]; 9], freed: [bool; NC], wdone: [bool; NC], max_done: [bool; NC], inith: [i32; NC],
    cache: HashMap<u32, (f32, f32), BuildHasherDefault<Fx>>,
    rng: Mt64,
}

impl Sim {
    fn new() -> Self {
        let mut sumcol = [0i32; 13];
        for s in 3..=11 { sumcol[s] = s as i32 - 3; }
        sumcol[2] = -1; sumcol[12] = -1;
        Sim {
            h_max: 12, maxm: [4, 6, 8, 10, 12, 10, 8, 6, 4], dmg: [3, 2, 2, 1, 1, 1, 2, 2, 3], guard: 0, gw: 0.0, wkt: 0, wkc: 0,
            wkr: 0, wmult: 2.0, wval: 0.0, nhz: 0, hv: 0.0, hzmode: 1, free: 0, fat: 0, fatmode: 0, fattrig: 0, combo: 0.0,
            bval: [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0], sumcol, r: 3, maxrun: 1, bonus: [[0; HMAX + 1]; NC], commonwild: false,
            policy: 0, strikes: 1, rollcap: 1000, safe: 0, lockm: 0, grapm: 0, rr_max: 0, wmult2: 3.0, wval2: 0.0, evade: 0.0,
            wcol: 0, wcolm: 2.0, wflat: 0, wsteps: 0, hz: [[0; HMAX + 1]; 9], freed: [false; NC], wdone: [false; NC],
            max_done: [false; NC], inith: [0; NC], cache: HashMap::default(), rng: Mt64::new(5),
            sqadd: [[0; HMAX + 1]; NC], stop: false, stop_bonus: 0.0, counter: 3.0, pfumble: 0.0, charge: 0,
            bloodlust: false, unstop: false, pack: false, ext: false, stop_guardx: 0.0, pack_wild: true, reserve: 0, col_extra: [0.0; NC], stop_val: 0.0, stop_keep: 0.0, head: 0, head_c: -1, head_col: -1, timestop: 0, ts_used: false, ts_left: 0, ts_bank: 0, ts_plus: 0, ts_ending: false, charge_extra: false, pack_plus: false, pack_free: true, pack_with: false, pack_norm: false, pack12: false, pack_once: false, pack_cap: false, pack_max: 0, lance2: 0, lance_c: -1,
        }
    }

    #[inline] fn legal(&self, s: &St, c: usize) -> bool {
        (self.lockm >> c) & 1 == 0 && (s.h[c] as i32) < self.h_max && (((s.run >> c) & 1) != 0 || s.placed < s.reff) && s.beast != c as i8
    }
    #[inline] fn beast_ok(&self, s: &St, c: usize) -> bool {
        self.pack && (self.lockm >> c) & 1 == 0 && (s.h[c] as i32) < self.h_max && (!self.pack_cap || (s.h[c] as i32) < self.fat - 1)   // below the danger line
            && (s.beast == c as i8 || (s.beast < 0 && (s.run >> c) & 1 == 0))
    }
    #[inline] fn app_beast(s: &mut St, c: usize) { s.beast = c as i8; s.h[c] += 1; }
    /// Damage one column deals: squares x column damage, +1 squares, per-square extras; the beast's column counts twice.
    fn new_dmg(&self, s: &St, c: usize) -> i32 {
        let v = self.col_dmg(s, c);
        if self.head_c == c as i32 { let mut t = *s; t.h[c] = (self.head.min(s.h[c] as i32)) as i8; v - self.col_dmg(&t, c) } else { v }
    }
    fn col_dmg(&self, s: &St, c: usize) -> i32 {
        let mut v = s.h[c] as i32 * self.dmg[c];
        for r in 1..=s.h[c] as usize { if self.bonus[c][r] == 5 { v += 1; } v += self.sqadd[c][r]; }
        if self.lance_c == c as i32 { if self.lance2 == 2 { v += s.h[c] as i32; } else { v *= 2; } }   // Trample: lance squares double, or +1
        if s.beast == c as i8 && !self.pack_norm { if self.pack_plus { v += s.h[c] as i32; } else { v *= 2; } }   // beast: double, +1, or normal
        v
    }
    #[inline] fn app(s: &mut St, c: usize) { if (s.run >> c) & 1 == 0 { s.run |= 1 << c; s.placed += 1; } s.h[c] += 1; }
    #[inline] fn grappled(&self, c: usize) -> bool { (self.grapm >> c) & 1 != 0 }

    fn guard_of(&self, h: &[i8; NC]) -> i32 {
        match self.guard {
            4 => { let mut g = 0; for c in 3..=5 { for r in 1..=h[c] as usize { if self.bonus[c][r] != 5 { g += 1; } } } g }
            1 => h[4] as i32,
            2 => (h[3] as i32 + h[4] as i32 + h[5] as i32) / 2,
            3 => h[3] as i32 + h[4] as i32 + h[5] as i32,
            _ => 0,
        }
    }
    fn weak_of(&self, h: &[i8; NC]) -> i32 {
        let (c, r) = (self.wkc, self.wkr);
        match self.wkt {
            1 => (h[c] as i32 >= r) as i32,
            2 => (h[c] as i32 >= r && h[8 - c] as i32 >= r) as i32,
            3 => if c == 4 { (h[4] as i32 >= r) as i32 } else { (h[c] as i32 >= r) as i32 + (h[8 - c] as i32 >= r) as i32 },
            _ => 0,
        }
    }
    #[inline] fn w(&self, c: usize) -> f64 {
        let mut w = if self.policy == 0 { self.dmg[c] as f64 + self.combo + self.col_extra[c] } else { 1.0 };
        if self.guard == 1 && c == 4 { w += self.gw; }
        if self.guard == 2 && (3..=5).contains(&c) { w += self.gw / 2.0; }
        if (self.guard == 3 || self.guard == 4) && (3..=5).contains(&c) { w += self.gw; }
        w
    }

    fn rec(&self, s: &St, tk: &[(i32, i32); 2], i: usize, adv: i32, g: f64, out: &mut Vec<Opt>, advs: &mut Vec<i32>) {
        if i == 2 { out.push(Opt { s: *s, g }); advs.push(adv); return; }
        let (c, mult) = tk[i];
        if c == -2 { self.rec(s, tk, i + 1, adv, g, out, advs); return; }
        let cap = if self.pack_once { 1 } else { self.pack_max };
        let pounce = (!self.pack12 || c == -3) && !(cap > 0 && s.pounced as i32 >= cap);
        if c < 0 {
            let mut any = false;
            for x in 0..NC {
                if self.grappled(x) { continue; }
                if self.legal(s, x) {
                    any = true; let mut n = *s; Sim::app(&mut n, x); let (mut a, mut gg) = (1, self.w(x));
                    if mult == 2 && self.legal(&n, x) { Sim::app(&mut n, x); a += 1; gg += self.w(x); }
                    if self.pack_with && pounce { self.beast_along(&n, tk, i, adv + a, g + gg, out, advs); }
                    else { self.rec(&n, tk, i + 1, adv + a, g + gg, out, advs); }
                }
                if self.pack_wild && self.beast_ok(s, x) {        // a wild can move the beast instead
                    any = true; let mut n = *s; Sim::app_beast(&mut n, x); let bw = self.w(x) + if self.pack_plus { 1.0 } else { self.dmg[x] as f64 }; let (mut a, mut gg) = (1, bw);
                    if mult == 2 && self.beast_ok(&n, x) { Sim::app_beast(&mut n, x); a += 1; gg += bw; }
                    self.rec(&n, tk, i + 1, adv + a, g + gg, out, advs);
                }
            }
            if !any {
                if self.pack_with && pounce { self.beast_along(s, tk, i, adv, g, out, advs); } else { self.rec(s, tk, i + 1, adv, g, out, advs); }
            }
        } else if self.legal(s, c as usize) {
            let cu = c as usize; let mut n = *s; Sim::app(&mut n, cu); let (mut a, mut gg) = (1, self.w(cu));
            if mult == 2 && self.legal(&n, cu) { Sim::app(&mut n, cu); a += 1; gg += self.w(cu); }
            self.rec(&n, tk, i + 1, adv + a, g + gg, out, advs);
        } else { self.rec(s, tk, i + 1, adv, g, out, advs); }
    }

    /// Pack (with the wild): after a wild's normal move, the beast climbs one square (in its column, or starts in a free one).
    fn beast_along(&self, s: &St, tk: &[(i32, i32); 2], i: usize, adv: i32, g: f64, out: &mut Vec<Opt>, advs: &mut Vec<i32>) {
        let mut moved = false;
        for x in 0..NC {
            if self.beast_ok(s, x) && !self.grappled(x) {
                moved = true; let mut n = *s; Sim::app_beast(&mut n, x); n.pounced += 1;
                let bw = self.w(x) + if self.pack_norm { 0.0 } else if self.pack_plus { 1.0 } else { self.dmg[x] as f64 };
                self.rec(&n, tk, i + 1, adv + 1, g + bw, out, advs);
            }
        }
        if !moved { self.rec(s, tk, i + 1, adv, g, out, advs); }
    }

    fn gen(&self, s: &St, d: &[i32; 4], out: &mut Vec<Opt>) {
        out.clear();
        let mut advs: Vec<i32> = Vec::with_capacity(32);
        const P: [[usize; 4]; 3] = [[0, 1, 2, 3], [0, 2, 1, 3], [0, 3, 1, 2]];
        for p in P.iter() {
            let pair = |a: usize, b: usize| (self.sumcol[(d[a] + d[b]) as usize], if self.bloodlust && d[a] == d[b] { 2 } else { 1 });
            let mut tk = [pair(p[0], p[1]), pair(p[2], p[3])];
            if tk[1] < tk[0] { tk.swap(0, 1); }
            self.rec(s, &tk, 0, 0, 0.0, out, &mut advs);           // do { ... } while (next_permutation)
            if tk[0] < tk[1] { tk.swap(0, 1); self.rec(s, &tk, 0, 0, 0.0, out, &mut advs); }
        }
        let mx = advs.iter().copied().max().unwrap_or(0);
        if mx > 0 {
            let mut k = 0;
            for i in 0..out.len() { if advs[i] == mx { out[k] = out[i]; k += 1; } }
            out.truncate(k);
        } else { out.clear(); }
    }

    fn key_of(&self, s: &St) -> u32 {
        let mut um: u32 = 0;
        for c in 0..NC { if s.h[c] as i32 >= self.h_max { um |= 1 << c; } }
        s.run as u32 | (um << 9) | ((s.placed as u32) << 18) | ((s.reff as u32) << 22) | (((s.beast + 1) as u32) << 26) | ((s.pounced.min(3) as u32) << 30)
    }

    fn get_bg(&mut self, s: &St) -> (f32, f32) {
        let k = self.key_of(s);
        if let Some(v) = self.cache.get(&k) { return *v; }
        let mut t = *s;
        for c in 0..NC { t.h[c] = if s.h[c] as i32 >= self.h_max { self.h_max as i8 } else { 0 }; }
        let (mut bust, mut gs, mut nb) = (0.0f64, 0.0f64, 0.0f64);
        let mut out = Vec::with_capacity(64);
        for a in 1..=6 { for b in 1..=6 { for c in 1..=6 { for e in 1..=6 {
            self.gen(&t, &[a, b, c, e], &mut out);
            if out.is_empty() { bust += 1.0; continue; }
            let mut bg = 0.0f64;
            for o in out.iter() { if o.g > bg { bg = o.g; } }        // std::max(bg, o.g)
            gs += bg; nb += 1.0;
        } } } }
        let r = ((bust / 1296.0) as f32, (if nb > 0.0 { gs / nb } else { 0.0 }) as f32);
        self.cache.insert(k, r);
        r
    }

    fn score(&mut self, s: &St, now: f64) -> f64 {
        let (b, g) = self.get_bg(s);
        let num = (1.0f32 - b) as f64;                                // (1 - g.b) is float arithmetic in the C++
        let den = { let x = b as f64; if x < 0.03 { 0.03 } else { x } };   // std::max((double)g.b, 0.03)
        let q = num / den;
        let fut = if 30.0 < q { 30.0 } else { q };                    // std::min(q, 30.0)
        now + fut * g as f64
    }

    fn value_of(&self, s: &St) -> f64 {
        let h = &s.h; let mut v = 0.0f64;
        for c in 0..NC {
            v += h[c] as f64 * (if self.policy == 0 { self.dmg[c] as f64 + self.combo } else { 1.0 });
            for r in 1..=h[c] as usize { v += self.bval[self.bonus[c][r] as usize]; v -= self.hv * self.hz[c][r] as f64; if self.sqadd[c][r] != 0 { v += self.sqadd[c][r] as f64; } }
        }
        if s.beast >= 0 && !self.pack_norm { let b = s.beast as usize; let mut e = 0; for r in 1..=h[b] as usize { e += if self.pack_plus { 1 } else { self.dmg[b] + self.sqadd[b][r] + (self.bonus[b][r] == 5) as i32 }; } v += e as f64; }
        v += self.gw * self.guard_of(h) as f64;
        let wn = self.weak_of(h);
        if wn == 2 { v += self.wval2; } else if wn == 1 { v += self.wval; }
        let (wc, wr) = (self.wkc, self.wkr);
        if self.wkt == 3 && self.wval > 0.0 {
            let a = (h[wc] as i32).min(wr); let b = (h[8 - wc] as i32).min(wr);
            if wn == 0 { v += 0.6 * self.wval * a.max(b) as f64 / wr as f64; }
            else if wn == 1 && wc != 4 { v += 0.5 * (self.wval2 - self.wval) * a.min(b) as f64 / wr as f64; }
        } else if wn == 0 && self.wval > 0.0 {
            if self.wkt == 1 { v += 0.6 * self.wval * (h[wc] as i32).min(wr) as f64 / wr as f64; }
            if self.wkt == 2 { v += 0.3 * self.wval * ((h[wc] as i32).min(wr) + (h[8 - wc] as i32).min(wr)) as f64 / wr as f64; }
        }
        v
    }

    /// Best single free step (used by weak-point steps and the common-wild bonus).
    fn best_step(&mut self, s: &St, skip_grapple: bool) -> Option<St> {
        let (mut bs, mut best) = (-1.0f64, None);
        for x in 0..NC {
            if skip_grapple && self.grappled(x) { continue; }
            if self.legal(s, x) {
                let mut n = *s; Sim::app(&mut n, x); let v = self.value_of(&n); let sc = self.score(&n, v);
                if sc > bs { bs = sc; best = Some(n); }
            }
            if self.pack_free && self.beast_ok(s, x) {
                let mut n = *s; Sim::app_beast(&mut n, x); let v = self.value_of(&n); let sc = self.score(&n, v);
                if sc > bs { bs = sc; best = Some(n); }
            }
        }
        best
    }

    fn awards(&mut self, s: &mut St, max_used: &mut bool, bon_done: &mut [bool; NC * 16], rr: &mut RunRes) {
        let mut again = true;
        while again {
            again = false;
            if self.wsteps != 0 && self.wkt == 3 {
                let cs2 = [self.wkc, 8 - self.wkc];
                for k in 0..(if self.wkc == 4 { 1 } else { 2 }) {
                    let c = cs2[k];
                    if s.h[c] as i32 >= self.wkr && !self.wdone[c] {
                        self.wdone[c] = true; again = true;
                        for _ in 0..self.wsteps { if let Some(n) = self.best_step(s, false) { *s = n; } }
                    }
                }
            }
            for c in 0..NC {
                if self.free != 0 && s.h[c] as i32 >= self.h_max && (s.run >> c) & 1 != 0 && !self.freed[c] { self.freed[c] = true; s.placed -= 1; again = true; }
                let mut r = 1usize;
                while r <= s.h[c] as usize {                           // bonus squares crossed
                    let b = self.bonus[c][r];
                    if b != 0 && !bon_done[c * 16 + r] {
                        bon_done[c * 16 + r] = true; rr.bonus[b as usize] += 1; again = true;
                        if b == 6 && self.timestop > 0 && !self.ts_used {
                            self.ts_used = true; let n = self.rng.d6() + self.ts_plus; rr.ts = n;
                            if self.timestop == 2 { self.ts_bank = n; } else { self.ts_left = n; }   // 2: banked for when the attack would end
                        }
                        if self.commonwild && b == 1 { if let Some(n) = self.best_step(s, false) { *s = n; } }
                    }
                    r += 1;
                }
                if self.maxrun == 1 && !*max_used && s.h[c] as i32 >= self.maxm[c] && (s.run >> c) & 1 != 0 {
                    *max_used = true; again = true; rr.maxbonus += 1; s.reff += 1;
                    let (mut bs, mut bc) = (-1.0f64, None);
                    for x in 0..NC {
                        if s.h[x] as i32 >= self.h_max || (s.run >> x) & 1 != 0 || (self.lockm >> x) & 1 != 0 || self.grappled(x) { continue; }
                        let mut n = *s; Sim::app(&mut n, x); let v = self.value_of(&n); let sc = self.score(&n, v);
                        if sc > bs { bs = sc; bc = Some(x); }
                    }
                    if let Some(bc) = bc { Sim::app(s, bc); }
                }
                if self.maxrun >= 2 && s.h[c] as i32 >= self.maxm[c] && ((s.run >> c) & 1 != 0 || s.beast == c as i8) && !self.max_done[c] && !(self.maxrun == 2 && *max_used) {
                    self.max_done[c] = true; *max_used = true; again = true; rr.maxbonus += 1;
                    for _ in 0..(if self.maxrun == 4 { 2 } else { 1 }) { if let Some(n) = self.best_step(s, true) { *s = n; } }
                }
            }
        }
    }

    fn run(&mut self) -> RunRes {
        self.hz = [[0; HMAX + 1]; 9]; self.lance_c = -1;          // per-attack state starts here
        for _ in 0..self.nhz {                                         // place traps
            let (mut c, mut r);
            loop {
                let sm = self.rng.d6() + self.rng.d6();
                if !(3..=11).contains(&sm) { continue; }
                c = (sm - 3) as usize; r = self.rng.d6() as usize;
                if self.hz[c][r] == 0 && self.bonus[c][r] == 0 { break; }
            }
            self.hz[c][r] = 1;
        }
        let mut s = St { h: [0; NC], run: 0, placed: 0, reff: self.r as i8, beast: -1, pounced: 0 };
        for c in 0..NC { s.h[c] = self.inith[c] as i8; }
        let mut rr = RunRes::default();
        let mut max_used = false; let mut bon_done = [false; NC * 16];
        self.max_done = [false; NC]; self.freed = [false; NC]; self.wdone = [false; NC];
        for c in 0..NC {
            for r in 1..=self.inith[c] as usize { bon_done[c * 16 + r] = true; }
            if self.inith[c] >= self.maxm[c] { self.max_done[c] = true; }
            if self.inith[c] >= self.h_max { self.freed[c] = true; }
        }
        if self.charge > 0 {                                          // Charge: a runner starts on row `charge`
            let (mut bs, mut best) = (-1.0f64, None);
            for c in 0..NC {
                if !self.legal(&s, c) { continue; }
                let mut n = s; n.run |= 1 << c; n.placed += 1; n.h[c] = self.charge.min(self.h_max) as i8;
                if self.charge_extra { n.reff += 1; }                    // the lance runner doesn't count toward the 3
                let v = self.value_of(&n); let sc = self.score(&n, v);
                if sc > bs { bs = sc; best = Some(n); }
            }
            if let Some(n) = best {
                if self.lance2 > 0 { self.lance_c = (0..NC).find(|&c| n.h[c] != s.h[c]).map(|c| c as i32).unwrap_or(-1); }
                s = n; self.awards(&mut s, &mut max_used, &mut bon_done, &mut rr);
            }
        }
        self.head_c = -1; self.ts_used = false; self.ts_left = 0; self.ts_bank = 0; self.ts_ending = false;
        if self.head > 0 {
            let (mut bs, mut best) = (-1.0f64, None);
            for c in 0..NC {
                if !self.legal(&s, c) || (self.head_col >= 0 && c as i32 != self.head_col) { continue; }
                let mut n = s; n.run |= 1 << c; n.placed += 1; n.h[c] = self.head.min(self.h_max) as i8;
                let v = self.value_of(&n) - self.col_dmg(&n, c) as f64; let sc = self.score(&n, v);   // old squares are worth nothing now
                if sc > bs { bs = sc; best = Some((n, c)); }
            }
            if let Some((n, c)) = best {
                s = n; self.head_c = c as i32;
                for r in 1..=s.h[c] as usize { bon_done[c * 16 + r] = true; }
                if s.h[c] as i32 >= self.maxm[c] { self.max_done[c] = true; }
                if s.h[c] as i32 >= self.wkr && (c == self.wkc || c == 8 - self.wkc) { self.wdone[c] = true; }
            }
        }
        let mut unstop_used = false; let mut reserve_used = false;
        let mut out: Vec<Opt> = Vec::with_capacity(64);
        let mut d = [0i32; 4];
        let (mut strikes, mut rerolls) = (0, 0);
        loop {
            if rr.rolls >= self.rollcap { break; }
            for i in 0..4 { d[i] = self.rng.d6(); }
            rr.throws += 1;
            let mut fat_on = false;
            if self.fat != 0 || self.fattrig != 0 {
                if self.fattrig == 0 { fat_on = rr.rolls + 1 >= self.fat; }
                else if self.fattrig == 1 { for c in 0..NC { if s.h[c] as i32 >= self.fat { fat_on = true; } } }
                else { for c in 0..NC { if s.h[c] as i32 >= self.maxm[c] { fat_on = true; } } }
                if rr.rolls + 1 <= self.safe { fat_on = false; }
            }
            if fat_on { rr.danger = 1; }
            if self.reserve == 2 && fat_on && !reserve_used { reserve_used = true; rr.reserve = 1; s.reff += 1; }
            if fat_on {
                let mut cnt = [0i32; 7];
                for i in 0..4 { cnt[d[i] as usize] += 1; }
                let (mut pr, mut tr) = (0, 0);
                for v in 1..=6 { pr += cnt[v] / 2; if cnt[v] >= 3 { tr = 1; } }
                let f = match self.fatmode { 1 => pr >= 2 || tr == 1, 2 => pr >= 1, 3 => tr == 1, _ => false };
                if f && self.ts_left == 0 && self.ts_bank > 0 { self.ts_left = self.ts_bank; self.ts_bank = 0; self.ts_ending = true; }   // time stops instead
                if f && self.ts_left > 0 { /* time is stopped: no fumble */ }
                else if f {
                    if rerolls < self.rr_max { rerolls += 1; rr.rrused += 1; continue; }
                    if self.unstop && !unstop_used {
                        unstop_used = true; rr.ucount = 1;
                        if let Some(n) = self.best_step(&s, true) { s = n; }
                        rr.rolls += 1; self.awards(&mut s, &mut max_used, &mut bon_done, &mut rr);
                        continue;
                    }
                    rr.busts += 1; rr.fumble = 1; break;
                }
            }
            self.gen(&s, &d, &mut out);
            if out.is_empty() && self.ts_left == 0 && self.ts_bank > 0 { self.ts_left = self.ts_bank; self.ts_bank = 0; self.ts_ending = true; }
            if out.is_empty() && self.ts_left > 0 { self.ts_left -= 1; rr.rolls += 1; if self.ts_left == 0 && self.ts_ending { break; } continue; }
            if out.is_empty() && self.reserve == 1 && !reserve_used {
                let mut t = s; t.reff += 1; self.gen(&t, &d, &mut out);
                if !out.is_empty() { reserve_used = true; rr.reserve = 1; s = t; }
            }
            if out.is_empty() {
                if rr.rolls < self.safe { continue; }
                if rerolls < self.rr_max { rerolls += 1; rr.rrused += 1; continue; }
                strikes += 1; rr.busts += 1;
                if strikes >= self.strikes { break; }
                continue;
            }
            let (mut best, mut bi) = (-1.0f64, 0usize);
            for i in 0..out.len() {
                let st = out[i].s; let v = self.value_of(&st); let sc = self.score(&st, v);
                if sc > best { best = sc; bi = i; }
            }
            s = out[bi].s; rr.rolls += 1;
            let frozen = self.ts_left > 0;
            self.awards(&mut s, &mut max_used, &mut bon_done, &mut rr);
            if self.hzmode == 2 {
                let mut tr = false;
                for c in 0..NC { for r in 1..=s.h[c] as usize {
                    if self.hz[c][r] == 1 {
                        if self.rng.uniform01() < self.evade { self.hz[c][r] = 2; rr.evaded += 1; } else { tr = true; }
                    }
                } }
                if tr { rr.fumble = 1; rr.trapped = 1; break; }
            }
            if frozen { self.ts_left -= 1; if self.ts_left == 0 && self.ts_ending { break; } }
            if self.stop && (0..NC).any(|c| s.h[c] as i32 >= self.fat) {
                let (b, g) = self.get_bg(&s); let (b, g) = (b as f64, g as f64);
                let mut sb = self.stop_bonus * s.placed as f64 + self.stop_guardx * self.gw * self.guard_of(&s.h) as f64 + self.stop_val;
                let tall = (0..NC).filter(|&c| (s.run >> c) & 1 != 0 && (s.h[c] as i32) < self.h_max)
                    .max_by(|&a, &b| (s.h[a] as f64 * self.w(a)).partial_cmp(&(s.h[b] as f64 * self.w(b))).unwrap().then(a.cmp(&b)));
                if self.stop_keep > 0.0 { if let Some(c) = tall { sb += self.stop_keep * self.col_dmg(&s, c) as f64; } }
                let ev = (1.0 - self.pfumble - b).max(0.0) * g - self.pfumble * (self.counter + sb) - b * sb;
                if ev < 0.0 { rr.stopped = 1; if let Some(c) = tall { rr.keep = s.h[c] as i32; rr.keepc = c as i32; } break; }
            }
        }
        rr.runners = s.placed as i32;
        for c in 0..NC {
            rr.h[c] = s.h[c] as i32; rr.dmg += self.new_dmg(&s, c);
            for r in 1..=s.h[c] as usize { if self.hz[c][r] != 0 { rr.hzhit += 1; } }
        }
        rr.topcol = 0;
        for c in 0..NC { let v = self.new_dmg(&s, c); if v > rr.topcol { rr.topcol = v; } }
        rr.mask = 0;
        let mut k = 0;
        for c in 0..NC { for r in 1..=self.h_max as usize { let b = self.bonus[c][r]; if (1..=4).contains(&b) || b == 6 { if s.h[c] as usize >= r { rr.mask |= 1i64 << k; } k += 1; } } }
        rr.guard = self.guard_of(&s.h); rr.weak = self.weak_of(&s.h);
        if self.wcol != 0 {
            let mut ex = 0; let cs = [self.wkc, 8 - self.wkc];
            for k in 0..(if self.wkc == 4 { 1 } else { 2 }) {
                let c = cs[k];
                if s.h[c] as i32 >= self.wkr { ex += self.new_dmg(&s, c); }
            }
            if rr.weak == 1 { rr.dmg += (ex as f64 * (self.wcolm - 1.0) + 0.5) as i32 + self.wflat; }
            else if rr.weak == 2 { rr.dmg = (rr.dmg as f64 * self.wmult2 + 0.5) as i32 + self.wflat; }
        } else if rr.weak == 1 { rr.dmg = (rr.dmg as f64 * self.wmult + 0.5) as i32; }
        else if rr.weak == 2 { rr.dmg = (rr.dmg as f64 * self.wmult2 + 0.5) as i32; }
        rr
    }
}

/// C atoi: optional sign and leading digits, 0 if none.
fn atoi(s: &str) -> i32 {
    let t = s.trim_start(); let b = t.as_bytes(); let mut i = 0; let mut neg = false;
    if i < b.len() && (b[i] == b'-' || b[i] == b'+') { neg = b[i] == b'-'; i += 1; }
    let mut v: i64 = 0;
    while i < b.len() && b[i].is_ascii_digit() { v = v * 10 + (b[i] - b'0') as i64; i += 1; }
    (if neg { -v } else { v }) as i32
}
/// C atof (the arguments used are plain decimals).
fn atof(s: &str) -> f64 { s.trim().parse::<f64>().unwrap_or_else(|_| atoi(s) as f64) }

fn main() {
    let all: Vec<String> = std::env::args().collect();
    let opts: Vec<(String, String)> = all.iter().skip(1).filter_map(|a| a.split_once('=').map(|(k, v)| (k.to_string(), v.to_string()))).collect();
    let argv: Vec<String> = all.into_iter().filter(|a| !a.contains('=')).collect();
    let argc = argv.len();
    if argc < 2 { eprintln!("usage: cs5 N policy commonwild layout ... (same positional arguments as cs5.cpp)"); std::process::exit(2); }
    let mut m = Sim::new();
    let n_runs = atoi(&argv[1]);
    m.policy = atoi(&argv[2]);
    m.commonwild = atoi(&argv[3]) != 0;
    let layout = if argc > 4 && argv[4] != "-" { Some(argv[4].clone()) } else { None };
    if argc > 5 { m.strikes = atoi(&argv[5]); }
    if argc > 6 { m.rollcap = atoi(&argv[6]); }
    if argc > 7 { m.safe = atoi(&argv[7]); }
    if argc > 8 { m.maxrun = atoi(&argv[8]); }
    if argc > 9 && atoi(&argv[9]) == 1 { m.dmg = [2, 1, 1, 0, 0, 0, 1, 1, 2]; m.combo = 0.5; m.bval[1] = 1.5; }
    if argc > 10 { m.free = atoi(&argv[10]); m.bval[2] = 3.0; m.bval[3] = 5.0; m.bval[4] = 8.0; m.bval[6] = 13.0; }
    if let Some(path) = layout {
        let text = std::fs::read_to_string(&path).unwrap_or_else(|e| { eprintln!("cannot read layout {path}: {e}"); std::process::exit(1) });
        let nums: Vec<i32> = text.split_whitespace().map_while(|t| t.parse::<i32>().ok()).collect();
        for tri in nums.chunks_exact(3) { m.bonus[tri[0] as usize][tri[1] as usize] = tri[2]; }
    }
    if argc > 12 {
        m.h_max = atoi(&argv[12]);
        let base = [4, 6, 8, 10, 12, 10, 8, 6, 4];
        for c in 0..NC { m.maxm[c] = (base[c] as f64 * m.h_max as f64 / 12.0 + 0.5).floor() as i32; }
    }
    if argc > 13 && atoi(&argv[13]) == 0 { m.sumcol[2] = -2; m.sumcol[12] = -2; }
    if argc > 18 {
        let l = atoi(&argv[18]);
        let block: &[usize] = match l { 311 => &[3, 11], 68 => &[6, 8], 678 => &[6, 7, 8], 759 => &[7, 5, 9], 7410 => &[7, 4, 10], 7311 => &[7, 3, 11], _ => &[] };
        for &x in block { m.sumcol[x] = -2; }
        if block.is_empty() && l > 0 { m.sumcol[l as usize] = -2; }
    }
    if argc > 19 {
        match atoi(&argv[19]) { 1 => { m.dmg[0] = 1; m.dmg[8] = 1; } 2 => { m.dmg[1] = 0; m.dmg[2] = 0; m.dmg[6] = 0; m.dmg[7] = 0; } 3 => { m.dmg[3] = 1; m.dmg[4] = 1; m.dmg[5] = 1; } _ => {} }
    }
    if argc > 14 { m.r = atoi(&argv[14]); }
    if argc > 15 { m.fat = atoi(&argv[15]); m.fatmode = atoi(&argv[16]); }
    if argc > 17 { m.fattrig = atoi(&argv[17]); }
    if argc > 20 { m.guard = atoi(&argv[20]); m.gw = atof(&argv[21]); }
    if argc > 22 { m.wkt = atoi(&argv[22]); m.wkc = atoi(&argv[23]) as usize; m.wkr = atoi(&argv[24]); m.wmult = atof(&argv[25]); m.wval = atof(&argv[26]); }
    if argc > 27 { m.nhz = atoi(&argv[27]); m.hv = atof(&argv[28]); }
    if argc > 30 { m.hzmode = atoi(&argv[30]); }
    if argc > 31 { m.evade = atof(&argv[31]); }
    if argc > 32 { m.wmult2 = atof(&argv[32]); m.wval2 = atof(&argv[33]); }
    if argc > 34 { m.wcol = atoi(&argv[34]); }
    if argc > 35 { m.wcolm = atof(&argv[35]); }
    if argc > 36 { m.wflat = atoi(&argv[36]); }
    if argc > 37 { m.wsteps = atoi(&argv[37]); }
    if argc > 38 { m.rr_max = atoi(&argv[38]); }
    if argc > 40 { m.lockm = atoi(&argv[39]) as u32; m.grapm = atoi(&argv[40]) as u32; }
    if argc > 49 { for i in 0..NC { m.dmg[i] = atoi(&argv[41 + i]); } }
    if argc > 50 && argv[50] != "-" {
        let v: Vec<i32> = argv[50].split(',').map(atoi).collect();
        if v.len() == NC { for c in 0..NC { m.maxm[c] = v[c]; } }
    }
    for (k, v) in &opts {
        m.ext = true;
        match k.as_str() {
            "sqadd" => for part in v.split(';').filter(|p| !p.is_empty()) {      // col:from_row:add, e.g. 0:6:1
                let f: Vec<i32> = part.split(':').map(atoi).collect();
                if f.len() == 3 { for r in (f[1].max(1) as usize)..=HMAX { m.sqadd[f[0] as usize][r] += f[2]; } }
            },
            "stop" => m.stop = atoi(v) != 0,
            "stopguard" => m.stop_bonus = atof(v),
            "counter" => m.counter = atof(v),
            "charge" => m.charge = atoi(v),
            "bloodlust" => m.bloodlust = atoi(v) != 0,
            "unstop" => m.unstop = atoi(v) != 0,
            "pack" => m.pack = atoi(v) != 0,
            "packwild" => m.pack_wild = atoi(v) != 0,
            "stopguardx" => m.stop_guardx = atof(v),
            "reserve" => m.reserve = atoi(v),
            "stopval" => m.stop_val = atof(v),
            "stopkeep" => m.stop_keep = atof(v),
            "timestop" => m.timestop = atoi(v),
            "chargex" => m.charge_extra = atoi(v) != 0,
            "packplus" => m.pack_plus = atoi(v) != 0,
            "packfree" => m.pack_free = atoi(v) != 0,
            "packwith" => m.pack_with = atoi(v) != 0,
            "packnorm" => m.pack_norm = atoi(v) != 0,
            "pack12" => m.pack12 = atoi(v) != 0,
            "packonce" => m.pack_once = atoi(v) != 0,
            "lance2" => m.lance2 = atoi(v),
            "packcap" => m.pack_cap = atoi(v) != 0,
            "packmax" => m.pack_max = atoi(v),
            "tsplus" => m.ts_plus = atoi(v),
            "head" => { if let Some((c, k)) = v.split_once(':') { m.head_col = atoi(c); m.head = atoi(k); } else { m.head = atoi(v); } }
            _ => { eprintln!("unknown option {k}"); std::process::exit(2); }
        }
    }
    if m.pack12 && m.sumcol[12] == -1 { m.sumcol[12] = -3; }            // Pack pounces on double sixes
    for c in 0..NC {                                                    // per-square extras the bot plans around
        let rows = m.h_max.max(1) as usize;
        m.col_extra[c] = (1..=rows).map(|r| m.sqadd[c][r] as f64).sum::<f64>() / rows as f64;
    }
    {                                                                   // chance that one roll fumbles past the danger line
        let mut n = 0;
        for a in 1..=6 { for b in 1..=6 { for c in 1..=6 { for e in 1..=6 {
            let mut cnt = [0i32; 7]; for x in [a, b, c, e] { cnt[x as usize] += 1; }
            let (mut pr, mut tr) = (0, 0); for v in 1..=6 { pr += cnt[v] / 2; if cnt[v] >= 3 { tr = 1; } }
            if match m.fatmode { 1 => pr >= 2 || tr == 1, 2 => pr >= 1, 3 => tr == 1, _ => false } { n += 1; }
        } } } }
        m.pfumble = n as f64 / 1296.0;
    }
    let cont = if argc > 11 { atoi(&argv[11]) } else { 0 };
    if cont != 6 {
        eprintln!("cs5 (Rust): only the data-dump mode (argument 11 = 6) is ported; the analysis modes 0/1/2/8/9 remain in cs5.cpp");
        std::process::exit(2);
    }
    let dump = if argc > 29 { argv[29].clone() } else { eprintln!("missing output file (argument 29)"); std::process::exit(2) };
    let f = std::fs::File::create(&dump).unwrap_or_else(|e| { eprintln!("cannot write {dump}: {e}"); std::process::exit(1) });
    let mut o = BufWriter::new(f);
    for _ in 0..n_runs {
        let a = m.run();
        write!(o, "{} {} {} {} {} {} {} {} {} {}", a.dmg, a.guard, a.fumble, a.weak, a.hzhit, a.rolls, a.evaded, a.trapped, a.topcol, a.mask).unwrap();
        for c in 0..NC { write!(o, " {}", a.h[c]).unwrap(); }
        if m.ext { writeln!(o, " {} {} {} {} {} {} {} {}", a.rrused, a.stopped, a.runners, a.ucount, a.reserve, a.keep, a.keepc, a.ts).unwrap(); }
        else { writeln!(o, " {}", a.rrused).unwrap(); }
    }
}
