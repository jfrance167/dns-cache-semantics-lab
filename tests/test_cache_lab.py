"""Independent semantic expectations and parser/CLI boundary checks."""
import json
from pathlib import Path
# Used only for the fixed local CLI fixture; no shell or remote execution.
import subprocess  # nosec B404
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cache_lab as lab


def query(at=0, name="host.example.", kind="A"):
    return {"at_ms": at, "op": "query", "name": name, "type": kind}


def positive(at=0, ttl=2, name="host.example.", kind="A", records=None):
    return {**query(at, name, kind), "op": "store_rrset", "ttl_s": ttl,
            "records": records if records is not None else (["2001:db8::1"] if kind == "AAAA" else ["192.0.2.1"])}


def negative(at=0, kind="NODATA", rtype="A", name="host.example.", ttl=30, minimum=10):
    return {**query(at, name, rtype), "op": "store_negative", "kind": kind,
            "soa": {"owner": "example.", "ttl_s": ttl, "minimum_s": minimum}}


def failure(at=0, duration=5, name="host.example.", kind="A"):
    return {**query(at, name, kind), "op": "store_failure", "duration_s": duration}


def run(*events):
    return lab.replay({"version": 1, "events": list(events)})["timeline"]


class Semantics(unittest.TestCase):
    def test_exact_expiry_and_zero(self):
        rows = run(positive(), query(1999), query(2000), positive(2000, 0), query(2000))
        self.assertEqual(rows[1]["evidence"]["remaining_ms"], 1)
        self.assertEqual([r["decision"] for r in rows[2:]], ["needs_information", "uncached", "needs_information"])

    def test_refresh_and_zero_preserves_reusable(self):
        rows = run(positive(), positive(1000, 10, records=["192.0.2.2"]), positive(1000, 0), query(2000))
        self.assertEqual(rows[-1]["evidence"]["records"], ["192.0.2.2"])
        self.assertEqual(rows[-1]["evidence"]["expires_ms"], 11000)

    def test_cross_type_denial_preserved(self):
        rows = run(negative(), negative(rtype="AAAA"), positive(1000, 20), query(1000), query(1000, kind="AAAA"))
        self.assertEqual(rows[-2]["decision"], "positive")
        self.assertEqual(rows[-1]["decision"], "NODATA")
        self.assertEqual(rows[-1]["evidence"]["remaining_ms"], 9000)

    def test_nxdomain_exact_name_and_refresh(self):
        rows = run(negative(kind="NXDOMAIN", ttl=10, minimum=30), query(), query(kind="AAAA"),
                   query(name="child.host.example."), positive(1000), query(1000, kind="AAAA"))
        self.assertEqual([rows[i]["decision"] for i in (1, 2, 3, 5)],
                         ["NXDOMAIN", "NXDOMAIN", "needs_information", "needs_information"])
        self.assertEqual(rows[1]["evidence"]["expires_ms"], 10000)

    def test_missing_soa_and_negative_zero_do_not_change_cache(self):
        event = negative(kind="NXDOMAIN")
        del event["soa"]
        rows = run(positive(ttl=10), event, negative(ttl=0), query())
        self.assertEqual([r["decision"] for r in rows], ["stored", "uncached", "uncached", "positive"])

    def test_negative_replaces_matching_data(self):
        rows = run(positive(ttl=10), positive(ttl=10, kind="AAAA"), negative(), query(), query(kind="AAAA"))
        self.assertEqual(rows[-2]["decision"], "NODATA")
        self.assertEqual(rows[-1]["decision"], "positive")
        self.assertEqual(run(positive(), negative(kind="NXDOMAIN"), query())[-1]["decision"], "NXDOMAIN")

    def test_alias_and_terminal_lifetimes(self):
        alias = positive(kind="CNAME", records=["target.example."])
        rows = run(alias, positive(ttl=10, name="target.example."), query(1999), query(2000), query(2000, name="target.example."))
        self.assertEqual(rows[2]["hops"][0]["remaining_ms"], 1)
        self.assertEqual(rows[2]["evidence"]["remaining_ms"], 8001)
        self.assertEqual(rows[3]["decision"], "needs_information")
        self.assertEqual(rows[4]["decision"], "positive")
        alias["ttl_s"] = 10
        rows = run(alias, positive(name="target.example."), query(2000))
        self.assertEqual(rows[-1]["terminal"], "target.example.")
        self.assertEqual(rows[-1]["decision"], "needs_information")

    def test_terminal_denial_preserves_alias(self):
        rows = run(positive(ttl=10, kind="CNAME", records=["target.example."]),
                   negative(kind="NXDOMAIN", name="target.example."), query(), query(kind="CNAME"))
        self.assertEqual(rows[2]["terminal"], "target.example.")
        self.assertEqual(rows[2]["decision"], "NXDOMAIN")
        self.assertEqual(rows[3]["decision"], "positive")

    def test_alias_exclusivity_and_recovery(self):
        rows = run(negative(rtype="AAAA"), positive(kind="CNAME", records=["target.example."]),
                   failure(name="target.example."), query(), positive(name="target.example."), query())
        self.assertEqual(rows[3]["decision"], "suppressed_failure")
        self.assertEqual(rows[5]["decision"], "positive")
        rows = run(positive(kind="CNAME", records=["target.example."]), positive(), query(kind="CNAME"))
        self.assertEqual(rows[-1]["decision"], "needs_information")
        for event in (negative(), failure()):
            with self.assertRaises(lab.LabError):
                run(positive(kind="CNAME", records=["target.example."]), event)

    def test_failure_duration_type_and_expiry(self):
        rows = run(failure(), query(4999), query(4999, kind="AAAA"), query(5000))
        self.assertEqual([r["decision"] for r in rows[1:]], ["suppressed_failure", "needs_information", "needs_information"])
        for duration in (1, 300):
            self.assertEqual(run(failure(duration=duration), query(duration * 1000))[-1]["decision"], "needs_information")
        for duration in (0, 301):
            with self.assertRaises(lab.LabError):
                run(failure(duration=duration))

    def test_failure_recovery_independent(self):
        rows = run(failure(), failure(kind="AAAA"), positive(), query(), query(kind="AAAA"))
        self.assertEqual(rows[-2]["decision"], "positive")
        self.assertEqual(rows[-1]["decision"], "suppressed_failure")
        for useful in (positive(), negative(), negative(kind="NXDOMAIN")):
            with self.assertRaises(lab.LabError):
                run(useful, failure())

    def test_alias_refresh_preserves_terminal_failure(self):
        rows = run(failure(name="target.example."),
                   positive(kind="CNAME", records=["target.example."]), query())
        self.assertEqual(rows[-1]["decision"], "suppressed_failure")
        self.assertEqual(rows[-1]["terminal"], "target.example.")

    def test_expiry_removed_before_conflicts(self):
        rows = run(positive(), failure(at=2000), query(2000))
        self.assertEqual(rows[-1]["decision"], "suppressed_failure")
        rows = run(positive(kind="CNAME", records=["target.example."]), negative(at=2000), query(2000))
        self.assertEqual(rows[-1]["decision"], "NODATA")

    def test_alias_cycle_and_depth(self):
        rows = run(positive(kind="CNAME", records=["b.example."]),
                   positive(name="b.example.", kind="CNAME", records=["host.example."]), query())
        self.assertEqual(rows[-1]["decision"], "alias_cycle")
        chain = [positive(name=f"n{i}.example.", kind="CNAME", records=[f"n{i+1}.example."]) for i in range(8)]
        self.assertEqual(run(*chain, positive(name="n8.example."), query(name="n0.example."))[-1]["decision"], "positive")
        chain.append(positive(name="n8.example.", kind="CNAME", records=["n9.example."]))
        self.assertEqual(run(*chain, query(name="n0.example."))[-1]["decision"], "alias_depth")

    def test_same_time_order_determinism_and_no_network(self):
        self.assertEqual(run(query(), positive())[-2]["decision"], "needs_information")
        document = {"version": 1, "events": [positive(), query()]}
        with patch("socket.socket", side_effect=RuntimeError("network forbidden")), patch("socket.getaddrinfo", side_effect=RuntimeError("DNS forbidden")):
            first = lab.render(lab.replay(lab.load(json.dumps(document).encode())))
            self.assertEqual(first, lab.render(lab.replay(document)))

    def test_expired_eviction_and_combined_capacity(self):
        cache = lab.Cache()
        for i in range(256):
            cache.store(positive(name=f"n{i}.example."))
        with self.assertRaises(lab.LabError):
            cache.store(failure(name="extra.example."))
        cache.evict(2000)
        self.assertEqual(len(cache.entries), 0)
        cache.store(failure(at=2000, name="extra.example."))
        self.assertEqual(len(cache.entries), 1)


