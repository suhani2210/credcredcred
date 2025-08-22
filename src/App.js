import React, { useState, useEffect } from 'react';
import './App.css';
import Layout from './components/Layout';
import CompanySelector from './components/CompanySelector';
import CreditScoreDisplay from './components/CreditScoreDisplay';
import FinancialCharts from './components/FinancialCharts';

// API base URL - change this to your backend URL
const API_BASE_URL = 'http://localhost:5000';

function App() {
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch available companies on app load
  useEffect(() => {
    fetchCompanies();
  }, []);

  const fetchCompanies = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/companies`);
      const data = await response.json();
      setCompanies(data.companies || []);
    } catch (error) {
      console.error('Error fetching companies:', error);
      // Fallback to hardcoded companies if API fails
      setCompanies([
        { ticker: 'AAPL', name: 'Apple Inc.' },
        { ticker: 'MSFT', name: 'Microsoft Corporation' },
        { ticker: 'GOOGL', name: 'Alphabet Inc.' },
        { ticker: 'AMZN', name: 'Amazon.com Inc.' },
        { ticker: 'TSLA', name: 'Tesla Inc.' },
        { ticker: 'META', name: 'Meta Platforms Inc.' }
      ]);
    }
  };

  const handleCompanySelect = async (ticker) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/company-analysis/${ticker}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch analysis for ${ticker}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Find the selected company from the companies list
      const company = companies.find(c => c.ticker === ticker);
      
      setSelectedCompany(company);
      setAnalysisData(data);
      
    } catch (error) {
      console.error('Error fetching company analysis:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <Layout>
        <div className="main-content">
          <CompanySelector 
            companies={companies}
            selectedCompany={selectedCompany}
            onCompanySelect={handleCompanySelect}
            loading={loading}
          />
          
          {error && (
            <div style={{
              padding: '1rem',
              backgroundColor: '#fee2e2',
              border: '1px solid #fecaca',
              borderRadius: '0.5rem',
              color: '#dc2626',
              marginTop: '1rem'
            }}>
              Error: {error}
            </div>
          )}
          
          {loading && (
            <div style={{
              textAlign: 'center',
              padding: '2rem',
              color: '#6b7280'
            }}>
              Loading analysis...
            </div>
          )}
          
          {selectedCompany && analysisData && !loading && (
            <div className="dashboard-grid">
              <CreditScoreDisplay 
                company={selectedCompany}
                analysisData={analysisData}
              />
              <FinancialCharts 
                company={selectedCompany}
                analysisData={analysisData}
              />
            </div>
          )}
        </div>
      </Layout>
    </div>
  );
}

export default App;