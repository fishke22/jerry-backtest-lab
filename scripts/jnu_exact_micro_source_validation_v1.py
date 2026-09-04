from __future__ import annotations
import re

TV_SYMBOL_RE=re.compile(r"^NK225MC[A-Z][0-9]{4}$")
JPX_CODE_RE=re.compile(r"^115\.[0-9]{4}/O$")
JPX_MONTH_RE=re.compile(r"^[A-Z][a-z]{2}\.[0-9]{4}$")

def validate_reference_source_metadata(meta:dict, reference_price:float, reference_timestamp:str)->str:
    if not isinstance(meta,dict):
        raise RuntimeError("reference source metadata missing")
    if meta.get("exact_product") is not True or meta.get("continuous_contract") is not False:
        raise RuntimeError("reference source product identity invalid")
    if meta.get("freshness_pass") is not True:
        raise RuntimeError("reference source freshness flag invalid")
    age=float(meta.get("freshness_age_seconds"))
    if age<0 or age>900:
        raise RuntimeError("reference source age invalid")
    if abs(float(meta.get("price"))-float(reference_price))>1e-12:
        raise RuntimeError("reference source price mismatch")
    if str(meta.get("source_timestamp"))!=str(reference_timestamp):
        raise RuntimeError("reference source timestamp mismatch")
    sid=str(meta.get("source_id",""))
    if sid=="OSE":
        if not TV_SYMBOL_RE.fullmatch(str(meta.get("symbol",""))):
            raise RuntimeError("TradingView primary source contract invalid")
        if str(meta.get("product",""))!="Nikkei 225 micro Futures":
            raise RuntimeError("TradingView primary source product invalid")
        return "TRADINGVIEW_OSE_EXACT_MICRO_B"
    if sid=="JPX_OSE_OFFICIAL":
        if meta.get("official_exchange_source") is not True:
            raise RuntimeError("JPX official-source flag missing")
        if str(meta.get("product",""))!="Nikkei 225 micro Futures":
            raise RuntimeError("JPX primary source product invalid")
        if not JPX_CODE_RE.fullmatch(str(meta.get("contract_code",""))):
            raise RuntimeError("JPX primary source contract code invalid")
        if not JPX_MONTH_RE.fullmatch(str(meta.get("contract_month",""))):
            raise RuntimeError("JPX primary source contract month invalid")
        return "JPX_OSE_OFFICIAL_EXACT_MICRO_A"
    raise RuntimeError("reference source is not in the frozen primary-source allowlist")
