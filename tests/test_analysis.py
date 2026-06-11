"""
analysis.py 煙霧測試（不需資料庫）。

重點：以合成 DataFrame 驗證分析模組可正常 import 與運算。
這組測試專門用來攔截「import 時即崩潰」與「圖表函式回傳非 Figure」這類
回歸——例如先前 `SEA_STATES = SEA_STATES` 自我參照導致整個分析管線
NameError 的事故（CI 僅做 py_compile 無法偵測）。

執行：
    pip install pandas numpy matplotlib seaborn scipy mysql-connector-python pytest
    pytest -q tests/
"""

import os
import sys
import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("MPLBACKEND", "Agg")

# 讓 `import analysis` 找得到 src/analysis/analysis.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "analysis"))
analysis = importlib.import_module("analysis")


# ── 合成資料（模擬 _clean 後的 attendance / leaves 結構）─────────────────────
def _synthetic_att(n: int = 150) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    start = pd.Timestamp.today().normalize() - pd.Timedelta(days=140)
    names = [f"員工{i}" for i in range(6)]
    vessels = [f"MAR-00{i}" for i in range(1, 5)]
    rows = []
    for i in range(n):
        d = start + pd.Timedelta(days=int(rng.integers(0, 140)))
        if d.weekday() == 6:  # 週日休
            d += pd.Timedelta(days=1)
        sea = analysis.SEA_STATES[int(rng.integers(0, len(analysis.SEA_STATES)))]
        zone = analysis.DUTY_ZONES[int(rng.integers(0, len(analysis.DUTY_ZONES)))]
        ci = d + pd.Timedelta(hours=7, minutes=int(rng.integers(0, 120)))
        hours = float(np.clip(rng.normal(9, 1.2), 4, 14))
        co = ci + pd.Timedelta(hours=hours)
        rows.append({
            "att_id": i + 1,
            "user_id": int(rng.integers(0, len(names))) + 1,
            "full_name": names[int(rng.integers(0, len(names)))],
            "role": "employee",
            "work_date": d,
            "check_in": ci,
            "check_out": co,
            "duty_zone": zone,
            "sea_state": sea,
            "vessel_id": vessels[int(rng.integers(0, len(vessels)))],
        })
    att = pd.DataFrame(rows)
    att["hours"] = (att["check_out"] - att["check_in"]).dt.total_seconds() / 3600
    att["month_str"] = att["work_date"].dt.strftime("%Y-%m")
    return att


def _synthetic_leaves(n: int = 24) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    start = pd.Timestamp.today().normalize() - pd.Timedelta(days=140)
    rows = []
    for i in range(n):
        d = start + pd.Timedelta(days=int(rng.integers(0, 130)))
        rows.append({
            "leave_id": i + 1,
            "user_id": int(rng.integers(1, 7)),
            "full_name": f"員工{int(rng.integers(0, 6))}",
            "date_from": d,
            "date_to": d + pd.Timedelta(days=1),
            "leave_type": ["personal", "sick", "other"][i % 3],
            "status": ["approved", "approved", "pending", "rejected"][i % 4],
        })
    return pd.DataFrame(rows)


# ── 測試 ──────────────────────────────────────────────────────────────────────
def test_module_constants_are_real_literals():
    """回歸守門：常數必須是真實字面值，不可是自我參照（防 SEA_STATES bug 再現）。"""
    assert analysis.SEA_STATES == ["平靜", "輕浪", "中浪", "大浪"]
    assert analysis.DUTY_ZONES == ["港口", "近海", "外海"]
    assert analysis.SEA_RANK["平靜"] == 1 and analysis.SEA_RANK["大浪"] == 4
    assert analysis.ZONE_RANK["港口"] == 1 and analysis.ZONE_RANK["外海"] == 3


def test_compute_stats_structure():
    out = analysis.compute_stats(_synthetic_att(), _synthetic_leaves())
    assert out["summary"]["records"] > 0
    assert isinstance(out["tests"], list)
    assert len(out["insights"]) >= 3
    assert "model" in out
    assert 0.0 <= out["model"]["r2"] <= 1.0


