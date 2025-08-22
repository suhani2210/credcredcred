import React from 'react';
import { TrendingUp, Shield, BarChart3 } from 'lucide-react';

const Layout = ({ children }) => {
  return (
    <div>
      <header style={{
        background: 'linear-gradient(90deg, #1e3a8a 0%, #3730a3 100%)',
        color: 'white',
        padding: '1rem 2rem',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem'
        }}>
          <Shield size={32} />
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
            Company Credit Score Analyzer
          </h1>
          <div style={{
            marginLeft: 'auto',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem'
          }}>
            <TrendingUp size={24} />
            <BarChart3 size={24} />
          </div>
        </div>
      </header>
      {children}
    </div>
  );
};

export default Layout;