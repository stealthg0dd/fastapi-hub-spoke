import { useState, useRef, useEffect } from 'react';
import { Search, TrendingUp } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface Stock {
  ticker: string;
  name: string;
  exchange: 'NYSE' | 'NASDAQ';
  price: number;
}

// Mock stock directory - in production this would be from an API
const STOCK_DIRECTORY: Stock[] = [
  { ticker: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ', price: 178.52 },
  { ticker: 'TSLA', name: 'Tesla, Inc.', exchange: 'NASDAQ', price: 242.84 },
  { ticker: 'NVDA', name: 'NVIDIA Corporation', exchange: 'NASDAQ', price: 875.28 },
  { ticker: 'MSFT', name: 'Microsoft Corporation', exchange: 'NASDAQ', price: 420.55 },
  { ticker: 'GOOGL', name: 'Alphabet Inc.', exchange: 'NASDAQ', price: 142.65 },
  { ticker: 'AMZN', name: 'Amazon.com, Inc.', exchange: 'NASDAQ', price: 178.25 },
  { ticker: 'META', name: 'Meta Platforms, Inc.', exchange: 'NASDAQ', price: 512.32 },
  { ticker: 'AMD', name: 'Advanced Micro Devices', exchange: 'NASDAQ', price: 142.18 },
  { ticker: 'JPM', name: 'JPMorgan Chase & Co.', exchange: 'NYSE', price: 218.75 },
  { ticker: 'BAC', name: 'Bank of America Corp', exchange: 'NYSE', price: 42.18 },
  { ticker: 'WFC', name: 'Wells Fargo & Company', exchange: 'NYSE', price: 65.42 },
  { ticker: 'GS', name: 'Goldman Sachs Group', exchange: 'NYSE', price: 528.65 },
  { ticker: 'V', name: 'Visa Inc.', exchange: 'NYSE', price: 298.42 },
  { ticker: 'MA', name: 'Mastercard Inc.', exchange: 'NYSE', price: 512.88 },
  { ticker: 'DIS', name: 'Walt Disney Company', exchange: 'NYSE', price: 112.45 },
  { ticker: 'NFLX', name: 'Netflix, Inc.', exchange: 'NASDAQ', price: 685.42 },
  { ticker: 'SPY', name: 'SPDR S&P 500 ETF', exchange: 'NYSE', price: 548.22 },
  { ticker: 'QQQ', name: 'Invesco QQQ Trust', exchange: 'NASDAQ', price: 472.18 },
];

interface TickerSearchProps {
  onSelectTicker: (stock: Stock) => void;
  currentTicker?: string;
}

export function TickerSearch({ onSelectTicker, currentTicker }: TickerSearchProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [filteredStocks, setFilteredStocks] = useState<Stock[]>([]);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.length > 0) {
      const filtered = STOCK_DIRECTORY.filter(stock => 
        stock.ticker.toLowerCase().includes(query.toLowerCase()) ||
        stock.name.toLowerCase().includes(query.toLowerCase())
      ).slice(0, 8);
      setFilteredStocks(filtered);
      setIsOpen(filtered.length > 0);
    } else {
      setFilteredStocks([]);
      setIsOpen(false);
    }
  }, [query]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (stock: Stock) => {
    setQuery('');
    setIsOpen(false);
    onSelectTicker(stock);
  };

  return (
    <div ref={searchRef} className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value.toUpperCase())}
          onFocus={() => query.length > 0 && setIsOpen(true)}
          placeholder="Search ticker or company..."
          className="w-full bg-[#0D1117] border border-[#1A1D23] rounded px-10 py-2 text-sm font-mono text-white placeholder-gray-600 focus:outline-none focus:border-[#F59E0B]/50"
        />
        {currentTicker && !query && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            <span className="text-xs font-mono text-[#00C087]">{currentTicker}</span>
            <TrendingUp className="w-3 h-3 text-[#00C087]" />
          </div>
        )}
      </div>

      <AnimatePresence>
        {isOpen && filteredStocks.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute z-50 w-full mt-2 bg-[#0D1117] border border-[#1A1D23] rounded-lg shadow-xl overflow-hidden"
          >
            {filteredStocks.map((stock) => (
              <button
                key={stock.ticker}
                onClick={() => handleSelect(stock)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors text-left border-b border-[#1A1D23] last:border-b-0"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-mono text-white font-semibold">{stock.ticker}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1A1D23] text-gray-400">
                      {stock.exchange}
                    </span>
                  </div>
                  <div className="text-xs font-mono text-gray-500">{stock.name}</div>
                </div>
                <div className="text-sm font-mono text-gray-400">${stock.price.toFixed(2)}</div>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
