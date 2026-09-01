from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import LoggingConfig, StrategyConfig
from nautilus_trader.model.currencies import JPY
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import AccountType, AssetClass, OmsType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId, Symbol, TraderId, Venue
from nautilus_trader.model.instruments import PerpetualContract
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.trading.strategy import Strategy

ROOT=Path(__file__).resolve().parents[1]
PREREG=ROOT/"config"/"jnu_boj_mpm_stage5_nautilus_execution_replay_g1_prereg.json"
STAGE4=ROOT/"config"/"jnu_boj_mpm_stage4_new_entry_blackout_g1_prereg.json"
RESULT=ROOT/"stage5_results"/"jnu_boj_mpm_stage5_nautilus_execution_replay_g1.json"
REPORT=ROOT/"stage5_reports"/"jnu_boj_mpm_stage5_nautilus_execution_replay_g1.md"
JST=ZoneInfo("Asia/Tokyo")

def local_dt(date_s:str, hhmm:str)->datetime:
    return datetime.fromisoformat(f"{date_s}T{hhmm}:00").replace(tzinfo=JST)

def ns(dt:datetime)->int:
    return int(dt.timestamp()*1_000_000_000)

class ReplayConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal

class IndependentBlackoutStrategy(Strategy):
    def __init__(self, config:ReplayConfig, scenario:dict, date_s:str):
        super().__init__(config)
        self.scenario=scenario
        self.date_s=date_s
        self.intent_map={hhmm:int(target) for hhmm,target in scenario.get("intents",[])}
        self.pending_limit_client_id=None
        self.actions=[]

    def on_start(self)->None:
        self.subscribe_bars(self.config.bar_type)

    def _current(self)->int:
        return int(self.portfolio.net_position(self.config.instrument_id))

    def _blackout(self, local:datetime)->bool:
        if not bool(self.scenario.get("scheduled")):
            return False
        start=local_dt(self.date_s,"11:00")
        release=self.scenario.get("release")
        session_close=local_dt(self.date_s,"15:45")
        end=session_close if release is None else min(local_dt(self.date_s,release)+timedelta(minutes=20),session_close)
        return start <= local < end

    def _effective_target(self,current:int,target:int,blocked:bool)->int:
        if not blocked:
            return target
        if target==current:
            return target
        if current==0:
            return 0
        if target==0:
            return 0
        if current*target>0:
            return current if abs(target)>abs(current) else target
        return 0

    def _market_delta(self,delta:int)->None:
        if delta==0:
            return
        inst=self.cache.instrument(self.config.instrument_id)
        order=self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY if delta>0 else OrderSide.SELL,
            quantity=inst.make_qty(abs(delta)),
        )
        self.submit_order(order)

    def _submit_resting_limit(self)->None:
        inst=self.cache.instrument(self.config.instrument_id)
        order=self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=inst.make_qty(1),
            price=inst.make_price(90.0),
            time_in_force=TimeInForce.GTC,
        )
        self.pending_limit_client_id=order.client_order_id
        self.submit_order(order)
        self.actions.append({"action":"SUBMIT_RESTING_LIMIT","client_order_id":str(order.client_order_id)})

    def on_bar(self,bar:Bar)->None:
        local=datetime.fromtimestamp(int(bar.ts_event)/1_000_000_000,tz=ZoneInfo("UTC")).astimezone(JST)
        hhmm=local.strftime("%H:%M")

        if self.scenario.get("special_limit_entry")==hhmm:
            self._submit_resting_limit()

        if hhmm=="11:00" and self.pending_limit_client_id is not None and bool(self.scenario.get("scheduled")):
            self.cancel_order(self.pending_limit_client_id)
            self.actions.append({"action":"CANCEL_RESTING_ENTRY","client_order_id":str(self.pending_limit_client_id)})

        if hhmm not in self.intent_map:
            return
        current=self._current()
        base_target=self.intent_map[hhmm]
        blocked=self._blackout(local)
        effective=self._effective_target(current,base_target,blocked)
        self.actions.append({
            "time":hhmm,"current":current,"base_target":base_target,
            "blocked":blocked,"effective_target":effective
        })
        self._market_delta(effective-current)
def make_instrument():
    iid=InstrumentId.from_str("JNU-STAGE5.SIM")
    inst=PerpetualContract(
        instrument_id=iid,
        raw_symbol=Symbol("JNU-STAGE5"),
        underlying="NIKKEI225",
        asset_class=AssetClass.INDEX,
        quote_currency=JPY,
        settlement_currency=JPY,
        is_inverse=False,
        price_precision=2,
        size_precision=0,
        price_increment=Price.from_str("0.01"),
        size_increment=Quantity.from_int(1),
        multiplier=Quantity.from_int(1),
        lot_size=Quantity.from_int(1),
        margin_init=Decimal("0.10"),
        margin_maint=Decimal("0.05"),
        maker_fee=Decimal("0"),
        taker_fee=Decimal("0"),
        ts_event=0,
        ts_init=0,
    )
    return iid,inst

def bar_times(scenario:dict)->list[str]:
    base={"08:50","10:58","10:59","11:00","11:01","11:30","12:00","12:22","12:23","12:42","12:43","15:44","15:45"}
    for hhmm,_ in scenario.get("intents",[]): base.add(hhmm)
    if scenario.get("special_limit_entry"): base.add(scenario["special_limit_entry"])
    if scenario.get("release"): base.add(scenario["release"])
    return sorted(base)

