from __future__ import annotations

import numpy as np
import pandas as pd

from process_phase4b_evidence import asof_strict, holm_from_tail_probs


def test_strict_asof_preserves_missing_day() -> None:
    source = pd.Series(
        [1.0, np.nan, 3.0],
        index=pd.to_datetime(["2026-01-01","2026-01-02","2026-01-03"]),
        name="news",
    )
    # Exact Jan-03 is prohibited, so Jan-02 is the causal source date. Because
    # Jan-02 is explicitly missing, the result must remain NaN rather than fall
    # back to Jan-01.
    out = asof_strict(pd.DatetimeIndex(pd.to_datetime(["2026-01-03"])), source)
    assert pd.isna(out.iloc[0]), out


def test_common_mask_excludes_any_missing_cell() -> None:
    idx = pd.to_datetime(["2026-01-05","2026-01-06","2026-01-07"])
    a = pd.DataFrame({"tone":[1.0,np.nan,1.0],"volume":[1.0,np.nan,1.0]},index=idx)
    b = pd.DataFrame({"tone":[1.0,1.0,1.0],"volume":[1.0,1.0,1.0]},index=idx)
    common = pd.Series(True,index=idx,dtype=bool)
    for x in [a,b]:
        common &= x.notna().all(axis=1)
    assert common.tolist() == [True,False,True], common.tolist()


def test_holm_step_down_stops_after_first_failure() -> None:
    h = holm_from_tail_probs({"a":0.01,"b":0.03,"c":0.20},0.05)
    assert h["reject"]["a"] is True, h
    assert h["reject"]["b"] is False, h
    assert h["reject"]["c"] is False, h


def main() -> int:
    test_strict_asof_preserves_missing_day()
    test_common_mask_excludes_any_missing_cell()
    test_holm_step_down_stops_after_first_failure()
    print("JNU_DATA_INTEGRITY_SELFTEST_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
