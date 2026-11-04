import json
import os
import re
import unittest

from _load import ROOT

SKILLS = ["bazaar-scanner", "bazaar-news", "bazaar-entry", "bazaar-exit", "bazaar-timemachine",
          "bazaar-risk", "bazaar-budget", "bazaar-broker", "bazaar-alerts", "bazaar-analyst",
          "bazaar-smartmoney"]
ABOUT = ("11 Claude skills for Indian day trading on NSE/BSE: scan EQ charts in IST, track NSE "
         "announcements, time entries and exits, replay outcomes with honest fills, and keep "
         "paper-only until you type yes.")
ORDER_PATH = ["bazaar-scanner", "bazaar-entry", "bazaar-exit", "bazaar-timemachine", "bazaar-budget",
              "bazaar-smartmoney", "bazaar-risk", "bazaar-broker", "bazaar-alerts"]


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1) if m else ""), text


class Repo(unittest.TestCase):
    def test_eleven_skill_folders(self):
        found = sorted(d for d in os.listdir(ROOT)
                       if os.path.isfile(os.path.join(ROOT, d, "SKILL.md")))
        self.assertEqual(found, sorted(SKILLS))

    def test_frontmatter_name_and_description(self):
        for s in SKILLS:
            fm, text = frontmatter(os.path.join(ROOT, s, "SKILL.md"))
            self.assertIn("name: %s\n" % s, fm + "\n", s)
            self.assertGreater(len(fm), 200, s)
            self.assertGreater(len(text.splitlines()), 60, s)

    def test_order_path_skills_carry_the_safety_rule(self):
        for s in ORDER_PATH:
            _, text = frontmatter(os.path.join(ROOT, s, "SKILL.md"))
            low = " ".join(text.lower().split())
            self.assertIn("not financial advice", low, s)
            self.assertIn("yes", low, s)

    def test_plugin_manifest(self):
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json")) as fh:
            plugin = json.load(fh)
        self.assertEqual(plugin["name"], "bazaar-trader-skill")
        self.assertEqual(plugin["skills"], "./")
        self.assertEqual(plugin["description"], ABOUT)

    def test_readme_maps_all_eleven(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertTrue(readme.startswith("# The Bazaar Trader skill"))
        for s in SKILLS:
            self.assertIn("/" + s, readme, s)
        self.assertIn("09:15", readme)
        self.assertIn("paper", readme)
        self.assertIn("bulk", readme.lower())
        self.assertIn("https://github.com/raiaashish-code/bazaar-trader-skill", readme)
        self.assertIn("/plugin marketplace add raiaashish-code/bazaar-trader-skill", readme)
        self.assertIn("install skill", readme)

    def test_paper_trading_is_the_default(self):
        with open(os.path.join(ROOT, "bazaar-budget", "config.example.json")) as fh:
            cfg = json.load(fh)
        self.assertIs(cfg["paper"], True)
        self.assertIs(cfg["live_trading"], False)
        self.assertEqual(cfg["broker"], "paper")
        self.assertIs(cfg["require_stop"], True)
        for k in ("max_loss_per_trade_inr", "max_daily_loss_inr", "max_trades_per_day",
                  "min_reward_risk", "no_entries_after", "flat_by"):
            self.assertIn(k, cfg, k)

    def test_pack_is_generic_not_a_desk_fork(self):
        banned = ("dhan", "nazar", "dhanalgo", "combo d1", "runtime_config")
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for f in files:
                if not f.endswith((".md", ".py", ".json")):
                    continue
                path = os.path.join(base, f)
                rel = os.path.relpath(path, ROOT)
                if rel.startswith("tests" + os.sep):
                    continue
                with open(path, encoding="utf-8") as fh:
                    low = fh.read().lower()
                for word in banned:
                    self.assertNotIn(word, low, rel)

    def test_no_live_enable_in_pack(self):
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for f in files:
                if not f.endswith((".md", ".py", ".json")):
                    continue
                path = os.path.join(base, f)
                rel = os.path.relpath(path, ROOT)
                if rel.startswith("tests" + os.sep):
                    continue
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                self.assertNotIn("place_live_order", text, path)


if __name__ == "__main__":
    unittest.main()
