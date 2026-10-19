"""Cheapest configuration that keeps >= target share of hours fully served in EVERY sizing year."""
import numpy as np
from . import core

TARGET = 0.98
PV_MULT = np.round(np.arange(0.6, 3.01, 0.2), 2)          # x rule-of-thumb kWp
BAT_DAYS = np.array([0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0])
GEN_FRAC = np.array([0.0, 0.3])                            # x peak load
FUEL_CAP_L = 2000.0                                        # one tank a year, no deliveries


def grid(kwp0, daily, peak):
    k, b, g = np.meshgrid(PV_MULT * kwp0, BAT_DAYS * daily / (1 - core.SOC_MIN), GEN_FRAC * peak, indexing="ij")
    k = np.ceil(k / core.BLOCK_KW) * core.BLOCK_KW
    b = np.ceil(b / core.RACK_KWH) * core.RACK_KWH
    return k.ravel(), b.ravel(), g.ravel()


def size(site, load, years, peak):
    kwp0, bat0, gen0 = core.rule_of_thumb(site, load, years, peak)
    sel = np.isin(site["year"], years)
    daily = load[sel].mean() * 24
    k, b, g = grid(kwp0, daily, peak)
    r = core.simulate(site, load, k, b, g, FUEL_CAP_L, years)
    worst = r["served"].min(axis=1)
    c = core.cost(k, b, g, r["fuel"].mean(axis=1))
    okc = worst >= TARGET
    if not okc.any():
        i = int(np.argmax(worst))
    else:
        i = int(np.where(okc)[0][np.argmin(c[okc])])
    # installer-style fix: scale the rule-of-thumb system up uniformly until it meets the target
    f = np.round(np.arange(1.0, 4.01, 0.1), 2)
    ks, bs = np.ceil(kwp0 * f / core.BLOCK_KW) * core.BLOCK_KW, np.ceil(bat0 * f / core.RACK_KWH) * core.RACK_KWH
    rs = core.simulate(site, load, ks, bs, np.full(f.size, gen0), FUEL_CAP_L, years)
    j = int(np.argmax(rs["served"].min(axis=1) >= TARGET)) if (rs["served"].min(axis=1) >= TARGET).any() else f.size - 1
    return dict(kwp=float(k[i]), bat=float(b[i]), gen=float(g[i]), cost=float(c[i]), worst_sizing=float(worst[i]),
                met_in_sizing=bool(okc.any()),
                rule=dict(kwp=float(kwp0), bat=float(bat0), gen=float(gen0)),
                rule_scaled=dict(kwp=float(ks[j]), bat=float(bs[j]), gen=float(gen0), factor=float(f[j])))


def check(site, load, cfg, years):
    r = core.simulate(site, load, [cfg["kwp"]], [cfg["bat"]], [cfg["gen"]], FUEL_CAP_L, years)
    return dict(served=r["served"][0].tolist(), worst=float(r["served"][0].min()), fuel=float(r["fuel"][0].mean()),
                cost=float(core.cost(cfg["kwp"], cfg["bat"], cfg["gen"], r["fuel"][0].mean())))