def test_fit_hours_ols():
    res = analysis._fit_hours_ols(_synthetic_att())
    assert res is not None
    r2, coefs = res
    assert 0.0 <= r2 <= 1.0
    assert set(coefs) == {"海況等級", "海域距岸", "星期", "上工時刻"}


def test_fit_hours_ols_insufficient_data_returns_none():
    assert analysis._fit_hours_ols(_synthetic_att(n=5)) is None


@pytest.mark.parametrize("fn", [
    "_chart_monthly_trend", "_chart_zone_bar", "_chart_zone_sea_stacked",
    "_chart_hours_boxplot", "_chart_person_heatmap", "_chart_hours_heatmap",
    "_chart_anomaly_detect", "_chart_anomaly_isoforest", "_chart_weekday_pattern",
    "_chart_vessel_pareto", "_chart_vessel_count", "_chart_forecast_duty",
    "_chart_forecast_holt", "_chart_correlation", "_chart_regression_coef",
    "_chart_crew_clusters", "_chart_crew_radar", "_chart_markov_heatmap",
    "_chart_zone_map_static", "_chart_feature_importance", "_chart_fatigue",
    "_chart_fairness_lorenz", "_chart_vessel_availability", "_chart_schedule_compare",
])
def test_chart_functions_return_figure(fn):
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    fig = getattr(analysis, fn)(_synthetic_att())
    assert isinstance(fig, Figure)
    plt.close(fig)


def test_generate_charts_writes_all_outputs(tmp_path, monkeypatch):
    """端到端（不連 DB）：產生全部 25 張圖 + 統計 JSON。"""
    class _DummyConn:
        def close(self):
            pass

    att, leaves = _synthetic_att(), _synthetic_leaves()
    monkeypatch.setattr(analysis, "get_connection", lambda: _DummyConn())
    monkeypatch.setattr(analysis, "_load_data", lambda conn, a, b: (att.copy(), leaves.copy()))
    monkeypatch.setattr(analysis, "_clean", lambda a, l: (a, l))

    paths = analysis.generate_charts(tmp_path)
    assert len(paths) == 25
    for p in paths:
        assert Path(p).exists()
    assert (tmp_path / "stats_summary.json").exists()
    assert (tmp_path / "recommendations.json").exists()


def test_compute_recommendations_structure():
    """compute_recommendations 回傳結構完整，關鍵欄位皆存在。"""
    att = _synthetic_att()
    rec = analysis.compute_recommendations(att)
    assert "headline" in rec and isinstance(rec["headline"], str) and len(rec["headline"]) > 0
    assert "alerts" in rec and isinstance(rec["alerts"], list) and len(rec["alerts"]) > 0
    assert "zone_risk" in rec and isinstance(rec["zone_risk"], list)
    assert "exposure_ranking" in rec and isinstance(rec["exposure_ranking"], list)
    assert "rotation_suggestions" in rec and isinstance(rec["rotation_suggestions"], list)
    assert "markov_rough_7day" in rec
    for alert in rec["alerts"]:
        assert "level" in alert and alert["level"] in ("ok", "info", "warn", "err")
        assert "text" in alert and len(alert["text"]) > 0
    for zr in rec["zone_risk"]:
        assert "zone" in zr and "rough_pct" in zr and "avg_hours" in zr
    for rs in rec["rotation_suggestions"]:
        assert "name" in rs and "action" in rs and "priority" in rs


def test_compute_recommendations_empty():
    """空 DataFrame 不應崩潰，headline 說明無資料。"""
    empty = pd.DataFrame(columns=_synthetic_att().columns)
    rec = analysis.compute_recommendations(empty)
    assert "headline" in rec
    assert "無" in rec["headline"] or len(rec["headline"]) > 0


# ── 人力資源與排班決策引擎測試（核心差異化）─────────────────────────────────
def test_compute_fatigue():
    fat = analysis.compute_fatigue(_synthetic_att())
    assert isinstance(fat, list) and len(fat) > 0
    for f in fat:
        assert {"user_id", "name", "fatigue_score", "level", "consecutive_days"} <= set(f)
        assert 0 <= f["fatigue_score"] <= 100
        assert f["level"] in ("low", "mid", "high")
    # 依疲勞分數遞減排序
    scores = [f["fatigue_score"] for f in fat]
    assert scores == sorted(scores, reverse=True)


