"""One site, one load: rule-of-thumb sizing vs weather-year sizing, checked on years not used to size."""
import sys
from sizer import core, optimize

sys.stdout.reconfigure(encoding="utf-8")
SITE, KIND, PEAK = "austin_tx", "camp", 60.0
s = core.load_site(SITE)
L = core.load_profile(s, KIND, PEAK)
optimize.TARGET = 0.99                          # 98% target + 1-point margin, chosen on dev
o = optimize.size(s, L, range(2005, 2011), PEAK)
optimize.TARGET = 0.98
print(f"{SITE}, '{KIND}' load (evening peak {PEAK:.0f} kW), PVGIS hourly weather 2005-2015")
print(f"target: >= 98% of hours fully served in EVERY year · sized on 2005-2010 · checked on 2011-2015\n")
for name, cfg in (("rule of thumb", o["rule"]), (f"rule x{o['rule_scaled']['factor']:.1f} (scaled until it passes 2005-10)", o["rule_scaled"]),
                  ("weather-year optimized (this)", o)):
    c = optimize.check(s, L, cfg, range(2011, 2016))
    yrs = "  ".join(f"{y}:{100 * v:5.1f}%" for y, v in zip(range(2011, 2016), c["served"]))
    blocks = int(round(cfg["kwp"] / core.BLOCK_KW))
    racks = int(round(cfg["bat"] / core.RACK_KWH))
    ok = "MEETS 98%" if c["worst"] >= 0.98 else "MISSES 98%"
    print(f"{name}")
    print(f"   {blocks} Solar Blocks ({cfg['kwp']:.0f} kWp), {racks} racks ({cfg['bat']:.0f} kWh), generator {cfg['gen']:.0f} kW")
    print(f"   {yrs}   -> {ok}, ${c['cost'] / 1e3:,.0f}k incl. 10 yrs fuel ({c['fuel']:.0f} L/yr)\n")
