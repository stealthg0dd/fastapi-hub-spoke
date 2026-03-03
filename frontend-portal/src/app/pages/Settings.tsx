import { useState } from 'react';
import { useNavigate } from 'react-router';
import { ArrowLeft, Key, Plus, Trash2, Eye, EyeOff, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { motion } from 'motion/react';

interface ApiKey {
  id: string;
  name: string;
  broker: string;
  apiKey: string;
  secretKey: string;
  isActive: boolean;
  createdAt: number;
}

export function Settings() {
  const navigate = useNavigate();
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([
    {
      id: '1',
      name: 'Primary Trading Account',
      broker: 'binance',
      apiKey: 'sk_live_51K8***************************',
      secretKey: '***************************',
      isActive: true,
      createdAt: Date.now() - 86400000 * 5
    }
  ]);

  const [showAddForm, setShowAddForm] = useState(false);
  const [newKey, setNewKey] = useState({
    name: '',
    broker: '',
    apiKey: '',
    secretKey: ''
  });

  const [visibleKeys, setVisibleKeys] = useState<{ [key: string]: boolean }>({});

  const brokers = [
    { value: 'binance', label: 'Binance' },
    { value: 'metatrader', label: 'MetaTrader' },
    { value: 'tradovate', label: 'Tradovate' },
    { value: 'coinbase', label: 'Coinbase Pro' },
    { value: 'kraken', label: 'Kraken' },
    { value: 'interactive-brokers', label: 'Interactive Brokers' },
    { value: 'alpaca', label: 'Alpaca' },
    { value: 'bybit', label: 'Bybit' },
  ];

  const handleAddKey = () => {
    if (!newKey.name || !newKey.broker || !newKey.apiKey || !newKey.secretKey) {
      return;
    }

    const newApiKey: ApiKey = {
      id: Date.now().toString(),
      name: newKey.name,
      broker: newKey.broker,
      apiKey: newKey.apiKey.substring(0, 10) + '*'.repeat(newKey.apiKey.length - 10),
      secretKey: '*'.repeat(newKey.secretKey.length),
      isActive: true,
      createdAt: Date.now()
    };

    setApiKeys([...apiKeys, newApiKey]);
    setNewKey({ name: '', broker: '', apiKey: '', secretKey: '' });
    setShowAddForm(false);
  };

  const handleDeleteKey = (id: string) => {
    setApiKeys(apiKeys.filter(key => key.id !== id));
  };

  const toggleKeyVisibility = (id: string) => {
    setVisibleKeys({ ...visibleKeys, [id]: !visibleKeys[id] });
  };

  const toggleKeyStatus = (id: string) => {
    setApiKeys(apiKeys.map(key =>
      key.id === id ? { ...key, isActive: !key.isActive } : key
    ));
  };

  return (
    <div className="min-h-screen bg-[#0B0E11] text-white">
      {/* Header */}
      <div className="bg-[#0D1117] border-b border-[#1A1D23] px-6 py-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-white/5 rounded transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </button>
          <div>
            <h1 className="text-lg font-mono text-white">Settings & Integration</h1>
            <p className="text-xs font-mono text-gray-500">Broker API Connections</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto p-6">
        {/* Info Box */}
        <div className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <Key className="w-5 h-5 text-[#F59E0B] mt-0.5 shrink-0" />
            <div>
              <h3 className="text-sm font-mono text-white mb-1">API Key Security</h3>
              <p className="text-xs font-mono text-gray-400 leading-relaxed">
                Neufin acts as middleware between your broker and the AI. Your API keys are encrypted and never shared.
                We only use them to fetch trade data and execute orders through your broker's official API.
              </p>
            </div>
          </div>
        </div>

        {/* Add New Key Button */}
        {!showAddForm && (
          <Button
            onClick={() => setShowAddForm(true)}
            className="mb-6 bg-[#F59E0B] hover:bg-[#F59E0B]/90 text-white font-mono"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Broker Connection
          </Button>
        )}

        {/* Add New Key Form */}
        {showAddForm && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-6 mb-6"
          >
            <h3 className="text-sm font-mono text-white mb-4">New Broker Connection</h3>
            <div className="space-y-4">
              <div>
                <Label className="text-xs font-mono text-gray-400 mb-2 block">Connection Name</Label>
                <Input
                  value={newKey.name}
                  onChange={(e) => setNewKey({ ...newKey, name: e.target.value })}
                  placeholder="e.g., Primary Trading Account"
                  className="bg-[#0B0E11] border-[#1A1D23] text-white font-mono text-sm"
                />
              </div>

              <div>
                <Label className="text-xs font-mono text-gray-400 mb-2 block">Broker</Label>
                <Select value={newKey.broker} onValueChange={(value) => setNewKey({ ...newKey, broker: value })}>
                  <SelectTrigger className="bg-[#0B0E11] border-[#1A1D23] text-white font-mono text-sm">
                    <SelectValue placeholder="Select broker" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0D1117] border-[#1A1D23]">
                    {brokers.map(broker => (
                      <SelectItem key={broker.value} value={broker.value} className="font-mono text-sm text-white">
                        {broker.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-xs font-mono text-gray-400 mb-2 block">API Key</Label>
                <Input
                  value={newKey.apiKey}
                  onChange={(e) => setNewKey({ ...newKey, apiKey: e.target.value })}
                  placeholder="Enter your API key"
                  className="bg-[#0B0E11] border-[#1A1D23] text-white font-mono text-sm"
                  type="password"
                />
              </div>

              <div>
                <Label className="text-xs font-mono text-gray-400 mb-2 block">Secret Key</Label>
                <Input
                  value={newKey.secretKey}
                  onChange={(e) => setNewKey({ ...newKey, secretKey: e.target.value })}
                  placeholder="Enter your secret key"
                  className="bg-[#0B0E11] border-[#1A1D23] text-white font-mono text-sm"
                  type="password"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <Button
                  onClick={handleAddKey}
                  className="bg-[#00C087] hover:bg-[#00C087]/90 text-white font-mono"
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Add Connection
                </Button>
                <Button
                  onClick={() => {
                    setShowAddForm(false);
                    setNewKey({ name: '', broker: '', apiKey: '', secretKey: '' });
                  }}
                  variant="outline"
                  className="bg-transparent border-[#1A1D23] text-gray-400 hover:bg-white/5 font-mono"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        {/* API Keys List */}
        <div className="space-y-4">
          <h3 className="text-xs font-mono text-gray-400 tracking-wider">CONNECTED BROKERS</h3>
          
          {apiKeys.length === 0 ? (
            <div className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-8 text-center">
              <AlertCircle className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <p className="text-sm font-mono text-gray-500">No broker connections yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {apiKeys.map(key => (
                <motion.div
                  key={key.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="bg-[#0D1117] border border-[#1A1D23] rounded-lg p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h4 className="text-sm font-mono text-white">{key.name}</h4>
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#1A1D23] text-gray-400 uppercase">
                          {brokers.find(b => b.value === key.broker)?.label || key.broker}
                        </span>
                        <button
                          onClick={() => toggleKeyStatus(key.id)}
                          className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                            key.isActive
                              ? 'bg-[#00C087]/20 text-[#00C087] border-[#00C087]'
                              : 'bg-[#6B7280]/20 text-[#6B7280] border-[#6B7280]'
                          }`}
                        >
                          {key.isActive ? 'ACTIVE' : 'INACTIVE'}
                        </button>
                      </div>

                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-gray-600">API Key:</span>
                          <code className="text-xs font-mono text-gray-400">
                            {visibleKeys[key.id] ? key.apiKey : key.apiKey}
                          </code>
                          <button
                            onClick={() => toggleKeyVisibility(key.id)}
                            className="p-1 hover:bg-white/5 rounded transition-colors"
                          >
                            {visibleKeys[key.id] ? (
                              <EyeOff className="w-3 h-3 text-gray-500" />
                            ) : (
                              <Eye className="w-3 h-3 text-gray-500" />
                            )}
                          </button>
                        </div>
                        
                        <div className="text-[10px] font-mono text-gray-600">
                          Added {new Date(key.createdAt).toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric', 
                            year: 'numeric' 
                          })}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteKey(key.id)}
                      className="p-2 hover:bg-[#FF3B69]/10 rounded transition-colors group"
                      title="Delete connection"
                    >
                      <Trash2 className="w-4 h-4 text-gray-600 group-hover:text-[#FF3B69]" />
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Security Notice */}
        <div className="mt-8 bg-[#0D1117] border border-[#F59E0B]/30 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-[#F59E0B] mt-0.5 shrink-0" />
            <div>
              <h3 className="text-sm font-mono text-white mb-1">Important Security Notes</h3>
              <ul className="text-xs font-mono text-gray-400 space-y-1 leading-relaxed">
                <li>• Ensure API keys have trading permissions enabled in your broker account</li>
                <li>• Use IP whitelisting when available for additional security</li>
                <li>• Never share your API keys or secret keys with anyone</li>
                <li>• Neufin encrypts all credentials using industry-standard AES-256 encryption</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}