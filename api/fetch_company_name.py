import yfinance as yf
import logging

logger = logging.getLogger(__name__)

def get_company_name_yfinance(ticker):
    """
    Fetches the company name from yfinance for a given ticker.
    
    Args:
        ticker (str): Stock ticker symbol.
        
    Returns:
        str: Company name, or an error message if not found.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info:
            return f"No information available for {ticker}"
            
        company_name = info.get('longName') or info.get('shortName') or info.get('name')
        
        if company_name:
            return company_name
        else:
            return f"Company name not available for {ticker}"
            
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {str(e)}")
        return f"Error fetching data for {ticker}: {str(e)}"

# Example usage and test
if __name__ == "__main__":
    test_tickers = ["AAPL", "MSFT", "GOOGL", "INVALID"]
    for ticker in test_tickers:
        name = get_company_name_yfinance(ticker)
        print(f"{ticker}: {name}")