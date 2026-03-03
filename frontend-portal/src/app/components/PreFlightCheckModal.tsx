import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { AlertTriangle, Brain, CheckCircle2, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';
import { motion } from 'motion/react';

interface PreFlightCheckModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (thesis: string, sentiment: number) => void;
  tradeSide: 'BUY' | 'SELL';
  currentSentiment: number;
}

export function PreFlightCheckModal({
  isOpen,
  onClose,
  onConfirm,
  tradeSide,
  currentSentiment
}: PreFlightCheckModalProps) {
  const [thesis, setThesis] = useState('');
  const [sentiment, setSentiment] = useState(currentSentiment);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResults, setScanResults] = useState<{
    detected: boolean;
    biases: string[];
    riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  } | null>(null);

  useEffect(() => {
    setSentiment(currentSentiment);
  }, [currentSentiment]);

  const handleScan = async () => {
    setIsScanning(true);
    setScanResults(null);

    // Simulate AI analysis with Claude API
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Mock scan results based on sentiment
    const biasesDetected = [];
    let riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' = 'LOW';

    if (sentiment >= 0.8) {
      biasesDetected.push('FOMO (Fear of Missing Out)');
      biasesDetected.push('Overconfidence Bias');
      riskLevel = 'HIGH';
    } else if (sentiment >= 0.6) {
      biasesDetected.push('Anchoring Bias');
      riskLevel = 'MEDIUM';
    } else if (sentiment <= 0.2) {
      biasesDetected.push('Loss Aversion');
      biasesDetected.push('Panic Selling Pattern');
      riskLevel = 'HIGH';
    }

    if (thesis.length < 20) {
      biasesDetected.push('Insufficient Planning (Low Conviction)');
      riskLevel = riskLevel === 'LOW' ? 'MEDIUM' : 'HIGH';
    }

    setScanResults({
      detected: biasesDetected.length > 0,
      biases: biasesDetected,
      riskLevel
    });
    setIsScanning(false);
  };

  const handleConfirm = () => {
    onConfirm(thesis, sentiment);
    setThesis('');
    setScanResults(null);
    onClose();
  };

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

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'HIGH': return '#FF3B69';
      case 'MEDIUM': return '#F59E0B';
      default: return '#00C087';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-[#0D1117] border-[#1A1D23] text-white max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-mono">
            <Brain className="w-5 h-5 text-[#F59E0B]" />
            Pre-Flight Check • {tradeSide} Order
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {/* Trade Thesis */}
          <div className="space-y-2">
            <label className="text-xs font-mono text-gray-400">
              What is your trading thesis? <span className="text-[#FF3B69]">*</span>
            </label>
            <Textarea
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
              placeholder="Describe your analysis, entry reason, and exit plan..."
              className="bg-[#0B0E11] border-[#1A1D23] text-white placeholder-gray-600 font-mono text-sm min-h-[100px] resize-none focus:border-[#F59E0B]"
            />
            <p className="text-[10px] font-mono text-gray-600">
              {thesis.length} characters • Minimum 20 recommended
            </p>
          </div>

          {/* Sentiment Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-mono text-gray-400">Confidence / Sentiment</label>
              <motion.div
                className="text-xs font-mono px-2 py-0.5 rounded"
                style={{
                  backgroundColor: `${getSentimentColor()}20`,
                  color: getSentimentColor()
                }}
              >
                {getSentimentLabel()}
              </motion.div>
            </div>

            <div className="relative pt-2">
              <div className="absolute top-1/2 left-0 right-0 h-1.5 -translate-y-1/2 rounded-full overflow-hidden">
                <div
                  className="absolute inset-0"
                  style={{
                    background: 'linear-gradient(to right, #00C087 0%, #F59E0B 50%, #FF3B69 100%)'
                  }}
                />
              </div>

              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={sentiment}
                onChange={(e) => setSentiment(parseFloat(e.target.value))}
                className="relative w-full appearance-none bg-transparent cursor-pointer z-10"
                style={{ WebkitAppearance: 'none' }}
              />

              <div className="flex justify-between text-[9px] font-mono text-gray-600 mt-1">
                <span>FEAR</span>
                <span>NEUTRAL</span>
                <span>GREED</span>
              </div>
            </div>
          </div>

          {/* AI Pre-Scan */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-mono text-gray-400">AI Pre-Scan</label>
              <Button
                onClick={handleScan}
                disabled={isScanning || !thesis}
                size="sm"
                className="bg-[#8B5CF6] hover:bg-[#8B5CF6]/90 text-white font-mono text-xs h-8"
              >
                {isScanning ? (
                  <>
                    <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Brain className="w-3 h-3 mr-1.5" />
                    Run Claude Profiler
                  </>
                )}
              </Button>
            </div>

            {/* Scan Results */}
            {scanResults && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`bg-[#0B0E11] border rounded-lg p-4 ${
                  scanResults.detected ? 'border-[#FF3B69]' : 'border-[#00C087]'
                }`}
              >
                <div className="flex items-start gap-3">
                  {scanResults.detected ? (
                    <AlertTriangle className="w-5 h-5 text-[#FF3B69] mt-0.5 shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-[#00C087] mt-0.5 shrink-0" />
                  )}

                  <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-mono text-white">
                        {scanResults.detected ? 'Biases Detected' : 'No Significant Biases'}
                      </p>
                      <span
                        className="text-[10px] font-mono px-2 py-0.5 rounded border"
                        style={{
                          color: getRiskColor(scanResults.riskLevel),
                          borderColor: getRiskColor(scanResults.riskLevel),
                          backgroundColor: `${getRiskColor(scanResults.riskLevel)}20`
                        }}
                      >
                        {scanResults.riskLevel} RISK
                      </span>
                    </div>

                    {scanResults.biases.length > 0 && (
                      <ul className="space-y-1.5 text-xs font-mono text-gray-400">
                        {scanResults.biases.map((bias, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-[#FF3B69] mt-0.5">•</span>
                            <span>{bias}</span>
                          </li>
                        ))}
                      </ul>
                    )}

                    {!scanResults.detected && (
                      <p className="text-xs font-mono text-gray-400">
                        Your trade appears rational based on provided thesis and sentiment level.
                      </p>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t border-[#1A1D23]">
            <Button
              onClick={onClose}
              variant="outline"
              className="flex-1 bg-transparent border-[#1A1D23] text-gray-400 hover:bg-white/5 hover:text-white font-mono"
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={!thesis || thesis.length < 10}
              className={`flex-1 font-mono ${
                tradeSide === 'BUY'
                  ? 'bg-[#00C087] hover:bg-[#00C087]/90'
                  : 'bg-[#FF3B69] hover:bg-[#FF3B69]/90'
              } text-white`}
            >
              {tradeSide === 'BUY' ? (
                <TrendingUp className="w-4 h-4 mr-2" />
              ) : (
                <TrendingDown className="w-4 h-4 mr-2" />
              )}
              Confirm {tradeSide}
            </Button>
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
      </DialogContent>
    </Dialog>
  );
}
