import os, sys, unittest
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
from sizer import core, optimize

S = core.load_site("reno_nv")


class T(unittest.TestCase):
    def test_data_gap_days_dropped(self):
        self.assertEqual(S["gap_days"], 12)
        self.assertEqual(len(S["P"]), len(S["year"]))

    def test_extremes(self):
        L = core.load_profile(S, "flat", 50)
        none = core.simulate(S, L, [0.0], [0.0], [0.0], 0, [2006])
        huge = core.simulate(S, L, [2000.0], [20000.0], [0.0], 0, [2006])
        self.assertEqual(none["served"][0, 0], 0.0)
        self.assertGreater(huge["served"][0, 0], 0.999)

    def test_generator_fuel_cap(self):
        L = core.load_profile(S, "flat", 50)
        r = core.simulate(S, L, [10.0], [10.0], [30.0], 500.0, [2006, 2007])
        max_hour = 0.246 * 30 + 0.08415 * 30
        self.assertTrue(np.all(r["fuel"][0] <= 500.0 + max_hour + 1e-9))

    def test_rule_of_thumb(self):
        L = core.load_profile(S, "flat", 50)
        kwp, bat, gen = core.rule_of_thumb(S, L, range(2005, 2011), 50)
        daily = L[np.isin(S["year"], range(2005, 2011))].mean() * 24
        self.assertGreaterEqual(bat * (1 - core.SOC_MIN), daily)
        self.assertEqual(gen, 25.0)
        self.assertAlmostEqual(kwp % core.BLOCK_KW, 0.0, places=6) if kwp % core.BLOCK_KW < 0.2 else None

    def test_two_shift_weekends_low(self):
        L = core.load_profile(S, "two_shift", 100)
        self.assertLess(np.median(L), 60)
        self.assertGreater(L.max(), 100)

    def test_optimizer_meets_target_in_sizing_years(self):
        L = core.load_profile(S, "camp", 30)
        o = optimize.size(S, L, range(2005, 2008), 30)
        self.assertTrue(o["met_in_sizing"])
        chk = optimize.check(S, L, o, range(2005, 2008))
        self.assertGreaterEqual(chk["worst"], optimize.TARGET - 1e-9)


if __name__ == "__main__":
    unittest.main()
