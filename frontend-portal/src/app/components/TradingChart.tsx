import { useState, useMemo } from 'react';
import { generateLiquidityData } from '../utils/mockData';
import type { LiquidityLevel } from '../types/trading';

interface TradingChartProps {
  ticker?: string;
  currentPrice?: number;
}

export function TradingChart({ ticker = 'AAPL', currentPrice = 178.52 }: TradingChartProps) {
  const [liquidityLevels, setLiquidityLevels] = useState<LiquidityLevel[]>([]);

  // Generate chart data
  const candleData = useMemo(() => {
    const data = [];
    let basePrice = currentPrice - 5; // Start slightly below current
    
    for (let i = 0; i < 100; i++) {
      const change = (Math.random() - 0.5) * 1.5; // Smaller movements for stocks
      basePrice += change;
      
      const open = basePrice;
      const close = basePrice + (Math.random() - 0.5) * 1.2;
      const high = Math.max(open, close) + Math.random() * 0.8;
      const low = Math.min(open, close) - Math.random() * 0.8;
      
      data.push({ open, high, low, close, index: i });
    }
    
    // Update last candle to current price
    if (data.length > 0) {
      data[data.length - 1].close = currentPrice;
      data[data.length - 1].high = Math.max(data[data.length - 1].high, currentPrice);
      data[data.length - 1].low = Math.min(data[data.length - 1].low, currentPrice);
    }
    
    return data;
  }, [currentPrice, ticker]);

  useMemo(() => {
    setLiquidityLevels(generateLiquidityData(currentPrice));
  }, [currentPrice, ticker]);

  return (
    <div className="relative h-full w-full bg-[#0B0E11] rounded-lg border border-[#1A1D23] overflow-hidden">
      {/* Chart Canvas */}
      <div className="absolute inset-0" style={{ paddingRight: '160px' }}>
        <svg width="100%" height="100%" className="overflow-visible">
          {/* Grid Lines */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1A1D23" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          
          {/* Candlesticks */}
          <g>
            {candleData.map((candle, i) => {
              const x = (i / candleData.length) * 100;
              const width = (1 / candleData.length) * 90;
              
              const maxPrice = Math.max(...candleData.map(c => c.high));
              const minPrice = Math.min(...candleData.map(c => c.low));
              const priceRange = maxPrice - minPrice;
              
              const yHigh = ((maxPrice - candle.high) / priceRange) * 90 + 5;
              const yLow = ((maxPrice - candle.low) / priceRange) * 90 + 5;
              const yOpen = ((maxPrice - candle.open) / priceRange) * 90 + 5;
              const yClose = ((maxPrice - candle.close) / priceRange) * 90 + 5;
              
              const isGreen = candle.close >= candle.open;
              const color = isGreen ? '#00C087' : '#FF3B69';
              
              return (
                <g key={i}>
                  {/* Wick */}
                  <line
                    x1={`${x + width / 2}%`}
                    y1={`${yHigh}%`}
                    x2={`${x + width / 2}%`}
                    y2={`${yLow}%`}
                    stroke={color}
                    strokeWidth="1"
                  />
                  {/* Body */}
                  <rect
                    x={`${x}%`}
                    y={`${Math.min(yOpen, yClose)}%`}
                    width={`${width}%`}
                    height={`${Math.max(0.5, Math.abs(yClose - yOpen))}%`}
                    fill={color}
                    opacity={isGreen ? 0.8 : 1}
                  />
                </g>
              );
            })}
          </g>
        </svg>
      </div>
      
      {/* Price Ladder (DOM) - Order Book */}
      <div className="absolute right-0 top-0 bottom-0 w-[160px] border-l border-[#1A1D23] bg-[#0D1117] overflow-hidden">
        <div className="sticky top-0 bg-[#0D1117] border-b border-[#1A1D23] px-2 py-1.5 text-[10px] font-mono text-gray-400">
          <div className="flex justify-between">
            <span>PRICE</span>
            <span>SIZE (00s)</span>
          </div>
        </div>
        <div className="h-full overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-gray-700">
          {liquidityLevels.map((level, idx) => {
            const isNearPrice = Math.abs(level.price - currentPrice) < 0.5;
            const heatmapOpacity = level.intensity * 0.4;
            const size = Math.floor(level.volume / 100); // Convert to hundreds of shares
            
            return (
              <div
                key={idx}
                className="relative px-2 py-0.5 text-[10px] font-mono border-b border-[#1A1D23]/30 hover:bg-white/5 cursor-pointer transition-colors"
                style={{
                  backgroundColor: level.price > currentPrice 
                    ? `rgba(0, 192, 135, ${heatmapOpacity})`
                    : `rgba(255, 59, 105, ${heatmapOpacity})`
                }}
              >
                <div className={`flex justify-between ${isNearPrice ? 'text-white font-bold' : 'text-gray-500'}`}>
                  <span>{level.price.toFixed(2)}</span>
                  <span className="text-gray-600">{size}</span>
                </div>
                {isNearPrice && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-full bg-amber-400" />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}