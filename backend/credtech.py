from typing import Tuple
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

class CompanyFinancials(BaseModel):
    # Core financial input fields required to compute Altman Z and Ohlson O-score
    total_assets: float = Field(..., description="Total assets of the company")
    total_liabilities: float = Field(..., description="Total liabilities of the company")
    working_capital: float = Field(..., description="Working capital = Current Assets - Current Liabilities")
    retained_earnings: float = Field(..., description="Retained earnings from balance sheet")
    ebit: float = Field(..., description="Earnings before interest and taxes")
    market_value_equity: float = Field(..., description="Market capitalization of company")
    sales: float = Field(..., description="Total revenue / sales")
    net_income: float = Field(..., description="Net income from income statement")
    current_assets: float = Field(..., description="Current assets")
    current_liabilities: float = Field(..., description="Current liabilities")
    sentiment_score: float = Field(..., ge=0, le=1, description="Sentiment score (0 = worst, 1 = best)")


def altman_z_score(fin: CompanyFinancials) -> float:
    """
    Compute the Altman Z-score.
    Formula is a weighted linear combination of financial ratios
    designed to predict bankruptcy risk.
    """
    try:
        x1 = fin.working_capital / fin.total_assets
        x2 = fin.retained_earnings / fin.total_assets
        x3 = fin.ebit / fin.total_assets
        x4 = fin.market_value_equity / fin.total_liabilities
        x5 = fin.sales / fin.total_assets

        return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
    except Exception as e:
        logger.warning(f"Error calculating Altman Z-score: {e}")
        return 0.0


def ohlson_o_score(fin: CompanyFinancials) -> float:
    """
    Compute the Ohlson O-score.
    A logit-based bankruptcy probability model combining 9 ratios.
    """
    try:
        size = fin.total_liabilities / fin.total_assets if fin.total_assets != 0 else 0
        leverage = fin.current_liabilities / fin.current_assets if fin.current_assets != 0 else 0
        net_income_sign = 1 if fin.net_income < 0 else 0
        wc_over_assets = fin.working_capital / fin.total_assets if fin.total_assets != 0 else 0

        # Simplified formula (not all 9 terms included here)
        score = (
            -1.32
            - 0.407 * size
            + 6.03 * leverage
            - 1.43 * wc_over_assets
            + 0.0757 * (fin.current_liabilities / fin.current_assets if fin.current_assets != 0 else 0)
            - 2.37 * net_income_sign
        )
        return score
    except Exception as e:
        logger.warning(f"Error calculating Ohlson O-score: {e}")
        return 0.0


def normalize_score(score: float, min_val: float, max_val: float) -> float:
    """Normalize any score into the 0-100 range."""
    if max_val == min_val:
        return 50.0  # Default to middle if no range
    return max(0, min(100, 100 * (score - min_val) / (max_val - min_val)))


def combined_credit_score(
    fin: CompanyFinancials,
    weight_altman: float = 0.5,
    weight_ohlson: float = 0.4,
    weight_sentiment: float = 0.1,
) -> Tuple[float, Tuple[float, float]]:
    """
    Combine Altman Z, Ohlson O, and sentiment into a final score.
    The weights should sum close to 1.0.

    Returns:
        final_score (float): Credit score out of 100
        confidence_interval (tuple): Score range (low, high) showing error margin
    """

    # Step 1: Compute raw Altman Z and Ohlson O scores
    altman = altman_z_score(fin)
    ohlson = ohlson_o_score(fin)
    sentiment = fin.sentiment_score  # Already between 0-1

    # Step 2: Normalize scores into comparable 0-100 range
    altman_norm = normalize_score(altman, -5, 8)  # typical range
    ohlson_norm = 100 - normalize_score(ohlson, -3, 3)  # Invert since lower is better
    sentiment_norm = sentiment * 100

    # Step 3: Weighted combination
    final_score = (
        weight_altman * altman_norm
        + weight_ohlson * ohlson_norm
        + weight_sentiment * sentiment_norm
    )

    # Step 4: Error margins (±5% of score to reflect uncertainty)
    margin = final_score * 0.05
    return final_score, (final_score - margin, final_score + margin)


# ================== Example Usage =====================
if __name__ == "__main__":
    fin = CompanyFinancials(
        total_assets=1000,
        total_liabilities=400,
        working_capital=200,
        retained_earnings=150,
        ebit=120,
        market_value_equity=800,
        sales=900,
        net_income=100,
        current_assets=500,
        current_liabilities=300,
        sentiment_score=0.75,  # example sentiment score from NLP
    )

    score, interval = combined_credit_score(fin)
    print(f"Final Credit Score: {score:.2f}/100")
    print(f"Confidence Interval: {interval}")