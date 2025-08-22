import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { BarChart3, TrendingUp, PieChart as PieChartIcon } from 'lucide-react';

const FinancialCharts = ({ company, analysisData }) => {
  if (!analysisData) {
    return null;
  }

  const ratios = analysisData.financial_ratios || {};
  const creditScores = analysisData.credit_scores || {};

  // Convert financial ratios to chart data
  const ratioData = Object.entries(ratios)
    .filter(([key, value]) => value !== 'N/A' && !isNaN(parseFloat(value)))
    .map(([key, value]) => ({
      name: key.replace(/([A-Z])/g, ' $1').trim(),
      value: parseFloat(value),
      displayValue: value
    }));

  // Score breakdown data
  const scoreBreakdownData = [
    { name: 'Altman Z-Score', value: 50, color: '#3b82f6' },
    { name: 'Ohlson O-Score', value: 40, color: '#10b981' },
    { name: 'Market Sentiment', value: 10, color: '#f59e0b' }
  ];

  // Component scores for detailed view
  const componentData = [
    { name: 'Altman Z', value: Math.abs(creditScores.altman_z || 0), color: '#3b82f6' },
    { name: 'Ohlson O', value: Math.abs(creditScores.ohlson_o || 0), color: '#10b981' },
    { name: 'Sentiment', value: (creditScores.sentiment || 0) * 10, color: '#f59e0b' }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Score Composition */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <PieChartIcon size={20} />
          <h3>Score Composition</h3>
        </div>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={scoreBreakdownData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={5}
              dataKey="value"
            >
              {scoreBreakdownData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => [`${value}%`, 'Weight']} />
          </PieChart>
        </ResponsiveContainer>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '1rem',
          marginTop: '1rem'
        }}>
          {scoreBreakdownData.map((item, index) => (
            <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <div style={{
                width: '12px',
                height: '12px',
                backgroundColor: item.color,
                borderRadius: '2px'
              }} />
              <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                {item.name}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Component Values */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <BarChart3 size={20} />
          <h3>Component Values</h3>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={componentData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis 
              dataKey="name" 
              tick={{ fontSize: 12, fill: '#6b7280' }}
              tickLine={{ stroke: '#e5e7eb' }}
            />
            <YAxis 
              tick={{ fontSize: 12, fill: '#6b7280' }}
              tickLine={{ stroke: '#e5e7eb' }}
            />
            <Tooltip 
              formatter={(value, name) => [value.toFixed(3), name]}
              labelStyle={{ color: '#1f2937' }}
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '6px'
              }}
            />
            <Bar 
              dataKey="value" 
              radius={[4, 4, 0, 0]}
            >
              {componentData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Financial Ratios */}
      {ratioData.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <TrendingUp size={20} />
            <h3>Financial Ratios</h3>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ratioData} layout="horizontal">
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis 
                type="number"
                tick={{ fontSize: 12, fill: '#6b7280' }}
                tickLine={{ stroke: '#e5e7eb' }}
              />
              <YAxis 
                type="category"
                dataKey="name"
                tick={{ fontSize: 12, fill: '#6b7280' }}
                tickLine={{ stroke: '#e5e7eb' }}
                width={120}
              />
              <Tooltip 
                formatter={(value, name) => [typeof value === 'number' ? value.toFixed(4) : value, name]}
                labelStyle={{ color: '#1f2937' }}
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px'
                }}
              />
              <Bar 
                dataKey="value" 
                fill="#8b5cf6"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default FinancialCharts;