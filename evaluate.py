"""Size on 2005-2010, check 2011-2015: rule of thumb vs cost-optimal sizing.
python evaluate.py [dev|heldout] [out.json]"""
import json, sys, time
from sizer import core, optimize

SIZE_YEARS, TEST_YEARS = range(2005, 2011), range(2011, 2016)
LOADS = [("flat", 50.0), ("two_shift", 120.0), ("camp", 60.0)]
DEV_SITES = ["honolulu_hi", "reno_nv", "austin_tx", "chicago_il"]


def run(which, margin=None):
    if which == "heldout":
        h = json.load(open("heldout/config.json"))
        sites, margin = h["sites"], h["margin"]
    else:
        sites = DEV_SITES
    margin = 0.0 if margin is None else margin
    rows = []
    for name in sites:
        s = core.load_site(name)
        for kind, peak in LOADS:
            L = core.load_profile(s, kind, peak)
            optimize.TARGET = 0.98 + margin
            o = optimize.size(s, L, SIZE_YEARS, peak)
            optimize.TARGET = 0.98
            rule = optimize.check(s, L, o["rule"], TEST_YEARS)
            opt = optimize.check(s, L, o, TEST_YEARS)
            scaled = optimize.check(s, L, o["rule_scaled"], TEST_YEARS)
            rows.append(dict(site=name, load=kind, peak=peak, rule_cfg=o["rule"], opt_cfg={k: o[k] for k in ("kwp", "bat", "gen")},
                             scaled_cfg=o["rule_scaled"], rule=rule, opt=opt, scaled=scaled,
                             rule_sizing=optimize.check(s, L, o["rule"], SIZE_YEARS)["worst"]))
    met = lambda k: sum(r[k]["worst"] >= 0.98 for r in rows)
    tot = lambda k: sum(r[k]["cost"] for r in rows)
    return dict(set=which, margin=margin, cases=len(rows), rule_met=met("rule"), opt_met=met("opt"), scaled_met=met("scaled"),
                rule_cost=tot("rule"), opt_cost=tot("opt"), scaled_cost=tot("scaled"), rows=rows)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    margin = float(sys.argv[2]) if len(sys.argv) > 2 and which == "dev" else None
    t0 = time.time()
    r = run(which, margin)
    print(f"{which}: {r['cases']} site x load cases, sized on 2005-2010 at {0.98 + r['margin']:.2f}, checked on 2011-2015 ({time.time() - t0:.0f}s)")
    for x in r["rows"]:
        print(f"  {x['site']:12s} {x['load']:9s} rule: worst test yr {100 * x['rule']['worst']:5.1f}% ${x['rule']['cost'] / 1e3:6.0f}k   "
              f"optimized: {100 * x['opt']['worst']:5.1f}% ${x['opt']['cost'] / 1e3:6.0f}k  "
              f"({x['opt_cfg']['kwp']:.0f} kWp, {x['opt_cfg']['bat']:.0f} kWh, gen {x['opt_cfg']['gen']:.0f} kW)")
    print(f"  met 98% in the worst test year: rule of thumb {r['rule_met']}/{r['cases']} (${r['rule_cost'] / 1e6:.2f}M), "
          f"rule scaled up to meet it on sizing years {r['scaled_met']}/{r['cases']} (${r['scaled_cost'] / 1e6:.2f}M), "
          f"optimized {r['opt_met']}/{r['cases']} (${r['opt_cost'] / 1e6:.2f}M)")
    out = sys.argv[2] if which == "heldout" and len(sys.argv) > 2 else (sys.argv[3] if len(sys.argv) > 3 else None)
    if out:
        json.dump(r, open(out, "w"), indent=1)
