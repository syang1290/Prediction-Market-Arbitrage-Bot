import { useEffect, useState } from 'react';
import './index.css';

interface ArbitrageOpportunity {
  type: string;
  route: string;
  market_name: string;
  kalshi_ticker: string;
  leg1: string;
  leg2: string;
  quantity: number;
  total_cost: number;
  net_profit: number;
  roi_pct: number;
  timestamp: number;
}

export default function App() {
  const [opportunities, setOpportunities] = useState<ArbitrageOpportunity[]>([]);
  const [, setIsConnected] = useState<boolean>(false);

  useEffect(() => {
    const BACKEND_URL = 'https://prediction-market-arbitrage-bot-2k7x.onrender.com';
    const ws = new WebSocket(BACKEND_URL);

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);

    ws.onmessage = (event) => {
      const data: ArbitrageOpportunity = JSON.parse(event.data);
      setOpportunities((prev) => [data, ...prev.slice(0, 49)]); 
    };

    return () => ws.close();
  }, []);

  return (
    <div style={{ padding: '24px', fontFamily: 'var(--sans)', backgroundColor: '#0f172a', minHeight: '100vh', color: '#f8fafc' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: 0, color: '#f8fafc' }}>Prediction Market Arbitrage Scanner</h1>
        </div>
      </header>

      <div style={{ backgroundColor: '#1e293b', borderRadius: '8px', overflow: 'hidden', border: '1px solid #334155' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
          <thead style={{ backgroundColor: '#0f172a', color: '#cbd5e1', fontSize: '14px' }}>
            <tr>
              <th style={{ padding: '12px 16px' }}>Event</th>
              <th style={{ padding: '12px 16px' }}>Strategy</th>
              <th style={{ padding: '12px 16px' }}>Execution Legs</th>
              <th style={{ padding: '12px 16px' }}>Size</th>
              <th style={{ padding: '12px 16px' }}>Cost</th>
              <th style={{ padding: '12px 16px' }}>Net Profit</th>
              <th style={{ padding: '12px 16px' }}>ROI</th>
            </tr>
          </thead>
          <tbody>
            {opportunities.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                  Go grab a coffee while you wait for arbitrage opportunities...
                </td>
              </tr>
            ) : (
              opportunities.map((opp, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '12px 16px', fontWeight: '500' }}>{opp.market_name}</td>
                  <td style={{ padding: '12px 16px', color: '#38bdf8' }}>{opp.route}</td>
                  <td style={{ padding: '12px 16px', fontSize: '13px' }}>
                    <div>{opp.leg1}</div>
                    <div style={{ color: '#94a3b8' }}>{opp.leg2}</div>
                  </td>
                  <td style={{ padding: '12px 16px' }}>{opp.quantity}</td>
                  <td style={{ padding: '12px 16px' }}>${opp.total_cost.toFixed(2)}</td>
                  <td style={{ padding: '12px 16px', color: '#4ade80', fontWeight: 'bold' }}>+${opp.net_profit.toFixed(2)}</td>
                  <td style={{ padding: '12px 16px', color: '#4ade80' }}>+{opp.roi_pct.toFixed(2)}%</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}