class Boundaries(unittest.TestCase):
    def test_json_rejections(self):
        for data in (b'{"version":1,"version":1,"events":[]}', b'{"version":NaN,"events":[]}',
                     b'{"version":1.0,"events":[]}', b'[' * 9 + b']' * 9,
                     b'{"version":1234567890123,"events":[]}', b'"' + b'a' * 255 + b'"',
                     b'"\\u001b"', b'"\\ud800"', b'\xff', b'\xef\xbb\xbf{}', b'{', b' ' * (lab.MAX_BYTES + 1)):
            with self.subTest(data=data[:40]), self.assertRaises(lab.LabError):
                lab.load(data)

    def test_schema_invalid(self):
        events = [query(), query(1), positive(), negative(), failure()]
        bad = []
        for change in ({"at_ms": True}, {"at_ms": -1}, {"at_ms": 86400001}, {"type": []},
                       {"type": "TXT"}, {"op": []}, {"extra": 1}, {"name": "public.com."}):
            bad.append({**query(), **change})
        bad.extend([positive(records=["10.0.0.1"]), positive(kind="AAAA", records=["2001:db8::1%eth0"]),
                    positive(records=["192.0.2.1"] * 2), positive(kind="CNAME", records=["a.example.", "b.example."]),
                    positive(ttl=True), positive(records=[]), positive(records=["192.0.2.1"] * 33),
                    positive(kind="AAAA", records=["2001:db8::1", "2001:0db8:0:0:0:0:0:1"]),
                    {**negative(), "soa": None}, {**negative(), "kind": []}])
        for event in bad:
            with self.subTest(event=event), self.assertRaises(lab.LabError):
                run(event)
        for root in ({"version": True, "events": []}, {"version": 1, "events": events * 60}):
            with self.assertRaises(lab.LabError):
                lab.replay(root)
        with self.assertRaises(lab.LabError):
            run(query(1), query(0))

    def test_name_and_soa_bounds(self):
        self.assertEqual(lab.name("HOST.EXAMPLE."), "host.example.")
        good = ".".join(["a" * 63] * 3 + ["b" * 53, "example", ""])
        self.assertEqual(len(good), 254)
        self.assertEqual(lab.name(good), good)
        for value in (good.replace("b" * 53, "b" * 54), "a" * 64 + ".example.", "-a.example.",
                      "a-.example.", "a..example.", "a.example", "é.example.", "a.example.\x1b"):
            with self.assertRaises(lab.LabError):
                lab.name(value)
        event = negative(name="notzone.example.")
        event["soa"]["owner"] = "zone.example."
        with self.assertRaises(lab.LabError):
            run(event)

    def test_render_budget_and_formats(self):
        result = lab.replay({"version": 1, "events": [positive(), query()]})
        self.assertIn(b"remaining=2000ms", lab.render(result, "text"))
        with patch.object(lab, "MAX_BYTES", 2), self.assertRaises(lab.LabError):
            lab.render(result)
        with self.assertRaises(lab.LabError):
            lab.render(result, "html")

    def test_cli_atomic_error_and_success(self):
        cli = str(Path(lab.__file__).resolve())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.json"
            for events, exit_code in (([positive(), query()], 0), ([positive(), failure()], 2), ([query(), query(-1)], 2)):
                path.write_text(json.dumps({"version": 1, "events": events}), encoding="utf-8")
                command = [sys.executable] + (["-O"] if sys.flags.optimize else []) + [cli, str(path)]
                # Fixed interpreter/script with a locally generated inert JSON fixture.
                result = subprocess.run(command, capture_output=True, timeout=10, check=False)  # nosec B603
                self.assertEqual(result.returncode, exit_code)
                if exit_code:
                    self.assertEqual(result.stdout, b"")
                    self.assertIn(b"cache-lab:", result.stderr)
                else:
                    self.assertEqual(json.loads(result.stdout)["timeline"][-1]["decision"], "positive")


if __name__ == "__main__":
    unittest.main()
