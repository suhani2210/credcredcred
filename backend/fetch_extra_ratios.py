import yfinance as yf
import pandas as pd
import numpy as np
import logging
import re
from typing import Dict, List, Optional, Tuple

# ---------------------------
# Logging — very chatty on purpose
# ---------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(asctime)s:%(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ratios")

# ---------------------------
# Helpers
# ---------------------------
def _normalize(s: str) -> str:
    """Normalize a line-item name for matching (case/space/punct insensitive)."""
    if s is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

def _latest_col(df: pd.DataFrame) -> Optional[pd.Timestamp]:
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    # Try datetimes; if fail, assume first column is most recent (yfinance typical)
    try:
        dts = pd.to_datetime(cols, errors="coerce")
        # pick the max valid date
        if dts.notna().any():
            mx_idx = int(np.nanargmax(dts.values))
            return cols[mx_idx]
    except Exception:
        pass
    return cols[0]

def _find_item_value(
    df: Optional[pd.DataFrame],
    candidates: List[str],
) -> Tuple[Optional[float], Optional[str]]:
    """Search df’s index for any candidate key (robust, fuzzy). Return (value, matched_key)."""
    if df is None or df.empty:
        return None, None

    # map normalized index -> real index
    idx_map = {_normalize(idx): idx for idx in df.index}
    # Try exact normalized matches first
    for key in candidates:
        nk = _normalize(key)
        if nk in idx_map:
            col = _latest_col(df)
            if col is not None and col in df.columns:
                try:
                    val = df.loc[idx_map[nk], col]
                    return float(val), idx_map[nk]
                except Exception:
                    pass

    # Fallback: substring search
    for key in candidates:
        nk = _normalize(key)
        hits = [real for norm, real in idx_map.items() if nk in norm]
        if hits:
            col = _latest_col(df)
            if col is not None and col in df.columns:
                for real in hits:
                    try:
                        val = df.loc[real, col]
                        return float(val), real
                    except Exception:
                        continue
    return None, None

def _choose(value_list: List[Tuple[Optional[float], str]]) -> Tuple[Optional[float], Optional[str]]:
    """Return the first non-None (value, src)."""
    for v, s in value_list:
        if v is not None and (isinstance(v, (int, float)) and not np.isnan(v)):
            return float(v), s
    return None, None

def _pretty(num: Optional[float]) -> str:
    if num is None or (isinstance(num, float) and (np.isnan(num) or np.isinf(num))):
        return "N/A"
    # Format compactly; ratios like ROE/ROA/ROCE are in decimals
    return f"{num:.6f}"

def _series_two(df: Optional[pd.DataFrame], candidates: List[str]) -> Optional[pd.Series]:
    """Extract the latest values for a given set of keys from a dataframe as a pandas Series."""
    if df is None or df.empty:
        return None

    idx_map = {_normalize(idx): idx for idx in df.index}
    for key in candidates:
        nk = _normalize(key)
        if nk in idx_map:
            try:
                # Return the latest values from the found row as a Series
                return df.loc[idx_map[nk]].dropna().astype(float)
            except Exception:
                pass
    return None


