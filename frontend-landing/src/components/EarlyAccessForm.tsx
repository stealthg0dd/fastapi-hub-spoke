import { useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'motion/react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { X, Sparkles, CheckCircle, Mail, Phone, User, TrendingUp, Building2 } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

/* Works through Vite proxy in dev (/api → localhost:8000) and Vercel routes in prod */
const API_BASE = '/api/v1';

interface EarlyAccessFormProps {
  isOpen: boolean;
  onClose: () => void;
}

export function EarlyAccessForm({ isOpen, onClose }: EarlyAccessFormProps) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    portfolioSize: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      /* Route to FastAPI backend → emails info@neufin.ai */
      await axios.post(`${API_BASE}/concierge/waitlist`, {
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        company: formData.company || '',
        portfolio_size: formData.portfolioSize || '',
      });

      /* Also persist locally as backup */
      const submissions = JSON.parse(localStorage.getItem('neufin_early_access') || '[]');
      submissions.push({ ...formData, submittedAt: new Date().toISOString() });
      localStorage.setItem('neufin_early_access', JSON.stringify(submissions));

      setIsSubmitted(true);
      toast.success("You're on the list! We'll be in touch shortly.", { duration: 5000 });
    } catch {
      toast.error("Couldn't reach the server. Please email info@neufin.ai directly.", {
        duration: 8000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleReset = () => {
    setIsSubmitted(false);
    setFormData({ name: '', email: '', phone: '', company: '', portfolioSize: '' });
  };

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[9999] flex items-end sm:items-center justify-center">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ y: 32 }}
            animate={{ y: 0 }}
            exit={{ y: 32 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            className="relative z-10 w-full sm:max-w-lg mx-4 sm:mx-auto"
          >
            <div
              className="neufin-panel rounded-t-2xl sm:rounded-2xl shadow-2xl"
              style={{
                backgroundColor: '#0D1117',
                opacity: 1,
                backdropFilter: 'none',
                border: '1px solid #30363D',
                boxShadow: '0 25px 60px rgba(0,0,0,0.8)',
                maxHeight: '90vh',
                overflowY: 'auto',
              }}
            >
              {isSubmitted ? (
                /* ── Success ── */
                <div className="p-8 text-center">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 200, damping: 15 }}
                    className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5"
                    style={{ backgroundColor: 'rgba(34,197,94,0.15)' }}
                  >
                    <CheckCircle className="h-8 w-8 text-green-400" />
                  </motion.div>
                  <h3 className="text-xl font-semibold text-white mb-2">You're on the list! 🎉</h3>
                  <p className="text-sm text-gray-400 mb-1">
                    We'll reach out to{' '}
                    <span className="text-white font-medium">{formData.email}</span>
                  </p>
                  <p className="text-sm mb-8" style={{ color: '#6b7280' }}>
                    Expect a confirmation from info@neufin.ai shortly.
                  </p>
                  <div className="flex gap-3">
                    <Button
                      onClick={handleReset}
                      variant="outline"
                      className="flex-1 border-white/10 text-gray-300 hover:bg-white/5"
                    >
                      Submit Another
                    </Button>
                    <Button
                      onClick={onClose}
                      className="flex-1 text-white"
                      style={{ backgroundColor: '#7c3aed' }}
                    >
                      Done
                    </Button>
                  </div>
                </div>
              ) : (
                /* ── Form ── */
                <>
                  {/* Header */}
                  <div
                    className="flex items-start justify-between px-6 pt-6 pb-4 border-b"
                    style={{ borderColor: 'rgba(255,255,255,0.06)' }}
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Sparkles className="h-4 w-4 text-purple-400" />
                        <span className="text-xs font-medium text-purple-400 uppercase tracking-widest">
                          Early Bird
                        </span>
                      </div>
                      <h2 className="text-lg font-semibold text-white leading-tight">
                        Join the Waitlist
                      </h2>
                      <p className="text-sm mt-0.5" style={{ color: '#9ca3af' }}>
                        Neural Twin Technology™ · 50% off for early members
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={onClose}
                      className="p-1.5 rounded-lg transition-colors shrink-0 ml-4 hover:bg-white/5"
                      aria-label="Close"
                    >
                      <X className="h-5 w-5 text-gray-400" />
                    </button>
                  </div>

                  {/* Benefit chips */}
                  <div className="px-6 pt-4 flex flex-wrap gap-2">
                    {[
                      '50% off first 3 months',
                      'Priority feature access',
                      'Dedicated onboarding',
                      'Early adopter badge',
                    ].map((b) => (
                      <span
                        key={b}
                        className="inline-flex items-center gap-1 text-[11px] rounded-full px-2.5 py-1 border"
                        style={{
                          backgroundColor: 'rgba(34,197,94,0.08)',
                          borderColor: 'rgba(34,197,94,0.2)',
                          color: '#4ade80',
                        }}
                      >
                        <CheckCircle className="h-2.5 w-2.5 shrink-0" />
                        {b}
                      </span>
                    ))}
                  </div>

                  {/* Fields */}
                  <form onSubmit={handleSubmit} className="px-6 pt-4 pb-6 space-y-3">
                    {/* Row 1 — Name + Email */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <Label htmlFor="name" className="text-xs flex items-center gap-1.5" style={{ color: '#9ca3af' }}>
                          <User className="h-3 w-3 text-purple-400" />
                          Full Name <span className="text-purple-400">*</span>
                        </Label>
                        <Input
                          id="name" name="name" required placeholder="Jane Doe"
                          value={formData.name} onChange={handleChange}
                          className="h-9 text-sm text-white placeholder:text-gray-600 border focus-visible:ring-purple-500/30"
                          style={{ backgroundColor: '#151a23', borderColor: 'rgba(255,255,255,0.1)' }}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="email" className="text-xs flex items-center gap-1.5" style={{ color: '#9ca3af' }}>
                          <Mail className="h-3 w-3 text-purple-400" />
                          Email <span className="text-purple-400">*</span>
                        </Label>
                        <Input
                          id="email" name="email" type="email" required placeholder="jane@example.com"
                          value={formData.email} onChange={handleChange}
                          className="h-9 text-sm text-white placeholder:text-gray-600 border focus-visible:ring-purple-500/30"
                          style={{ backgroundColor: '#151a23', borderColor: 'rgba(255,255,255,0.1)' }}
                        />
                      </div>
                    </div>

                    {/* Row 2 — Phone + Company */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <Label htmlFor="phone" className="text-xs flex items-center gap-1.5" style={{ color: '#9ca3af' }}>
                          <Phone className="h-3 w-3 text-purple-400" />
                          Phone <span className="text-purple-400">*</span>
                        </Label>
                        <Input
                          id="phone" name="phone" type="tel" required placeholder="+1 555 123 4567"
                          value={formData.phone} onChange={handleChange}
                          className="h-9 text-sm text-white placeholder:text-gray-600 border focus-visible:ring-purple-500/30"
                          style={{ backgroundColor: '#151a23', borderColor: 'rgba(255,255,255,0.1)' }}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="company" className="text-xs flex items-center gap-1.5" style={{ color: '#9ca3af' }}>
                          <Building2 className="h-3 w-3 text-purple-400" />
                          Company <span style={{ color: '#6b7280' }}>(optional)</span>
                        </Label>
                        <Input
                          id="company" name="company" placeholder="Acme Corp"
                          value={formData.company} onChange={handleChange}
                          className="h-9 text-sm text-white placeholder:text-gray-600 border focus-visible:ring-purple-500/30"
                          style={{ backgroundColor: '#151a23', borderColor: 'rgba(255,255,255,0.1)' }}
                        />
                      </div>
                    </div>

                    {/* Portfolio size */}
                    <div className="space-y-1.5">
                      <Label htmlFor="portfolioSize" className="text-xs flex items-center gap-1.5" style={{ color: '#9ca3af' }}>
                        <TrendingUp className="h-3 w-3 text-purple-400" />
                        Est. Portfolio Size{' '}
                        <span style={{ color: '#6b7280' }}>(optional)</span>
                      </Label>
                      <Input
                        id="portfolioSize" name="portfolioSize" placeholder="e.g. $50,000 – $100,000"
                        value={formData.portfolioSize} onChange={handleChange}
                        className="h-9 text-sm text-white placeholder:text-gray-600 border focus-visible:ring-purple-500/30"
                        style={{ backgroundColor: '#151a23', borderColor: 'rgba(255,255,255,0.1)' }}
                      />
                    </div>

                    {/* Submit */}
                    <div className="pt-1">
                      <Button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full h-11 text-white font-medium"
                        style={{ backgroundColor: '#7c3aed' }}
                      >
                        {isSubmitting ? (
                          <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Submitting…
                          </span>
                        ) : (
                          <span className="flex items-center gap-2">
                            <Sparkles className="h-4 w-4" />
                            Reserve My Early Bird Spot
                          </span>
                        )}
                      </Button>
                      <p className="text-xs text-center mt-3" style={{ color: '#4b5563' }}>
                        By submitting you agree to receive updates from Neufin AI. Unsubscribe anytime.
                      </p>
                    </div>
                  </form>
                </>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}
