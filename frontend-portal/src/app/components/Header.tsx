import { Settings, Bell, User, BarChart3, Briefcase, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router';
import { signOut } from '../../utils/supabase';
//import logoImage from 'figma:asset/1e05f334cab806cc0d5cb5a632565c93d01080cd.png';//
const logoImage = "https://placehold.co/200x50?text=Neufin"

interface HeaderProps {
  currentPrice: number;
  priceChange: number;
  ticker?: string;
}

// Calculate days remaining in trial (7-day trial, started 3 days ago)
const TRIAL_START = Date.now() - (3 * 24 * 60 * 60 * 1000); // 3 days ago
const TRIAL_END = TRIAL_START + (7 * 24 * 60 * 60 * 1000); // 7 days total
const daysRemaining = Math.ceil((TRIAL_END - Date.now()) / (24 * 60 * 60 * 1000));

export function Header({ currentPrice, priceChange, ticker = 'AAPL' }: HeaderProps) {
  const navigate = useNavigate();
  const isPositive = priceChange >= 0;
  const trialIsEnding = daysRemaining <= 2; // Red when 2 days or less

  return (
    <div className="h-14 bg-[#0D1117] border-b border-[#1A1D23] flex items-center px-6 shrink-0">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/')} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <img src={logoImage} alt="Neufin AI" className="w-8 h-8" />
          <span className="text-lg font-mono text-white tracking-tight">Neufin AI</span>
        </button>
        <div className="h-4 w-px bg-[#1A1D23]" />
        <span className="text-xs font-mono text-gray-500 tracking-wider">US EQUITY TERMINAL</span>
      </div>
      
      <div className="ml-auto flex items-center gap-6">
        {/* Trial Status */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded border ${
          trialIsEnding 
            ? 'bg-[#FF3B69]/10 border-[#FF3B69]/30' 
            : 'bg-[#F59E0B]/10 border-[#F59E0B]/30'
        }`}>
          <div className={`w-1.5 h-1.5 rounded-full ${trialIsEnding ? 'bg-[#FF3B69]' : 'bg-[#F59E0B]'} animate-pulse`} />
          <span className={`text-xs font-mono ${trialIsEnding ? 'text-[#FF3B69]' : 'text-[#F59E0B]'}`}>
            Trial: {daysRemaining} {daysRemaining === 1 ? 'day' : 'days'} left
          </span>
        </div>

        {/* Current Market Data */}
        <div className="flex items-center gap-4">
          <div className="text-xs font-mono">
            <span className="text-gray-600">{ticker}</span>
            <span className="text-white ml-2">${currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            <span className={`ml-2 ${isPositive ? 'text-[#00C087]' : 'text-[#FF3B69]'}`}>
              {isPositive ? '+' : ''}{priceChange.toFixed(2)}%
            </span>
          </div>
          
          <div className="h-4 w-px bg-[#1A1D23]" />
          
          <div className="text-xs font-mono text-gray-600">
            VOL <span className="text-gray-400 ml-1">52.4M</span>
          </div>
        </div>

        {/* Action Icons */}
        <div className="flex items-center gap-2">
          <button 
            onClick={() => navigate('/analytics')}
            className="p-1.5 hover:bg-white/5 rounded transition-colors" 
            title="Analytics Dashboard"
          >
            <BarChart3 className="w-4 h-4 text-gray-500" />
          </button>
          <button
            onClick={() => navigate('/portfolio')}
            className="p-1.5 hover:bg-white/5 rounded transition-colors"
            title="Portfolio Manager"
          >
            <Briefcase className="w-4 h-4 text-gray-500" />
          </button>
          <button className="p-1.5 hover:bg-white/5 rounded transition-colors" title="Notifications">
            <Bell className="w-4 h-4 text-gray-500" />
          </button>
          <button 
            onClick={() => navigate('/settings')}
            className="p-1.5 hover:bg-white/5 rounded transition-colors" 
            title="Settings"
          >
            <Settings className="w-4 h-4 text-gray-500" />
          </button>
          <button className="p-1.5 hover:bg-white/5 rounded transition-colors" title="Profile">
            <User className="w-4 h-4 text-gray-500" />
          </button>
          <button
            onClick={() => signOut()}
            className="p-1.5 hover:bg-[#FF3B69]/10 rounded transition-colors"
            title="Logout"
          >
            <LogOut className="w-4 h-4 text-gray-500 hover:text-[#FF3B69]" />
          </button>
        </div>
      </div>
    </div>
  );
}