# ---------------------------
# Main computation
# ---------------------------
def fetch_ratios_no_nans(ticker_symbol: str) -> Dict[str, str]:
    log.info("Fetching data for %s", ticker_symbol)
    tkr = yf.Ticker(ticker_symbol)

    # Pull statements
    try:
        bal_yr = tkr.balance_sheet
        bal_q = tkr.quarterly_balance_sheet
        inc_yr = tkr.financials          # annual income statement
        inc_q = tkr.quarterly_financials # quarterly income statement
        info = tkr.info or {}
        fast = getattr(tkr, "fast_info", {}) or {}
    except Exception as e:
        log.error("Failed to fetch statements: %s", e)
        raise

    # --- Price/Earnings (trailing) ---
    # Preferred: info['trailingPE']; else compute from price / trailingEps
    trailing_pe = info.get("trailingPE")
    trailing_eps = info.get("trailingEps")
    price_sources = [fast.get("last_price"), fast.get("last_price_raw"), info.get("currentPrice")]
    price = next((p for p in price_sources if isinstance(p, (int, float)) and p is not None), None)
    if trailing_pe is None and (price is not None and trailing_eps not in (None, 0)):
        trailing_pe = price / trailing_eps if trailing_eps not in (None, 0) else None
        log.debug("Computed trailing P/E via price/eps: price=%s eps=%s -> pe=%s", price, trailing_eps, trailing_pe)
    else:
        log.debug("Using info['trailingPE']=%s (price=%s, eps=%s)", trailing_pe, price, trailing_eps)

    # --- Balance sheet items ---
    # Equity
    equity_candidates = [
        "Total Stockholder Equity",
        "Total Stockholders' Equity",
        "Total Equity",
        "Total Equity Gross Minority Interest",
    ]
    equity_val, equity_key = _choose([
        (*_find_item_value(bal_yr, equity_candidates),),  # type: ignore
        (*_find_item_value(bal_q, equity_candidates),),   # type: ignore
        (info.get("totalStockholderEquity"), "info.totalStockholderEquity"),
    ])
    log.debug("Equity found: %s via %s", equity_val, equity_key)

    # Total assets
    assets_candidates = ["Total Assets"]
    assets_val, assets_key = _choose([
        (*_find_item_value(bal_yr, assets_candidates),),
        (*_find_item_value(bal_q, assets_candidates),),
        (info.get("totalAssets"), "info.totalAssets"),
    ])
    log.debug("Total Assets found: %s via %s", assets_val, assets_key)

    # Current assets / liabilities
    cur_assets_candidates = ["Total Current Assets"]
    cur_liab_candidates   = ["Total Current Liabilities"]
    cur_assets_val, cur_assets_key = _choose([
        (*_find_item_value(bal_yr, cur_assets_candidates),),
        (*_find_item_value(bal_q, cur_assets_candidates),),
        (info.get("totalCurrentAssets"), "info.totalCurrentAssets"),
    ])
    log.debug("Current Assets: %s via %s", cur_assets_val, cur_assets_key)

    cur_liab_val, cur_liab_key = _choose([
        (*_find_item_value(bal_yr, cur_liab_candidates),),
        (*_find_item_value(bal_q, cur_liab_candidates),),
        (info.get("totalCurrentLiabilities"), "info.totalCurrentLiabilities"),
    ])
    log.debug("Current Liabilities: %s via %s", cur_liab_val, cur_liab_key)

    # Inventory (for Quick ratio). Some tech firms have small/no inventory.
    inventory_candidates = ["Inventory", "Inventories"]
    inventory_val, inventory_key = _choose([
        (*_find_item_value(bal_yr, inventory_candidates),),
        (*_find_item_value(bal_q, inventory_candidates),),
        (info.get("inventory"), "info.inventory"),
    ])
    log.debug("Inventory: %s via %s", inventory_val, inventory_key)

    # Cash & Short-term investments & Receivables for Quick ratio robust calc
    cash_candidates = [
        "Cash And Cash Equivalents",
        "Cash And Cash Equivalents, at Carrying Value",
        "Cash",
    ]
    sti_candidates = ["Short Term Investments", "Marketable Securities"]
    recv_candidates = ["Net Receivables", "Accounts Receivable", "Accounts Receivable Net Current"]

    cash_val, cash_key = _choose([
        (*_find_item_value(bal_yr, cash_candidates),),
        (*_find_item_value(bal_q, cash_candidates),),
        (info.get("cash"), "info.cash"),
    ])
    sti_val, sti_key = _choose([
        (*_find_item_value(bal_yr, sti_candidates),),
        (*_find_item_value(bal_q, sti_candidates),),
        (info.get("shortTermInvestments"), "info.shortTermInvestments"),
    ])
    recv_val, recv_key = _choose([
        (*_find_item_value(bal_yr, recv_candidates),),
        (*_find_item_value(bal_q, recv_candidates),),
        (info.get("netReceivables"), "info.netReceivables"),
    ])
    log.debug("Cash=%s (%s), ShortTermInv=%s (%s), Receivables=%s (%s)",
              cash_val, cash_key, sti_val, sti_key, recv_val, recv_key)

    # Total Debt = (Short-term + Long-term). Prefer balance sheet items; else info.totalDebt
    debt_parts_candidates = [
        (["Short Long Term Debt", "Short-Term Debt", "Short Term Debt", "Current Debt"], "short_debt"),
        (["Long Term Debt", "Long-Term Debt", "Long Term Debt Noncurrent",
          "Long Term Debt And Capital Lease Obligation"], "long_debt"),
    ]
    short_debt, short_src = _choose([
        (*_find_item_value(bal_yr, debt_parts_candidates[0][0]),),
        (*_find_item_value(bal_q, debt_parts_candidates[0][0]),),
        (info.get("shortLongTermDebt"), "info.shortLongTermDebt"),
        (info.get("shortTermDebt"), "info.shortTermDebt"),
    ])
    long_debt, long_src = _choose([
        (*_find_item_value(bal_yr, debt_parts_candidates[1][0]),),
        (*_find_item_value(bal_q, debt_parts_candidates[1][0]),),
        (info.get("longTermDebt"), "info.longTermDebt"),
    ])
    total_debt = None
    if short_debt is not None or long_debt is not None:
        total_debt = (short_debt or 0.0) + (long_debt or 0.0)
        log.debug("Debt from parts: short=%s (%s) + long=%s (%s) => total=%s",
                  short_debt, short_src, long_debt, long_src, total_debt)
    else:
        total_debt = info.get("totalDebt")
        log.debug("Debt from info.totalDebt => %s", total_debt)

    # --- Income statement items ---
    # Net Income (TTM approx: use latest annual first, else quarterly sum if available)
    net_income_candidates = ["Net Income", "Net Income Common Stockholders", "Net Income Applicable To Common Shares"]
    ni_yr, ni_yr_key = _find_item_value(inc_yr, net_income_candidates)
    ni_q,  ni_q_key  = _find_item_value(inc_q, net_income_candidates)

    net_income = None
    ni_src = None
    if ni_yr is not None:
        net_income = ni_yr
        ni_src = f"annual:{ni_yr_key}"
    elif ni_q is not None:
        # Sum last 4 quarters if available
        try:
            vals = inc_q.loc[ni_q_key].dropna().astype(float)
            net_income = float(vals.iloc[:4].sum()) if len(vals) >= 1 else float(ni_q)
            ni_src = f"quarterly_sum:{ni_q_key}"
        except Exception:
            net_income = ni_q
            ni_src = f"quarterly:{ni_q_key}"
    else:
        net_income = info.get("netIncomeToCommon") or info.get("netIncome")
        ni_src = "info"
    log.debug("Net Income: %s via %s", net_income, ni_src)

    # EBIT (use 'Ebit' row; fallback to Operating Income)
    ebit_candidates = ["Ebit", "EBIT", "Operating Income"]
    ebit_val, ebit_key = _choose([
        (*_find_item_value(inc_yr, ebit_candidates),),
        (*_find_item_value(inc_q, ebit_candidates),),
        (info.get("ebitda") if info.get("depreciation") is not None else None, "approx from info.ebitda - depreciation (not applied)"),
    ])
    log.debug("EBIT: %s via %s", ebit_val, ebit_key)

    # For averages, try to compute 2-period averages if columns exist
    def _two_period_avg(df: Optional[pd.DataFrame], candidates: List[str]) -> Optional[float]:
        if df is None or df.empty:
            return None
        idx_val, idx_key = _find_item_value(df, candidates)
        if idx_val is None:
            return None
        try:
            row = df.loc[idx_key].dropna().astype(float)
            if len(row) >= 2:
                avg = float(row.iloc[:2].mean())
                log.debug("Avg(2) for %s => %s", idx_key, avg)
                return avg
            return float(row.iloc[0])
        except Exception:
            return float(row.iloc[0]) # Use the latest if only one period is available
        except Exception:
            return idx_val

    assets_series_2_yr = _series_two(bal_yr, assets_candidates)
    assets_series_2_q  = _series_two(bal_q, assets_candidates)
    assets_series_2 = assets_series_2_yr if assets_series_2_yr is not None and not assets_series_2_yr.empty else assets_series_2_q

    cliab_series_2_yr = _series_two(bal_yr, cur_liab_candidates)
    cliab_series_2_q  = _series_two(bal_q, cur_liab_candidates)
    cliab_series_2 = cliab_series_2_yr if cliab_series_2_yr is not None and not cliab_series_2_yr.empty else cliab_series_2_q

    avg_equity = _choose([
        (_two_period_avg(bal_yr, equity_candidates), "annual avg equity"),
        (_two_period_avg(bal_q, equity_candidates), "quarterly avg equity"),
        (equity_val, "single latest equity"),
    ])[0]

    avg_assets = _choose([
        (_two_period_avg(bal_yr, assets_candidates), "annual avg assets"),
        (_two_period_avg(bal_q, assets_candidates), "quarterly avg assets"),
        (assets_val, "single latest assets"),
    ])[0]


    # Capital Employed = Total Assets - Current Liabilities (use average if possible)
    ce_latest = (assets_val if assets_val is not None else 0.0) - (cur_liab_val if cur_liab_val is not None else 0.0)

    cap_employed_avg = ce_latest # Default to latest

    if assets_series_2 is not None and cliab_series_2 is not None and len(assets_series_2) == len(cliab_series_2) and len(assets_series_2) >= 1:
        try:
            cap_employed_avg = float((assets_series_2 - cliab_series_2).mean())
            log.debug("Capital Employed (avg of %d) => %s", len(assets_series_2), cap_employed_avg)
        except Exception as e:
            log.warning("Failed to compute average Capital Employed: %s", e)
            cap_employed_avg = ce_latest
            log.debug("Capital Employed (latest) => %s", cap_employed_avg)
    else:
        log.debug("Capital Employed (latest) => %s", cap_employed_avg)


    # ---------------------------
    # Ratios (no NaNs allowed)
    # ---------------------------
    def safe_div(n: Optional[float], d: Optional[float]) -> Optional[float]:
        try:
            if n is None or d in (None, 0, 0.0) or (isinstance(d, float) and np.isclose(d, 0.0)):
                return None
            return float(n) / float(d)
        except Exception:
            return None

    # Debt to Equity
    d_to_e = safe_div(total_debt, equity_val)

    # Current Ratio
    current_ratio = safe_div(cur_assets_val, cur_liab_val)

    # Quick Ratio — robust (cash + short-term investments + receivables)/current liabilities
    quick_assets = None
    parts = [cash_val, sti_val, recv_val]
    if any(p is not None for p in parts) and cur_liab_val not in (None, 0):
        quick_assets = (cash_val or 0.0) + (sti_val or 0.0) + (recv_val or 0.0)
        quick_ratio = safe_div(quick_assets, cur_liab_val)
        log.debug("Quick ratio via (Cash+STI+Receivables)/CL: qa=%s, cl=%s => %s",
                  quick_assets, cur_liab_val, quick_ratio)
    else:
        # fallback using (current assets - inventory)/current liabilities
        if cur_assets_val is not None and cur_liab_val not in (None, 0):
            quick_ratio = safe_div((cur_assets_val - (inventory_val or 0.0)), cur_liab_val)
            log.debug("Quick ratio via (CA-Inventory)/CL: ca=%s, inv=%s, cl=%s => %s",
                      cur_assets_val, inventory_val, cur_liab_val, quick_ratio)
        else:
            quick_ratio = None
            log.debug("Quick ratio could not be computed from either method.")

    # ROE = Net Income / Avg Equity
    roe = safe_div(net_income, avg_equity)
    # Fallback to info.returnOnEquity if needed
    if roe is None and isinstance(info.get("returnOnEquity"), (int, float)):
        roe = float(info["returnOnEquity"])
        log.debug("ROE fallback to info.returnOnEquity => %s", roe)

    # ROA = Net Income / Avg Assets
    roa = safe_div(net_income, avg_assets)
    if roa is None and isinstance(info.get("returnOnAssets"), (int, float)):
        roa = float(info["returnOnAssets"])
        log.debug("ROA fallback to info.returnOnAssets => %s", roa)

    # ROCE = EBIT / Capital Employed (avg if available)
    roce = safe_div(ebit_val, cap_employed_avg)
    if roce is None:
        log.debug("ROCE could not be computed (ebit=%s, cap_employed_avg=%s)", ebit_val, cap_employed_avg)

    # Price/Earnings already determined (trailing_pe)
    pe = trailing_pe

    # ---------------------------
    # Final, with no NaNs (strings)
    # ---------------------------
    result = {
        "Debt to Equity": _pretty(d_to_e),
        "Price to Earnings": _pretty(pe),
        "Current Ratio": _pretty(current_ratio),
        "Quick Ratio": _pretty(quick_ratio),
        "ROCE": _pretty(roce),
        "ROE": _pretty(roe),
        "ROA": _pretty(roa),
    }

    # Helpful recap in logs
    log.info("Computed ratios for %s => %s", ticker_symbol, result)
    return result


if __name__ == "__main__":
    # Example: Apple Inc.
    symbol = "AAPL"
    ratios = fetch_ratios_no_nans(symbol)
    # Pretty table
    df = pd.DataFrame.from_dict(ratios, orient="index", columns=["Value"])
    print(f"\nFinancial Ratios for {symbol} (no NaNs):\n")
    print(df.to_string())