def run_scenario(scenario:dict,index:int)->dict:
    date_s=(datetime(2026,1,5,tzinfo=JST)+timedelta(days=index*2)).date().isoformat()
    iid,inst=make_instrument()
    bar_type=BarType.from_str("JNU-STAGE5.SIM-1-MINUTE-LAST-EXTERNAL")
    bars=[]
    for hhmm in bar_times(scenario):
        t=local_dt(date_s,hhmm)
        bars.append(Bar(
            bar_type=bar_type,
            open=Price.from_str("100.00"), high=Price.from_str("100.00"),
            low=Price.from_str("100.00"), close=Price.from_str("100.00"),
            volume=Quantity.from_int(100), ts_event=ns(t), ts_init=ns(t)
        ))

    engine=BacktestEngine(BacktestEngineConfig(
        trader_id=TraderId(f"JNU-STAGE5-{index:02d}"),
        logging=LoggingConfig(log_level="ERROR"),
    ))
    engine.add_venue(
        venue=Venue("SIM"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
        base_currency=JPY, starting_balances=[Money(100_000_000,JPY)],
        default_leverage=Decimal(1),
    )
    engine.add_instrument(inst)
    engine.add_data(bars)
    strat=IndependentBlackoutStrategy(
        ReplayConfig(instrument_id=iid,bar_type=bar_type,trade_size=Decimal("1")),
        scenario,date_s
    )
    engine.add_strategy(strat)
    engine.run()

    fills=engine.trader.generate_fills_report()
    orders=engine.trader.generate_orders_report()
    final_position=int(strat.portfolio.net_position(iid))
    statuses=[]
    if len(orders) and "status" in orders.columns:
        statuses=[str(x).upper() for x in orders["status"].tolist()]
    canceled=sum(("CANCEL" in x) for x in statuses)
    actual_fills=int(len(fills))

    expected_fills=int(scenario["expected_fills"])
    expected_final=int(scenario["expected_final_position"])
    checks={
        "fill_count_match":actual_fills==expected_fills,
        "final_position_match":final_position==expected_final,
    }
    if "expected_canceled_orders" in scenario:
        checks["canceled_order_count_match"]=canceled==int(scenario["expected_canceled_orders"])
    passed=all(checks.values())
    out={
        "scenario_id":scenario["id"],"pass":passed,"checks":checks,
        "expected_fills":expected_fills,"actual_fills":actual_fills,
        "expected_final_position":expected_final,"actual_final_position":final_position,
        "order_statuses":statuses,"canceled_orders":canceled,
        "actions":strat.actions,
    }
    engine.dispose()
    return out

def main()->None:
    prereg=json.loads(PREREG.read_text(encoding="utf-8"))
    stage4=json.loads(STAGE4.read_text(encoding="utf-8"))
    assert prereg["status"]=="PREREGISTERED_BEFORE_NAUTILUS_REPLAY"
    assert prereg["parent_stage4"]==stage4["candidate_id"]
    assert prereg["inputs"]["real_jnu_prices_used"] is False
    assert prereg["inputs"]["real_pnl_used"] is False

    results=[run_scenario(s,i) for i,s in enumerate(prereg["scenarios"])]
    all_pass=all(x["pass"] for x in results)
    result={
      "candidate_id":prereg["candidate_id"],
      "status":"PASS_STAGE5_INDEPENDENT_EXECUTION_REPLAY" if all_pass else "FAIL_STAGE5_INDEPENDENT_EXECUTION_REPLAY",
      "promotion_pipeline_stage":5,
      "engine":prereg["engine"],
      "independent_code_path":True,
      "imports_stage4_selftest":False,
      "real_jnu_prices_used":False,
      "real_pnl_used":False,
      "scenario_count":len(results),
      "passed_scenarios":sum(x["pass"] for x in results),
      "scenarios":results,
      "alpha_or_utility_evidence":False,
      "live_use":False,
      "promotion_ceiling":prereg["promotion_ceiling"],
      "next_rule":"Stage-5 PASS confirms mechanical replay only. Do not run Stage 6/7 economic validation until a validated base-entry process and downstream protocol exist."
    }
    RESULT.parent.mkdir(exist_ok=True)
    REPORT.parent.mkdir(exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
      "# BOJ MPM Stage-5 Nautilus independent execution replay G1","",
      f"- Status: **{result['status']}**",
      f"- Scenarios: **{result['passed_scenarios']}/{result['scenario_count']}**",
      "- Engine: NautilusTrader 1.231.0",
      "- Real JNU prices used: **false**",
      "- PnL/alpha/utility evaluated: **false**",
      "- Live use: **false**","",
      "| Scenario | PASS | Fills exp/actual | Position exp/actual | Canceled |",
      "|---|---:|---:|---:|---:|",
    ]
    for x in results:
        lines.append(f"| {x['scenario_id']} | {x['pass']} | {x['expected_fills']}/{x['actual_fills']} | {x['expected_final_position']}/{x['actual_final_position']} | {x['canceled_orders']} |")
    lines += ["","Stage-5 PASS, if achieved, is execution/mechanical validation only and is not evidence of alpha or economic risk reduction.",""]
    REPORT.write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if all_pass else 1)

if __name__=="__main__":
    main()
