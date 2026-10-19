import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

r = json.load(open("out/heldout_first_run.json"))
rows = r["rows"]
lab = [f"{x['site'].split('_')[0]}\n{x['load']}" for x in rows]
x = np.arange(len(rows))
fig, ax = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
for j, (k, col, name) in enumerate((("rule", "#bbb", "rule of thumb"), ("scaled", "#888", "rule scaled up"), ("opt", "#2a7", "weather-year optimized"))):
    ax[0].bar(x + (j - 1) * 0.27, [100 * row[k]["worst"] for row in rows], 0.27, color=col, label=name)
    ax[1].bar(x + (j - 1) * 0.27, [row[k]["cost"] / 1e3 for row in rows], 0.27, color=col, label=name)
ax[0].axhline(98, color="r", lw=1, ls="--"); ax[0].set_ylim(65, 101); ax[0].set_ylabel("% hours served,\nworst year 2011-15")
ax[1].set_ylabel("cost $k (capex + 10 yr fuel)")
ax[1].set_xticks(x); ax[1].set_xticklabels(lab, fontsize=8)
ax[0].legend(fontsize=8, loc="lower right")
fig.suptitle("Held-out sites (PVGIS 2005-2015): sized on 2005-10, checked on 2011-15, target 98%")
fig.tight_layout()
fig.savefig("docs/result.png", dpi=105)
