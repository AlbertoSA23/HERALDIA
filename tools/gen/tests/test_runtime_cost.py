"""tools/smoke/runtime_cost.py: pure functions of the play cost test (tick statistics, TickSampler's output, entity groups,
the fitted line and the margin, the combination of passes, the limits and the Markdown)."""
import os, sys
import pytest

SMOKE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "smoke")
sys.path.insert(0, SMOKE)
import runtime_cost as r  # noqa: E402


def test_tick_stats():
    assert r.tick_stats([]) == {"ticks": 0}
    ns = [10_000_000] * 98 + [60_000_000, 120_000_000]      # 98 ticks of 10 ms, one of 60 and one of 120
    st = r.tick_stats(ns, seconds=5)
    assert st["ticks"] == 100 and st["tps"] == 20
    assert st["p50"] == pytest.approx(10) and st["max"] == pytest.approx(120)
    assert st["media"] == pytest.approx((98 * 10 + 60 + 120) / 100)
    assert st["lentos"] == 2 and st["lentos_pct"] == pytest.approx(0.02)
    assert 10 < st["p99"] < 120


def test_parse_sampler():
    ticks, polls, lost = r.parse_sampler("Picked up JAVA_TOOL_OPTIONS: x\n12345\n678\n# polls 40 lost 1\n")
    assert ticks == [12345, 678] and polls == 40 and lost == 1
    assert r.parse_sampler("") == ([], 0, 0)


def test_group_counts():
    g = r.group_counts({"villager": 12, "iron_golem": 3, "zombie": 2, "skeleton": 1, "cow": 4, "item": 5, "wandering_trader": 1},
                       total=40, players=2)
    assert (g["aldeanos"], g["golems"], g["monstruos"], g["animales"], g["objetos"], g["comerciantes"]) == (12, 3, 3, 4, 5, 1)
    assert g["total"] == 38 and g["otros"] == 38 - 28
    assert r.group_counts({}, 0)["otros"] == 0
    assert not set(sum(r.GROUPS.values(), [])) - {t for t in sum(r.GROUPS.values(), [])}      # no duplicates across groups
    flat = sum(r.GROUPS.values(), [])
    assert len(flat) == len(set(flat))


def test_fit_and_margin():
    pts = [(10, 5.0), (60, 10.0), (110, 15.0)]          # 0.1 ms per villager, 4 ms with none
    a, b = r.fit(pts)
    assert a == pytest.approx(4) and b == pytest.approx(0.1)
    assert r.margin(pts, 50) == pytest.approx((50 - 5) / 0.1)        # from the village as it generates (the first point)
    assert r.margin(pts, 4.5) == 0                        # already over the target: no margin left
    assert r.fit([(10, 1), (10, 2)]) is None
    assert r.margin([(10, 5.0), (60, 5.0), (110, 4.0)], 50) is None      # it does not grow: the cost is not visible


def _pass(media, p95, p99, mx, ald=10):
    return {"mspt": {"media": media, "p50": media, "p95": p95, "p99": p99, "max": mx, "lentos_pct": 0, "tps": 20, "ticks": 1200},
            "entidades": {"aldeanos": ald, "golems": 2, "monstruos": 1, "animales": 3, "comerciantes": 0, "objetos": 0,
                          "otros": 0, "total": ald + 6}}


def test_combine_median_and_worst():
    c = r.combine([_pass(5, 8, 12, 30), _pass(6, 9, 14, 80), _pass(7, 10, 13, 40)])
    assert c["pasadas"] == 3
    assert c["mspt"]["media"] == 6 and c["mspt"]["p95"] == 9 and c["mspt"]["p99"] == 13
    assert c["mspt"]["max"] == 80                        # the worst tick of all the passes
    assert c["entidades"]["aldeanos"] == 10
    assert r.combine([]) is None


def _result(con, sin):
    return {"con": {sc: r.combine([p]) for sc, p in con.items()}, "sin": {sc: r.combine([p]) for sc, p in sin.items()}}


def test_compare_limits():
    sin = {sc: _pass(3, 5, 7, 20) for sc in r.SCENARIOS}
    ok, text = r.compare(_result({sc: _pass(3.5, 6, 8, 25) for sc in r.SCENARIOS}, sin))
    assert ok, text
    con = {sc: _pass(3.5, 6, 8, 25) for sc in r.SCENARIOS}
    con["aldea"] = _pass(20, 30, 60, 90)                  # over a tick at p99 and +25 ms at p95
    ok, text = r.compare(_result(con, sin))
    assert not ok and "aldea: p99" in text and "aldea: p95" in text
    # the limits of the reference win over the default ones
    ok, _ = r.compare(_result(con, sin), {"limites": {"mspt_p99_ms": 100, "p95_extra_ms": 30, "aldea_vs_vanilla": 10}})
    assert ok
    # scenarios without anything of Heraldia's (the control) do not count for the p95 extra
    con = {sc: _pass(3.5, 6, 8, 25) for sc in r.SCENARIOS}
    con["campo"] = _pass(3.5, 20, 30, 40)
    assert r.compare(_result(con, sin))[0] is True or "campo: p95" not in r.compare(_result(con, sin))[1]


def test_escalation_summary_and_markdown():
    steps = [{"mspt": {"media": 4 + 0.05 * n, "p50": 4, "p95": 6 + 0.1 * n, "p99": 8 + 0.1 * n, "max": 20},
              "entidades": {"aldeanos": 10 + n, "total": 30 + n}} for n in (0, 50, 100)]
    e = r.escalation_summary(steps)
    assert e["ms_por_aldeano_p95"] == pytest.approx(0.1)
    assert e["margen_p95_50ms"] == pytest.approx((50 - 6) / 0.1)
    assert r.escalation_summary([]) is None
    sin = {sc: _pass(3, 5, 7, 20) for sc in r.SCENARIOS}
    res = dict(_result(sin, sin), semilla="heraldia", vista=10, maquina="4 núcleos", pasadas=1, segundos=60, commit="abc",
               escalada=e)
    md = r.markdown(res, r.compare(res))
    assert "| aldea |" in md and "Margen" in md and "✅" in md
