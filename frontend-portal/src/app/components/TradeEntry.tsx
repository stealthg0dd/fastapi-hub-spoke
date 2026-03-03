import { useState } from 'react';
import { motion } from 'motion/react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface TradeEntryProps {
  onTrade: (side: 'BUY' | 'SELL', sentiment: number) => void;
  disabled?: boolean;
}

export function TradeEntry({ onTrade, disabled = false }: TradeEntryProps) {
  const [sentiment, setSentiment] = useState(0.5);
  const [amount, setAmount] = useState('');
  const [price, setPrice] = useState('');

  const isGreed = sentiment >= 1.0;
  const isFear = sentiment <= 0.0;

  const getSentimentLabel = () => {
    if (sentiment >= 0.9) return 'EXTREME GREED';
    if (sentiment >= 0.7) return 'GREED';
    if (sentiment >= 0.4) return 'NEUTRAL';
    if (sentiment >= 0.2) return 'FEAR';
    return 'EXTREME FEAR';
  };

  const getSentimentColor = () => {
    if (sentiment >= 0.7) return '#FF3B69';
    if (sentiment >= 0.4) return '#F59E0B';
    return '#00C087';
  };

  const handleTrade = (side: 'BUY' | 'SELL') => {
    if (!disabled) {
      onTrade(side, sentiment);
    }
  };

  return (
    <motion.div 
      className={`bg-[#0D1117] rounded-lg border border-[#1A1D23] p-4 ${disabled ? 'opacity-50' : ''}`}
      animate={{
        boxShadow: isGreed && !disabled
          ? '0 0 20px rgba(255, 59, 105, 0.5), 0 0 40px rgba(255, 59, 105, 0.3)'
          : '0 0 0 rgba(255, 59, 105, 0)'
      }}
      transition={{ duration: 0.3 }}
    >
      {disabled && (
        <div className="absolute inset-0 bg-[#0B0E11]/80 backdrop-blur-sm rounded-lg flex items-center justify-center z-10">
          <div className="text-center">
            <div className="text-sm font-mono text-[#FF3B69] mb-1">🔒 TRADING FROZEN</div>
            <div className="text-xs font-mono text-gray-500">Emotional Breaker Active</div>
          </div>
        </div>
      )}
      
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="text-xs font-mono text-gray-400 tracking-wider">TRADE ENTRY</div>
          {isGreed && !disabled && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#FF3B69]/20 text-[#FF3B69] border border-[#FF3B69]"
            >
              ⚠️ OVERCONFIDENCE DETECTED
            </motion.div>
          )}
        </div>

        {/* Input Fields */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] font-mono text-gray-500 mb-1 block">SHARES</label>
            <input
              type="text"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              disabled={disabled}
              className="w-full bg-[#0B0E11] border border-[#1A1D23] rounded px-3 py-2 text-sm font-mono text-white placeholder-gray-600 focus:outline-none focus:border-[#F59E0B] transition-colors disabled:opacity-50"
            />
          </div>
          <div>
            <label className="text-[10px] font-mono text-gray-500 mb-1 block">PRICE</label>
            <input
              type="text"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="Market"
              disabled={disabled}
              className="w-full bg-[#0B0E11] border border-[#1A1D23] rounded px-3 py-2 text-sm font-mono text-white placeholder-gray-600 focus:outline-none focus:border-[#F59E0B] transition-colors disabled:opacity-50"
            />
          </div>
        </div>

        {/* Sentiment Slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-[10px] font-mono text-gray-500">CONFIDENCE / SENTIMENT</label>
            <motion.div 
              className="text-xs font-mono px-2 py-0.5 rounded"
              style={{ 
                backgroundColor: `${getSentimentColor()}20`,
                color: getSentimentColor()
              }}
              animate={{
                scale: isGreed && !disabled ? [1, 1.05, 1] : 1
              }}
              transition={{
                duration: 0.5,
                repeat: isGreed && !disabled ? Infinity : 0
              }}
            >
              {getSentimentLabel()}
            </motion.div>
          </div>
          
          <div className="relative pt-2">
            {/* Slider Track Background */}
            <div className="absolute top-1/2 left-0 right-0 h-1.5 -translate-y-1/2 rounded-full overflow-hidden">
              <div 
                className="absolute inset-0"
                style={{
                  background: 'linear-gradient(to right, #00C087 0%, #F59E0B 50%, #FF3B69 100%)'
                }}
              />
            </div>
            
            {/* Slider */}
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={sentiment}
              onChange={(e) => setSentiment(parseFloat(e.target.value))}
              disabled={disabled}
              className="relative w-full appearance-none bg-transparent cursor-pointer z-10 disabled:cursor-not-allowed"
              style={{
                WebkitAppearance: 'none',
              }}
            />
            
            {/* Labels */}
            <div className="flex justify-between text-[9px] font-mono text-gray-600 mt-1">
              <span>FEAR</span>
              <span>NEUTRAL</span>
              <span>GREED</span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3">
          <motion.button
            whileHover={{ scale: disabled ? 1 : 1.02 }}
            whileTap={{ scale: disabled ? 1 : 0.98 }}
            onClick={() => handleTrade('BUY')}
            disabled={disabled}
            className="flex items-center justify-center gap-2 bg-[#00C087] hover:bg-[#00C087]/90 text-white rounded py-2.5 transition-colors font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <TrendingUp className="w-4 h-4" />
            BUY
          </motion.button>
          <motion.button
            whileHover={{ scale: disabled ? 1 : 1.02 }}
            whileTap={{ scale: disabled ? 1 : 0.98 }}
            onClick={() => handleTrade('SELL')}
            disabled={disabled}
            className="flex items-center justify-center gap-2 bg-[#FF3B69] hover:bg-[#FF3B69]/90 text-white rounded py-2.5 transition-colors font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <TrendingDown className="w-4 h-4" />
            SELL
          </motion.button>
        </div>
      </div>

      <style>{`
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: white;
          cursor: pointer;
          box-shadow: 0 0 0 2px ${getSentimentColor()}, 0 2px 8px rgba(0,0,0,0.5);
          transition: all 0.2s;
        }
        
        input[type="range"]::-webkit-slider-thumb:hover {
          width: 18px;
          height: 18px;
        }
        
        input[type="range"]::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: white;
          cursor: pointer;
          border: none;
          box-shadow: 0 0 0 2px ${getSentimentColor()}, 0 2px 8px rgba(0,0,0,0.5);
          transition: all 0.2s;
        }
        
        input[type="range"]::-moz-range-thumb:hover {
          width: 18px;
          height: 18px;
        }
      `}</style>
    </motion.div>
  );
}