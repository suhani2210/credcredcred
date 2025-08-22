export const calculateCreditScore = (company) => {
  // Pseudo credit score algorithm
  // Weights for different factors
  const weights = {
    profitability: 0.25,    // Net margin
    liquidity: 0.20,        // Current ratio
    leverage: 0.25,         // Debt ratio (inverse)
    efficiency: 0.15,       // ROA
    growth: 0.15           // Revenue growth
  };

  // Calculate net margin
  const netMargin = company.netIncome / company.revenue;
  
  // Calculate revenue growth (simplified - using last year data)
  const currentRevenue = company.historicalData[company.historicalData.length - 1].revenue;
  const previousRevenue = company.historicalData[company.historicalData.length - 2].revenue;
  const revenueGrowth = (currentRevenue - previousRevenue) / previousRevenue;

  // Normalize scores to 0-100 scale
  const scores = {
    profitability: Math.min(100, Math.max(0, netMargin * 400)), // Scale net margin
    liquidity: Math.min(100, Math.max(0, (company.currentRatio - 0.5) * 50)), // Scale current ratio
    leverage: Math.min(100, Math.max(0, (1 - company.debtRatio) * 100)), // Inverse debt ratio
    efficiency: Math.min(100, Math.max(0, company.roa * 500)), // Scale ROA
    growth: Math.min(100, Math.max(0, 50 + (revenueGrowth * 200))) // Scale growth rate
  };

  // Calculate weighted average
  const creditScore = Math.round(
    scores.profitability * weights.profitability +
    scores.liquidity * weights.liquidity +
    scores.leverage * weights.leverage +
    scores.efficiency * weights.efficiency +
    scores.growth * weights.growth
  );

  return Math.min(100, Math.max(0, creditScore));
};