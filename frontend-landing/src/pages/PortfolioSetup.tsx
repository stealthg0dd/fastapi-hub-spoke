import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Building2, Plus, Trash2, TrendingUp, AlertCircle, Check } from 'lucide-react';
import { motion } from 'motion/react';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { createClient } from '../utils/supabase/client';
import { projectId, publicAnonKey } from '../utils/supabase/info';

interface Holding {
  symbol: string;
  shares: number;
  avgCost: number;
}

export function PortfolioSetup() {
  const [setupMethod, setSetupMethod] = useState<'plaid' | 'manual' | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([{ symbol: '', shares: 0, avgCost: 0 }]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const navigate = useNavigate();
  const supabase = createClient();

  useEffect(() => {
    const getSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        navigate('/login');
      } else {
        setAccessToken(session.access_token);
      }
    };
    getSession();
  }, [navigate]);

  const addHolding = () => {
    setHoldings([...holdings, { symbol: '', shares: 0, avgCost: 0 }]);
  };

  const removeHolding = (index: number) => {
    setHoldings(holdings.filter((_, i) => i !== index));
  };

  const updateHolding = (index: number, field: keyof Holding, value: string | number) => {
    const newHoldings = [...holdings];
    newHoldings[index] = { ...newHoldings[index], [field]: value };
    setHoldings(newHoldings);
  };

  const handlePlaidSetup = async () => {
    setIsLoading(true);
    setError(null);

    try {
      if (!accessToken) {
        setError('Not authenticated. Please log in again.');
        setIsLoading(false);
        return;
      }

      // Create link token
      const linkTokenResponse = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-22c8dcd8/plaid/create-link-token`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
        }
      );

      // Check if response is JSON
      const contentType = linkTokenResponse.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        console.error('Non-JSON response from Plaid endpoint');
        setError('Plaid integration is not available. Please use Manual Entry instead.');
        setIsLoading(false);
        return;
      }

      if (!linkTokenResponse.ok) {
        const errorText = await linkTokenResponse.text();
        console.error('Plaid endpoint error:', errorText);
        setError('Plaid integration is not configured. Please use Manual Entry instead.');
        setIsLoading(false);
        return;
      }

      const linkTokenData = await linkTokenResponse.json();

      if (linkTokenData.error) {
        setError(linkTokenData.message || 'Plaid integration requires setup. Please configure PLAID_CLIENT_ID and PLAID_SECRET in Supabase dashboard, or use Manual Entry.');
        setIsLoading(false);
        return;
      }

      if (!linkTokenData.link_token) {
        setError('Failed to create Plaid link token. Please use Manual Entry or contact support.');
        setIsLoading(false);
        return;
      }

      // Load Plaid Link script dynamically
      if (!(window as any).Plaid) {
        const script = document.createElement('script');
        script.src = 'https://cdn.plaid.com/link/v2/stable/link-initialize.js';
        script.async = true;
        document.body.appendChild(script);
        
        await new Promise((resolve) => {
          script.onload = resolve;
        });
      }

      // Initialize Plaid Link
      const handler = (window as any).Plaid.create({
        token: linkTokenData.link_token,
        onSuccess: async (public_token: string, metadata: any) => {
          setIsLoading(true);
          try {
            // Exchange public token for access token and get holdings
            const exchangeResponse = await fetch(
              `https://${projectId}.supabase.co/functions/v1/make-server-22c8dcd8/plaid/exchange-token`,
              {
                method: 'POST',
                headers: {
                  'Authorization': `Bearer ${accessToken}`,
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ public_token }),
              }
            );

            const exchangeData = await exchangeResponse.json();

            if (exchangeData.success) {
              setSuccess(true);
              setTimeout(() => {
                navigate('/user-dashboard');
              }, 2000);
            } else {
              throw new Error(exchangeData.error || 'Failed to sync portfolio');
            }
          } catch (err: any) {
            setError(err.message || 'Failed to sync portfolio from Plaid');
            setIsLoading(false);
          }
        },
        onExit: (err: any, metadata: any) => {
          setIsLoading(false);
          if (err) {
            console.error('Plaid Link error:', err);
            setError('Plaid connection was cancelled or failed. Please try again or use Manual Entry.');
          }
        },
        onEvent: (eventName: string, metadata: any) => {
          console.log('Plaid event:', eventName, metadata);
        },
      });

      // Open Plaid Link
      handler.open();
      setIsLoading(false);
      
    } catch (err: any) {
      console.error('Plaid setup error:', err);
      setError(err.message || 'Failed to connect with Plaid. Please use Manual Entry or contact support.');
      setIsLoading(false);
    }
  };

  const handleManualSave = async () => {
    if (!accessToken) {
      setError('Not authenticated. Please log in again.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Validate holdings
      const validHoldings = holdings.filter(h => h.symbol && h.shares > 0 && h.avgCost > 0);
      
      if (validHoldings.length === 0) {
        setError('Please add at least one valid holding');
        setIsLoading(false);
        return;
      }

      // Calculate portfolio value
      const totalValue = validHoldings.reduce((sum, h) => sum + (h.shares * h.avgCost), 0);

      const portfolioData = {
        holdings: validHoldings,
        totalValue,
        method: 'manual',
        setupCompletedAt: new Date().toISOString(),
      };

      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-22c8dcd8/portfolio/save`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(portfolioData),
        }
      );

      // Check content type
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        console.error('Non-JSON response from save endpoint');
        throw new Error('Server error. Please try again or contact support.');
      }

      const responseData = await response.json();
      console.log('Portfolio save response:', responseData);

      if (!response.ok) {
        throw new Error(responseData.error || 'Failed to save portfolio');
      }

      if (responseData.success) {
        setSuccess(true);
        console.log('Portfolio saved successfully, redirecting to dashboard...');
        setTimeout(() => {
          navigate('/user-dashboard');
        }, 2000);
      } else {
        throw new Error('Failed to save portfolio');
      }
    } catch (err: any) {
      console.error('Save portfolio error:', err);
      setError(err.message || 'Failed to save portfolio');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen py-12 px-4">
      <div className="container mx-auto max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          {/* Header */}
          <div className="text-center mb-8">
            <Badge className="bg-gradient-to-r from-purple-500/20 to-blue-500/20 text-purple-400 border-purple-500/30 mb-4">
              <TrendingUp className="h-3 w-3 mr-1" />
              Step 1: Portfolio Setup
            </Badge>
            
            <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--heading-primary)' }}>
              Connect Your Portfolio
            </h1>
            <p className="text-muted-foreground">
              Link your brokerage account or manually enter your holdings to get started
            </p>
          </div>

          {success && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg flex items-center space-x-3"
            >
              <Check className="h-5 w-5 text-green-400" />
              <p className="text-green-400">Portfolio saved successfully! Redirecting to dashboard...</p>
            </motion.div>
          )}

          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center space-x-3"
            >
              <AlertCircle className="h-5 w-5 text-red-400" />
              <p className="text-red-400">{error}</p>
            </motion.div>
          )}

          {!setupMethod ? (
            <>
              {/* Info Banner */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg"
              >
                <p className="text-sm text-blue-400">
                  <strong>Note:</strong> Plaid integration requires API credentials to be configured. 
                  If you encounter any issues with the brokerage connection, please use the Manual Entry option below.
                </p>
              </motion.div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Plaid Option */}
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card 
                    className="cursor-pointer hover:border-purple-500/50 transition-all h-full"
                    onClick={() => setSetupMethod('plaid')}
                  >
                  <CardHeader>
                    <div className="flex items-center space-x-3 mb-2">
                      <div className="p-3 bg-purple-500/20 rounded-lg">
                        <Building2 className="h-6 w-6 text-purple-400" />
                      </div>
                      <CardTitle>Connect Brokerage</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                      Securely connect your brokerage account via Plaid for automatic portfolio sync
                    </p>
                    <ul className="space-y-2 text-xs text-muted-foreground">
                      <li className="flex items-center space-x-2">
                        <div className="w-1.5 h-1.5 bg-green-400 rounded-full" />
                        <span>Real-time portfolio updates</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-1.5 h-1.5 bg-green-400 rounded-full" />
                        <span>Bank-level encryption</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-1.5 h-1.5 bg-green-400 rounded-full" />
                        <span>Automatic trade tracking</span>
                      </li>
                    </ul>
                    <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                      Recommended
                    </Badge>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Manual Option */}
              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Card 
                  className="cursor-pointer hover:border-purple-500/50 transition-all h-full"
                  onClick={() => setSetupMethod('manual')}
                >
                  <CardHeader>
                    <div className="flex items-center space-x-3 mb-2">
                      <div className="p-3 bg-blue-500/20 rounded-lg">
                        <Plus className="h-6 w-6 text-blue-400" />
                      </div>
                      <CardTitle>Manual Entry</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">
                      Manually enter your portfolio holdings and update them as needed
                    </p>
                    <ul className="space-y-2 text-xs text-muted-foreground">
                      <li className="flex items-center space-x-2">
                        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full" />
                        <span>Full control over data</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full" />
                        <span>No account linking required</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full" />
                        <span>Quick setup</span>
                      </li>
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>
              </div>
            </>
          ) : setupMethod === 'plaid' ? (
            <Card>
              <CardHeader>
                <CardTitle>Connect Your Brokerage Account</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                  <p className="text-sm text-yellow-400">
                    <strong>Note:</strong> Plaid integration requires additional API setup and credentials. 
                    For this demo, please use Manual Entry or contact support to enable Plaid integration.
                  </p>
                </div>

                <div className="flex space-x-4">
                  <Button
                    onClick={handlePlaidSetup}
                    disabled={isLoading}
                    className="bg-gradient-to-r from-purple-600 to-blue-600"
                  >
                    {isLoading ? 'Connecting...' : 'Launch Plaid Link'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setSetupMethod(null)}
                  >
                    Back to Options
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Enter Your Portfolio Holdings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  {holdings.map((holding, index) => (
                    <div key={index} className="flex gap-3 items-end">
                      <div className="flex-1">
                        <Label htmlFor={`symbol-${index}`}>Stock Symbol</Label>
                        <Input
                          id={`symbol-${index}`}
                          placeholder="AAPL"
                          value={holding.symbol}
                          onChange={(e) => updateHolding(index, 'symbol', e.target.value.toUpperCase())}
                          className="bg-background/50"
                        />
                      </div>
                      <div className="flex-1">
                        <Label htmlFor={`shares-${index}`}>Shares</Label>
                        <Input
                          id={`shares-${index}`}
                          type="number"
                          placeholder="100"
                          value={holding.shares || ''}
                          onChange={(e) => updateHolding(index, 'shares', parseFloat(e.target.value) || 0)}
                          className="bg-background/50"
                        />
                      </div>
                      <div className="flex-1">
                        <Label htmlFor={`avgCost-${index}`}>Avg Cost ($)</Label>
                        <Input
                          id={`avgCost-${index}`}
                          type="number"
                          step="0.01"
                          placeholder="150.00"
                          value={holding.avgCost || ''}
                          onChange={(e) => updateHolding(index, 'avgCost', parseFloat(e.target.value) || 0)}
                          className="bg-background/50"
                        />
                      </div>
                      {holdings.length > 1 && (
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => removeHolding(index)}
                          className="text-red-400 hover:text-red-300"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>

                <Button
                  variant="outline"
                  onClick={addHolding}
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Another Holding
                </Button>

                <Separator />

                <div className="flex space-x-4">
                  <Button
                    onClick={handleManualSave}
                    disabled={isLoading}
                    className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600"
                  >
                    {isLoading ? 'Saving...' : 'Save Portfolio'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setSetupMethod(null)}
                    disabled={isLoading}
                  >
                    Back
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </motion.div>
      </div>
    </div>
  );
}
