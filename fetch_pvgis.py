"""Download hourly PV output per kWp (PVGIS, EU JRC, free public API) for each site, all years."""
import json, sys, urllib.request
import numpy as np

SITES = {
    # dev
    "honolulu_hi": (21.31, -157.86), "reno_nv": (39.53, -119.81), "austin_tx": (30.27, -97.74), "chicago_il": (41.88, -87.63),
    # held-out
    "seattle_wa": (47.61, -122.33), "phoenix_az": (33.45, -112.07), "denver_co": (39.74, -104.99), "hilo_hi": (19.71, -155.09),
}


def fetch(name, lat, lon):
    tilt = round(min(abs(lat), 35))
    url = (f"https://re.jrc.ec.europa.eu/api/v5_2/seriescalc?lat={lat}&lon={lon}&pvcalculation=1&peakpower=1"
           f"&loss=14&angle={tilt}&aspect=0&outputformat=json")
    d = json.load(urllib.request.urlopen(url, timeout=300))
    h = d["outputs"]["hourly"]
    P = np.array([x["P"] for x in h], np.float32) / 1000.0        # W per kWp -> kW per kWp
    T = np.array([x["T2m"] for x in h], np.float32)
    yr = np.array([int(x["time"][:4]) for x in h], np.int16)
    np.savez_compressed(f"data/pv/{name}.npz", P=P, T=T, year=yr, lat=lat, lon=lon, tilt=tilt,
                        source=d["inputs"]["meteo_data"]["radiation_db"])
    print(name, yr.min(), yr.max(), round(float(P.sum() / len(set(yr))), 0), "kWh/kWp/yr", d["inputs"]["meteo_data"]["radiation_db"])


if __name__ == "__main__":
    for n, (la, lo) in SITES.items():
        if len(sys.argv) == 1 or n in sys.argv[1:]:
            fetch(n, la, lo)
