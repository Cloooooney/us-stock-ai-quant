from __future__ import annotations

import json

from data_pipeline.build_sec_annual_features import main as rebuild_fundamentals
from data_pipeline.incremental_sec_update import update as update_sec
from data_pipeline.rebuild_monthly_dataset import rebuild as rebuild_monthly
from data_pipeline.update_market_data import update as update_market
from paper_trading.run_v5_forward import main as run_forward


def main():
    market = update_market()
    sec = update_sec()
    rebuild_fundamentals()
    monthly = rebuild_monthly()
    print(json.dumps({"market": market, "sec": sec, "monthly": monthly}, indent=2))
    run_forward()


if __name__ == "__main__": main()
