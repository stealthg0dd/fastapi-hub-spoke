import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { Info, AlertTriangle, CheckCircle, Target, Trophy, Zap, Star } from 'lucide-react';
import { Badge } from './ui/badge';
import { motion } from 'motion/react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from './ui/accordion';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { projectId } from '../utils/supabase/info';

const badgeStyles = {
  improving: { icon: Zap, color: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500/30' },
  champion: { icon: Trophy, color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' },
  master: { icon: Target, color: 'text-purple-400', bg: 'bg-purple-500/20', border: 'border-purple-500/30' },
  legend: { icon: Star, color: 'text-gold-400', bg: 'bg-gradient-to-r from-yellow-500/20 to-orange-500/20', border: 'border-yellow-500/30' }
};

const BiasCard = ({ bias, index }: { bias: any; index: number }) => {
  const badgeStyle = bias.badge ? badgeStyles[bias.badge as keyof typeof badgeStyles] : null;

  return (
    <AccordionItem value={bias.id} className="border-none">
      <div className={`p-4 rounded-lg transition-all ${
        bias.status === 'high' ? 'bg-red-500/5 border border-red-500/20' :
        bias.status === 'medium' ? 'bg-orange-500/5 border border-orange-500/20' : 
        'bg-green-500/5 border border-green-500/20'
      }`}>
        <AccordionTrigger className="hover:no-underline p-0 border-0">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center space-x-3">
              <div className={`p-2 rounded-full relative ${
                bias.status === 'high' ? 'bg-red-500/20' :
                bias.status === 'medium' ? 'bg-orange-500/20' : 'bg-green-500/20'
              }`}>
                {bias.status === 'high' ? (
                  <AlertTriangle className="h-4 w-4 text-red-400" />
                ) : bias.status === 'medium' ? (
                  <Target className="h-4 w-4 text-orange-400" />
                ) : (
                  <CheckCircle className="h-4 w-4 text-green-400" />
                )}
                {bias.streak > 0 && (
                  <motion.div
                    className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    {bias.streak}
                  </motion.div>
                )}
              </div>
              <div className="text-left">
                <div className="flex items-center space-x-2">
                  <h4 className="font-medium">{bias.name}</h4>
                  {badgeStyle && (
                    <motion.div
                      animate={{ y: [-2, 2, -2] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      <Badge className={`${badgeStyle.bg} ${badgeStyle.color} ${badgeStyle.border} text-xs flex items-center space-x-1`}>
                        <badgeStyle.icon className="h-3 w-3" />
                        <span>{bias.badge}</span>
                      </Badge>
                    </motion.div>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{bias.description}</p>
              </div>
            </div>
            <div className="text-right flex items-center space-x-4">
              <div>
                <p className="font-semibold text-red-400">${bias.impact.toLocaleString()}</p>
                <p className="text-xs text-muted-foreground">Lost potential</p>
              </div>
              <div className="text-center">
                <motion.div
                  className="text-lg font-bold"
                  animate={{ 
                    color: bias.progress > 80 ? '#10B981' : bias.progress > 50 ? '#F59E0B' : '#EF4444'
                  }}
                >
                  {bias.progress}%
                </motion.div>
                <p className="text-xs text-muted-foreground">Fixed</p>
              </div>
            </div>
          </div>
        </AccordionTrigger>
        
        <AccordionContent className="pt-4 pb-0">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Severity Level</span>
                  <span>{bias.severity}%</span>
                </div>
                <Progress 
                  value={bias.severity}
                  className="h-2"
                />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Improvement Progress</span>
                  <span>{bias.progress}%</span>
                </div>
                <Progress 
                  value={bias.progress}
                  className="h-2"
                />
              </div>
            </div>
            
            <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <div className="flex items-start space-x-2 mb-3">
                <div className="p-1 bg-blue-500/20 rounded-full mt-0.5">
                  <CheckCircle className="h-3 w-3 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-blue-400 mb-1">AI Recommendation</p>
                  <p className="text-sm text-muted-foreground">{bias.detailedTip}</p>
                </div>
              </div>
              
              <div className="space-y-2">
                <p className="text-xs font-medium text-blue-400">Action Items:</p>
                {bias.actionItems.map((action: string, idx: number) => (
                  <motion.div
                    key={idx}
                    className="flex items-center space-x-2 text-xs"
                    whileHover={{ x: 4 }}
                  >
                    <div className="w-1.5 h-1.5 bg-blue-400 rounded-full" />
                    <span>{action}</span>
                  </motion.div>
                ))}
              </div>
              
              <Button size="sm" className="w-full mt-3 bg-blue-600 hover:bg-blue-700">
                {bias.tip}
              </Button>
            </div>
          </div>
        </AccordionContent>
      </div>
    </AccordionItem>
  );
};

interface BiasBreakdownProps {
  accessToken?: string;
}

export function BiasBreakdown({ accessToken }: BiasBreakdownProps) {
  const [biasData, setBiasData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchBiasData = async () => {
      if (!accessToken) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(
          `https://${projectId}.supabase.co/functions/v1/make-server-22c8dcd8/bias/analysis`,
          {
            headers: {
              'Authorization': `Bearer ${accessToken}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.biases && data.biases.length > 0) {
            setBiasData(data.biases);
          }
        }
      } catch (error) {
        console.error('Error fetching bias data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchBiasData();
  }, [accessToken]);

  const totalImpact = biasData.reduce((sum, bias) => sum + (bias.impact || 0), 0);
  const averageProgress = biasData.length > 0 
    ? biasData.reduce((sum, bias) => sum + (bias.progress || 0), 0) / biasData.length 
    : 0;

  if (isLoading) {
    return (
      <Card className="bg-card/50">
        <CardContent className="p-8 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <AlertTriangle className="h-5 w-5 text-orange-400" />
            </motion.div>
            <CardTitle>Detailed Bias Breakdown</CardTitle>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="ghost" size="icon" className="h-6 w-6">
                  <Info className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80">
                <div className="space-y-2">
                  <h4 className="font-medium">Bias Analysis & Gamification</h4>
                  <p className="text-sm text-muted-foreground">
                    Track your progress in overcoming cognitive biases. Earn badges and maintain streaks 
                    to improve your Neural Twin Alpha Score.
                  </p>
                </div>
              </PopoverContent>
            </Popover>
          </div>
          <div className="flex items-center space-x-3">
            {totalImpact > 0 && (
              <motion.div
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 3, repeat: Infinity }}
              >
                <Badge variant="destructive" className="bg-red-500/20 text-red-400 border-red-500/30">
                  -${totalImpact.toLocaleString()} Impact
                </Badge>
              </motion.div>
            )}
            <Badge className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-blue-400 border-blue-500/30">
              {averageProgress.toFixed(0)}% Overall Progress
            </Badge>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {biasData.length > 0 ? (
          <>
            <Accordion type="multiple" className="space-y-4">
              {biasData.map((bias, index) => (
                <BiasCard key={bias.id} bias={bias} index={index} />
              ))}
            </Accordion>
            
            <motion.div 
              className="mt-6 p-4 bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/30 rounded-lg"
              animate={{ 
                boxShadow: ['0 0 0 0 rgba(34, 197, 94, 0)', '0 0 0 4px rgba(34, 197, 94, 0.1)', '0 0 0 0 rgba(34, 197, 94, 0)']
              }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <Trophy className="h-5 w-5 text-yellow-400" />
                  <span className="font-medium text-green-400">Weekly Challenge</span>
                </div>
                <Badge variant="secondary" className="text-xs bg-green-500/20 text-green-400">
                  Active
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                Keep improving your bias scores to unlock premium insights
              </p>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>🔥 Progress tracking active</span>
                <span>Check back for updates</span>
              </div>
            </motion.div>
          </>
        ) : (
          <div className="h-48 flex items-center justify-center">
            <div className="text-center">
              <p className="text-muted-foreground">No bias data available yet</p>
              <p className="text-xs text-muted-foreground mt-2">Analysis will appear as you trade</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