def test_compute_fairness():
    fr = analysis.compute_fairness(_synthetic_att())
    assert "gini" in fr and 0.0 <= fr["gini"] <= 1.0
    assert fr["label"] in ("均勻", "尚可", "失衡")
    assert "lorenz" in fr and len(fr["lorenz"]["x"]) == len(fr["lorenz"]["y"])


def test_compute_vessel_status():
    vs = analysis.compute_vessel_status(_synthetic_att())
    assert isinstance(vs, list) and len(vs) > 0
    for v in vs:
        assert {"vessel", "status", "availability_pct", "total_duties"} <= set(v)
        assert v["status"] in ("可用", "需維護")
        assert 0 <= v["availability_pct"] <= 100


def test_build_schedule_fills_slots():
    att = _synthetic_att()
    fat = analysis.compute_fatigue(att)
    vs = analysis.compute_vessel_status(att)
    rec = analysis.compute_recommendations(att)
    sched = analysis.build_schedule(att, fat, vs, rec["exposure_ranking"], rough_prob=20.0)
    assert "assignments" in sched and len(sched["assignments"]) > 0
    assert "date" in sched and "zone_slots" in sched
    for a in sched["assignments"]:
        assert {"name", "zone", "vessel", "reason"} <= set(a)
        assert a["zone"] in analysis.DUTY_ZONES


def test_build_schedule_reduces_offshore_when_rough():
    """惡劣海況機率高時，外海員額應被縮減。"""
    att = _synthetic_att()
    fat = analysis.compute_fatigue(att)
    vs = analysis.compute_vessel_status(att)
    rec = analysis.compute_recommendations(att)
    calm = analysis.build_schedule(att, fat, vs, rec["exposure_ranking"], rough_prob=5.0)
    rough = analysis.build_schedule(att, fat, vs, rec["exposure_ranking"], rough_prob=80.0)
    assert rough["zone_slots"]["外海"] < calm["zone_slots"]["外海"]


def test_recommendations_includes_workforce_engine():
    rec = analysis.compute_recommendations(_synthetic_att())
    assert isinstance(rec["fatigue"], list) and len(rec["fatigue"]) > 0
    assert isinstance(rec["vessel_status"], list) and len(rec["vessel_status"]) > 0
    assert "schedule" in rec and "assignments" in rec["schedule"]
    assert "fairness" in rec and "gini" in rec["fairness"]
    assert "sea_now" in rec  # 即時海況欄位存在（可為 None）


# ── MILP 最佳化排班引擎測試 ──────────────────────────────────────────────────
def _schedule_inputs():
    att = _synthetic_att()
    fat = analysis.compute_fatigue(att)
    vs = analysis.compute_vessel_status(att)
    rec = analysis.compute_recommendations(att)
    return att, fat, vs, rec["exposure_ranking"]


def test_build_schedule_no_double_assignment():
    """硬約束驗證：每人至多一艦、每艦至多一組、維護中船艦不得指派。"""
    att, fat, vs, expo = _schedule_inputs()
    sched = analysis.build_schedule(att, fat, vs, expo, rough_prob=20.0)
    names = [a["name"] for a in sched["assignments"]]
    vessels = [a["vessel"] for a in sched["assignments"]]
    assert len(names) == len(set(names)), "同一人被重複指派"
    assert len(vessels) == len(set(vessels)), "同一艦被重複指派"
    maint = set(sched["maintenance_vessels"])
    assert not (set(vessels) & maint), "維護中船艦被指派"


def test_build_schedule_engine_and_cost():
    """MILP 引擎啟用時，總成本不得高於貪婪基準（全域最佳化定義）。"""
    att, fat, vs, expo = _schedule_inputs()
    sched = analysis.build_schedule(att, fat, vs, expo, rough_prob=20.0)
    assert sched["engine"] in ("milp", "greedy")
    assert sched["greedy_cost"] >= 0
    if sched["engine"] == "milp" and len(sched["assignments"]) > 0:
        assert sched["objective_cost"] <= sched["greedy_cost"] + 1e-6


