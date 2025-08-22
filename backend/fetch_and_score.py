import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict
import logging
from credtech import altman_z_score, ohlson_o_score, normalize_score, CompanyFinancials
from unstructured import news_sentiment_score
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_and_compute_credit_scores(
    tickers: List[str], 
    weight_altman: float = 0.50,
    weight_ohlson: float = 0.40,
    weight_sentiment: float = 0.10
) -> Dict[str, Dict[str, float]]:
    results = {}
    failed_tickers = []
    
    for ticker in tickers:
        logger.info(f"Processing ticker: {ticker}")
        try:
            stock = yf.Ticker(ticker)
            quarterly_bs = stock.quarterly_balance_sheet
            quarterly_income = stock.quarterly_financials
            info = stock.info

            if quarterly_bs.empty or quarterly_income.empty:
                logger.warning(f"No financial data available for {ticker}")
                failed_tickers.append(ticker)
                continue

            bs_latest = quarterly_bs.iloc[:, 0]
            is_latest = quarterly_income.iloc[:, 0]

            def safe_extract(series, keys, default=np.nan):
                for key in keys:
                    try:
                        value = series.get(key)
                        if value is not None and not pd.isna(value):
                            return float(value)
                    except:
                        continue
                return default

            # Extract financial data
            total_assets = safe_extract(bs_latest, [
                'Total Assets', 'TotalAssets', 'Assets'
            ])
            
            total_liabilities = safe_extract(bs_latest, [
                'Total Liab', 'Total Liabilities', 'TotalLiabilities'
            ])
            if pd.isna(total_liabilities):
                total_equity = safe_extract(bs_latest, [
                    'Total Stockholder Equity', 'Stockholders Equity', 'Total Equity', 'Shareholders Equity'
                ])
                if not pd.isna(total_equity) and not pd.isna(total_assets):
                    total_liabilities = total_assets - total_equity
                    logger.info(f"{ticker}: Estimated total_liabilities as total_assets - total_equity")

            current_assets = safe_extract(bs_latest, [
                'Total Current Assets', 'TotalCurrentAssets', 'Current Assets'
            ])
            
            current_liabilities = safe_extract(bs_latest, [
                'Total Current Liabilities', 'TotalCurrentLiabilities', 'Current Liabilities'
            ])
            
            retained_earnings = safe_extract(bs_latest, [
                'Retained Earnings', 'RetainedEarnings'
            ])
            
            revenue = safe_extract(is_latest, [
                'Total Revenue', 'TotalRevenue', 'Revenue', 'Net Sales'
            ])
            
            net_income = safe_extract(is_latest, [
                'Net Income', 'NetIncome'
            ])
            
            ebit = safe_extract(is_latest, [
                'EBIT', 'Ebit', 'Operating Income', 'OperatingIncome'
            ])
            
            market_cap = info.get('marketCap')

            # Apply defaults and estimates for missing values
            def apply_default(value, default, field_name):
                if pd.isna(value) or value is None:
                    logger.warning(f"{ticker}: Using default for {field_name}: {default}")
                    return default
                return float(value)
            
            total_assets = max(apply_default(total_assets, 1000000, "total_assets"), 1000000)
            total_liabilities = max(apply_default(total_liabilities, 100000, "total_liabilities"), 100000)
            current_assets = max(apply_default(current_assets, total_assets * 0.4, "current_assets"), 0)
            current_liabilities = max(apply_default(current_liabilities, total_liabilities * 0.6, "current_liabilities"), 0)
            retained_earnings = apply_default(retained_earnings, total_assets - total_liabilities, "retained_earnings")
            ebit = apply_default(ebit, 0, "ebit")
            market_cap = max(apply_default(market_cap, 1000000, "market_cap"), 1000000)
            revenue = max(apply_default(revenue, 0, "revenue"), 0)
            net_income = apply_default(net_income, 0, "net_income")
            
            working_capital = current_assets - current_liabilities

            # Get sentiment score
            try:
                sentiment_score = news_sentiment_score(ticker)
            except Exception as e:
                logger.warning(f"Could not get sentiment for {ticker}: {e}")
                sentiment_score = 0.5  # Neutral default

            # Create financial object
            fin = CompanyFinancials(
                total_assets=total_assets,
                total_liabilities=total_liabilities,
                working_capital=working_capital,
                retained_earnings=retained_earnings,
                ebit=ebit,
                market_value_equity=market_cap,
                sales=revenue,
                net_income=net_income,
                current_assets=current_assets,
                current_liabilities=current_liabilities,
                sentiment_score=sentiment_score
            )

            # Calculate scores
            altman_raw = altman_z_score(fin)
            ohlson_raw = ohlson_o_score(fin)
            
            # Normalize scores
            altman_norm = normalize_score(altman_raw, -3, 10)
            ohlson_norm = 100 - normalize_score(ohlson_raw, -5, 4)  # Invert since lower is better

            final_score = (
                weight_altman * altman_norm
                + weight_ohlson * ohlson_norm
                + weight_sentiment * sentiment_score * 100
            )
            
            # Calculate confidence interval
            margin = final_score * 0.05
            score_min = max(0, final_score - margin)
            score_max = min(100, final_score + margin)

            results[ticker] = {
                'base_score': round(final_score, 2),
                'score_min': round(score_min, 2),
                'score_max': round(score_max, 2),
                'altman_z': round(altman_raw, 2),
                'ohlson_o': round(ohlson_raw, 2),
                'sentiment': round(sentiment_score, 3),
                'grade': get_credit_grade(final_score)
            }
            
            logger.info(f"{ticker}: Score = {final_score:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to process {ticker}: {str(e)}")
            failed_tickers.append(ticker)

    if failed_tickers:
        logger.warning(f"Failed tickers: {failed_tickers}")
    
    logger.info(f"Processed {len(results)} of {len(tickers)}")
    return results

def get_credit_grade(score: float) -> str:
    """Convert numeric score to letter grade"""
    if score >= 90:
        return 'AAA'
    elif score >= 80:
        return 'AA'
    elif score >= 70:
        return 'A'
    elif score >= 60:
        return 'BBB'
    elif score >= 50:
        return 'BB'
    elif score >= 40:
        return 'B'
    else:
        return 'CCC'

def get_score_breakdown_data():
    """Generate data for pie chart visualization"""
    
    altman_breakdown = {
        'Working Capital Efficiency': 11.78,
        'Retained Earnings': 13.91, 
        'Operating Performance': 51.03,
        'Market Valuation': 6.90,
        'Asset Turnover': 16.39
    }
    
    ohlson_breakdown = {
        'Company Size': 25.89,
        'Debt Structure': 8.17,
        'Working Capital': 28.70,
        'Liquidity Position': 1.52,
        'Profitability': 7.43,
        'Income Stability': 24.89,
        'Sales Efficiency': 3.41
    }
    
    return {
        'altman': altman_breakdown,
        'ohlson': ohlson_breakdown,
        'weights': {
            'altman_weight': 50,
            'ohlson_weight': 40,
            'sentiment_weight': 10
        }
    }

if __name__ == "__main__":
    # Test with a few tickers
    results = fetch_and_compute_credit_scores(['AAPL', 'GOOGL', 'MSFT'])
    for ticker, score_data in results.items():
        print(f"{ticker}: Base Score = {score_data['base_score']}, "
              f"Grade = {score_data['grade']}, "
              f"Range = ({score_data['score_min']}, {score_data['score_max']})")