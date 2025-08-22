from flask import Flask, jsonify, request
from flask_cors import CORS
from fetch_and_score import fetch_and_compute_credit_scores, get_score_breakdown_data
from fetch_company_name import get_company_name_yfinance
from fetch_extra_ratios import fetch_ratios_no_nans
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Credit Score API',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/companies')
def get_companies():
    """Get list of available companies with their names"""
    # Predefined list of major companies
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'INTC', 'ADBE']
    
    companies = []
    for ticker in tickers:
        try:
            name = get_company_name_yfinance(ticker)
            if not name.startswith("Error") and not name.startswith("Company name not available"):
                companies.append({
                    'ticker': ticker,
                    'name': name
                })
            else:
                # Fallback names for common tickers
                fallback_names = {
                    'AAPL': 'Apple Inc.',
                    'MSFT': 'Microsoft Corporation',
                    'GOOGL': 'Alphabet Inc.',
                    'AMZN': 'Amazon.com Inc.',
                    'TSLA': 'Tesla Inc.',
                    'META': 'Meta Platforms Inc.',
                    'NVDA': 'NVIDIA Corporation',
                    'NFLX': 'Netflix Inc.',
                    'INTC': 'Intel Corporation',
                    'ADBE': 'Adobe Inc.'
                }
                companies.append({
                    'ticker': ticker,
                    'name': fallback_names.get(ticker, f"{ticker} Inc.")
                })
        except Exception as e:
            logger.warning(f"Error getting name for {ticker}: {str(e)}")
            continue
    
    return jsonify({
        'companies': companies,
        'count': len(companies)
    })

@app.route('/api/company-analysis/<ticker>')
def company_analysis(ticker):
    """Get complete analysis for a specific company"""
    try:
        ticker = ticker.upper()
        logger.info(f"Analyzing ticker: {ticker}")
        
        # Get company name
        company_name = get_company_name_yfinance(ticker)
        
        # Get credit scores for the ticker
        credit_results = fetch_and_compute_credit_scores([ticker])
        
        if ticker not in credit_results:
            return jsonify({
                'error': f'No financial data available for {ticker}. Please check the ticker symbol.'
            }), 404
        
        # Get financial ratios
        try:
            ratios = fetch_ratios_no_nans(ticker)
        except Exception as e:
            logger.warning(f"Could not fetch ratios for {ticker}: {str(e)}")
            ratios = {}
        
        # Get breakdown data
        breakdown_data = get_score_breakdown_data()
        
        response_data = {
            'ticker': ticker,
            'company_name': company_name,
            'credit_scores': credit_results[ticker],
            'financial_ratios': ratios,
            'breakdown': breakdown_data,
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Successfully analyzed {ticker}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {str(e)}")
        return jsonify({
            'error': f'Failed to analyze {ticker}: {str(e)}'
        }), 500

@app.route('/api/batch-analysis', methods=['POST'])
def batch_analysis():
    """Analyze multiple companies at once"""
    try:
        data = request.get_json()
        tickers = data.get('tickers', [])
        
        if not tickers:
            return jsonify({'error': 'No tickers provided'}), 400
        
        # Limit batch size for performance
        if len(tickers) > 10:
            return jsonify({'error': 'Maximum 10 tickers per batch'}), 400
        
        # Convert to uppercase
        tickers = [ticker.upper() for ticker in tickers]
        
        # Get credit scores
        credit_results = fetch_and_compute_credit_scores(tickers)
        
        # Get company names and ratios for each ticker
        results = {}
        for ticker in credit_results.keys():
            try:
                company_name = get_company_name_yfinance(ticker)
                try:
                    ratios = fetch_ratios_no_nans(ticker)
                except:
                    ratios = {}
                
                results[ticker] = {
                    'company_name': company_name,
                    'credit_scores': credit_results[ticker],
                    'financial_ratios': ratios
                }
            except Exception as e:
                logger.warning(f"Error processing {ticker}: {str(e)}")
                continue
        
        # Get breakdown data
        breakdown_data = get_score_breakdown_data()
        
        return jsonify({
            'results': results,
            'breakdown': breakdown_data,
            'processed_count': len(results),
            'requested_count': len(tickers),
            'success': True,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        return jsonify({'error': 'Batch analysis failed'}), 500

@app.route('/api/chart-data')
def chart_data():
    """API endpoint to get pie chart data"""
    try:
        data = get_score_breakdown_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting chart data: {str(e)}")
        return jsonify({'error': 'Failed to load chart data'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)