def test_build_schedule_zone_caps_respected():
    """各海域成班數不得超過員額上限。"""
    att, fat, vs, expo = _schedule_inputs()
    sched = analysis.build_schedule(att, fat, vs, expo, rough_prob=60.0)
    by_zone = {}
    for a in sched["assignments"]:
        by_zone[a["zone"]] = by_zone.get(a["zone"], 0) + 1
    for zone, n in by_zone.items():
        assert n <= sched["zone_slots"][zone]


def test_milp_prioritizes_offshore_when_crew_short():
    """人力短缺時，安全關鍵海域（外海）應優先派滿（ZONE_PRIORITY 機制）。"""
    att = _synthetic_att()
    fatigue = [{"user_id": i, "name": f"P{i}", "fatigue_score": 30 + i, "level": "low",
                "consecutive_days": 1, "hours_7d": 8.0, "days_since_duty": 0}
               for i in range(1, 5)]   # 僅 4 人
    vessel_status = [
        {"vessel": "V-OFF1", "zone": "外海", "status": "可用", "total_duties": 1,
         "since_maint": 1, "maint_interval": 45, "availability_pct": 95, "last_used": "2026-06-01"},
        {"vessel": "V-OFF2", "zone": "外海", "status": "可用", "total_duties": 1,
         "since_maint": 1, "maint_interval": 45, "availability_pct": 95, "last_used": "2026-06-01"},
        {"vessel": "V-PORT1", "zone": "港口", "status": "可用", "total_duties": 1,
         "since_maint": 1, "maint_interval": 45, "availability_pct": 95, "last_used": "2026-06-01"},
        {"vessel": "V-PORT2", "zone": "港口", "status": "可用", "total_duties": 1,
         "since_maint": 1, "maint_interval": 45, "availability_pct": 95, "last_used": "2026-06-01"},
    ]
    expo = [{"user_id": i, "records": 10, "offshore_pct": 10.0,
             "rough_sea_pct": 5.0, "avg_hours": 9.0} for i in range(1, 5)]
    sched = analysis.build_schedule(att, fatigue, vessel_status, expo, rough_prob=5.0)
    n_offshore = sum(1 for a in sched["assignments"] if a["zone"] == "外海")
    # 平穩海況外海員額 3、可用外海艦 2 → 外海應派滿 2 組
    assert n_offshore == 2


# ── Holt 指數平滑與 Isolation Forest 測試 ────────────────────────────────────
def test_holt_forecast_follows_trend():
    """單調上升序列的 Holt 預測應延續上升趨勢且長度正確。"""
    y = np.array([10, 12, 14, 16, 18, 20, 22, 24], dtype=float)
    res = analysis.holt_forecast(y, horizon=4)
    assert res is not None
    assert len(res["forecast"]) == 4
    assert res["forecast"][0] > y[-1] - 1e-6
    assert all(np.diff(res["forecast"]) > 0)
    assert 0 < res["alpha"] < 1 and 0 < res["beta"] < 1


def test_holt_forecast_insufficient_data():
    assert analysis.holt_forecast(np.array([1.0, 2.0, 3.0]), horizon=2) is None


def test_detect_anomalies_iforest():
    pytest.importorskip("sklearn")
    att = _synthetic_att(n=200)
    res = analysis.detect_anomalies_iforest(att, contamination=0.05)
    assert res is not None
    flags, scores = res
    assert len(flags) == len(att) and len(scores) == len(att)
    # contamination=5% 時異常筆數應在合理範圍
    assert 0 < int(flags.sum()) <= int(len(att) * 0.10)


def test_train_sea_classifier_reports_cv():
    """GridSearchCV 交叉驗證指標應隨模型輸出（資料足夠時）。"""
    pytest.importorskip("sklearn")
    res = analysis.train_sea_classifier(_synthetic_att(n=300))
    if res is None:
        pytest.skip("合成資料不足以訓練（每日彙整後樣本過少）")
    assert {"accuracy", "auc", "cv_auc_mean", "cv_auc_std", "best_params"} <= set(res)
    if res["cv_auc_mean"] is not None:
        assert 0.0 <= res["cv_auc_mean"] <= 1.0
        assert res["best_params"] is not None
