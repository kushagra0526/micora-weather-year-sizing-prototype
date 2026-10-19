"""Hourly solar + LFP battery + small generator dispatch on real PVGIS weather years,
vectorised over many candidate configurations at once."""
import numpy as np

BLOCK_KW = 0.4                     # one Solar Block module
RACK_KWH = 5.0                     # one LFP rack
ETA = 0.92 ** 0.5                  # one-way battery efficiency (92% round trip)
SOC_MIN, C_RATE = 0.10, 0.5
GEN_MIN = 0.30                     # generator minimum load fraction
COST = dict(pv_kw=700.0, bat_kwh=300.0, gen_kw=400.0, fuel_l=1.6, fuel_years=10)
EPOCH_WEEKDAY = 5                  # 2005-01-01 was a Saturday (Mon=0)


def load_site(name):
    """Hourly PV per kWp. Whole days with ~zero output are data gaps, not weather (PVGIS-NSRDB has a
    12-day all-zero stretch in Sept 2012 at every site): those days are dropped from the series."""
    d = np.load(f"data/pv/{name}.npz")
    P, yr = d["P"].astype(float), d["year"]
    day = P[: len(P) // 24 * 24].reshape(-1, 24).sum(1)
    gap = np.repeat(day < 0.05, 24)
    keep = np.r_[~gap, np.ones(len(P) - gap.size, bool)]
    return dict(name=name, P=P[keep], year=yr[keep], hour_index=np.arange(len(P))[keep],
                gap_days=int((day < 0.05).sum()), offset=int(round(float(d["lon"]) / 15)))


def load_profile(site, kind, peak_kw, seed=0):
    n = len(site["P"])
    h_utc = site["hour_index"]
    local = h_utc + site["offset"]
    hour = local % 24
    dow = (EPOCH_WEEKDAY + local // 24) % 7
    if kind == "flat":                     # data center / process load
        x = np.full(n, 0.85)
    elif kind == "two_shift":              # manufacturing, weekdays 06-22
        x = np.where((dow < 5) & (hour >= 6) & (hour < 22), 1.0, 0.25)
    elif kind == "camp":                   # remote camp / island community, evening peak
        x = np.select([(hour >= 17) & (hour < 23), (hour >= 6) & (hour < 9)], [1.0, 0.6], 0.3)
    else:
        raise ValueError(kind)
    rng = np.random.default_rng(seed)
    return peak_kw * x * (1 + 0.05 * rng.standard_normal(n))


def simulate(site, load, kwp, bat_kwh, gen_kw, fuel_cap_l, years):
    """All arguments after `load` are arrays over configurations (or scalars).
    Returns dict of arrays [config, year]: share of hours fully served, unmet kWh, fuel L."""
    kwp, bat, gen = np.broadcast_arrays(np.asarray(kwp, float), np.asarray(bat_kwh, float), np.asarray(gen_kw, float))
    C = kwp.size
    kwp, bat, gen = kwp.ravel(), bat.ravel(), gen.ravel()
    sel = np.isin(site["year"], years)
    P, L, Y = site["P"][sel], load[sel], site["year"][sel]
    ys = list(years)
    ok = np.zeros((C, len(ys)))
    unmet = np.zeros((C, len(ys)))
    fuel = np.zeros((C, len(ys)))
    hours = np.zeros(len(ys))
    soc = 0.5 * bat
    lo, rate = SOC_MIN * bat, C_RATE * bat
    fuel_y = np.zeros(C)
    yidx = np.searchsorted(np.array(ys), Y)
    yi_prev = -1
    for h in range(len(P)):
        yi = int(yidx[h])
        if yi != yi_prev:                                    # new year: the fuel tank is refilled once
            fuel_y[:] = 0.0
            yi_prev = yi
        pv, l = P[h] * kwp, L[h]
        net = pv - l
        # surplus charges the battery
        ch = np.minimum(np.minimum(np.maximum(net, 0) * ETA, bat - soc), rate)
        # shortfall: battery first
        need = np.maximum(-net, 0)
        d = np.minimum(np.minimum(need / ETA, np.maximum(soc - lo, 0)), rate)
        short = need - d * ETA
        # then the generator, if it has fuel left this year
        run = (short > 1e-9) & (gen > 0) & (fuel_y < fuel_cap_l)
        g = np.where(run, np.clip(short, GEN_MIN * gen, gen), 0.0)
        extra = np.maximum(g - short, 0)                     # min-load surplus goes into the battery
        f = np.where(run, 0.246 * g + 0.08415 * gen, 0.0)
        fuel_y += f
        miss = np.maximum(short - g, 0)
        soc = soc + ch - d + np.minimum(extra * ETA, np.maximum(bat - (soc + ch - d), 0))
        ok[:, yi] += miss <= 0.01 * l
        unmet[:, yi] += miss
        fuel[:, yi] += f
        hours[yi] += 1
    return dict(served=ok / hours, unmet=unmet, fuel=fuel, years=ys)


def cost(kwp, bat, gen, fuel_per_year):
    c = COST
    return kwp * c["pv_kw"] + bat * c["bat_kwh"] + gen * c["gen_kw"] + fuel_per_year * c["fuel_l"] * c["fuel_years"]


def rule_of_thumb(site, load, years, peak_kw):
    """Daily energy over average peak-sun-hours with 20% derate; one day of battery; generator at half peak."""
    sel = np.isin(site["year"], years)
    psh = site["P"][sel].sum() / (sel.sum() / 24)          # kWh per kWp per day, averaged
    daily = load[sel].mean() * 24
    kwp = daily / (psh * 0.8)
    bat = np.ceil(daily / (1 - SOC_MIN) / RACK_KWH) * RACK_KWH
    return np.ceil(kwp / BLOCK_KW) * BLOCK_KW, bat, 0.5 * peak_kw
