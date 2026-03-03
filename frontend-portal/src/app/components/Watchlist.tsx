import { useState } from 'react';
import { Star, Plus, X, TrendingUp, TrendingDown } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface WatchlistStock {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
}

interface WatchlistProps {
  onSelectTicker: (ticker: string) => void;
}

export function Watchlist({ onSelectTicker }: WatchlistProps) {
  const [watchlist, setWatchlist] = useState<WatchlistStock[]>([
    { ticker: 'AAPL', price: 178.52, change: 2.34, changePercent: 1.33 },
    { ticker: 'TSLA', price: 242.84, change: -5.16, changePercent: -2.08 },
    { ticker: 'NVDA', price: 875.28, change: 12.45, changePercent: 1.44 },
    { ticker: 'MSFT', price: 420.55, change: 3.22, changePercent: 0.77 },
  ]);

  const [showAddForm, setShowAddForm] = useState(false);
  const [newTicker, setNewTicker] = useState('');

  const handleAddTicker = () => {
    if (!newTicker) return;
    
    // Mock adding new ticker
    const mockPrice = 100 + Math.random() * 500;
    const mockChange = (Math.random() - 0.5) * 10;
    setWatchlist([
      ...watchlist,
      {
        ticker: newTicker.toUpperCase(),
        price: mockPrice,
        change: mockChange,
        changePercent: (mockChange / mockPrice) * 100,
      },
    ]);
    setNewTicker('');
    setShowAddForm(false);
  };

  const handleRemoveTicker = (ticker: string) => {
    setWatchlist(watchlist.filter(s => s.ticker !== ticker));
  };

  return (
    <div className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Star className="w-4 h-4 text-[#F59E0B]" />
          <span className="text-xs font-mono text-gray-400 uppercase tracking-wider">Watchlist</span>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="p-1 hover:bg-white/5 rounded transition-colors"
          title="Add to watchlist"
        >
          {showAddForm ? (
            <X className="w-3.5 h-3.5 text-gray-500" />
          ) : (
            <Plus className="w-3.5 h-3.5 text-gray-500" />
          )}
        </button>
      </div>

      <AnimatePresence>
        {showAddForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3"
          >
            <div className="flex gap-2">
              <input
                type="text"
                value={newTicker}
                onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && handleAddTicker()}
                placeholder="TICKER"
                className="flex-1 bg-[#0B0E11] border border-[#1A1D23] rounded px-2 py-1.5 text-xs font-mono text-white placeholder-gray-600 focus:outline-none focus:border-[#F59E0B]/50"
              />
              <button
                onClick={handleAddTicker}
                className="px-3 py-1.5 bg-[#00C087] hover:bg-[#00C087]/90 rounded text-xs font-mono text-white transition-colors"
              >
                Add
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 overflow-y-auto space-y-2">
        {watchlist.map((stock) => (
          <motion.div
            key={stock.ticker}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="group"
          >
            <button
              onClick={() => onSelectTicker(stock.ticker)}
              className="w-full bg-[#0B0E11] border border-[#1A1D23] rounded p-2.5 hover:bg-white/5 transition-colors relative"
            >
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemoveTicker(stock.ticker);
                }}
                className="absolute top-1 right-1 p-1 opacity-0 group-hover:opacity-100 hover:bg-[#FF3B69]/10 rounded transition-all"
                title="Remove from watchlist"
              >
                <X className="w-2.5 h-2.5 text-gray-600 hover:text-[#FF3B69]" />
              </button>

              <div className="flex items-start justify-between mb-1">
                <span className="text-sm font-mono text-white font-semibold">{stock.ticker}</span>
                <div className={`flex items-center gap-1 ${stock.change >= 0 ? 'text-[#00C087]' : 'text-[#FF3B69]'}`}>
                  {stock.change >= 0 ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                </div>
              </div>

              <div className="flex items-end justify-between">
                <span className="text-xs font-mono text-gray-400">${stock.price.toFixed(2)}</span>
                <div className="text-[10px] font-mono">
                  <span className={stock.change >= 0 ? 'text-[#00C087]' : 'text-[#FF3B69]'}>
                    {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}
                  </span>
                  <span className="text-gray-600 ml-1">
                    ({stock.changePercent >= 0 ? '+' : ''}{stock.changePercent.toFixed(2)}%)
                  </span>
                </div>
              </div>
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
