import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { verifyPayment } from '../services/billing';

const PaymentVerifyPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const orderId = searchParams.get('order_id');
    if (!orderId) {
      setStatus('error');
      setErrorMessage('No order ID found.');
      return;
    }

    const checkPayment = async () => {
      try {
        const success = await verifyPayment(orderId);
        if (success) {
          setStatus('success');
          // Redirect to dashboard after a short delay
          setTimeout(() => {
            navigate('/dashboard', { replace: true });
          }, 3000);
        } else {
          setStatus('error');
          setErrorMessage('Payment verification failed or is still pending.');
        }
      } catch (err) {
        console.error(err);
        setStatus('error');
        setErrorMessage('An error occurred while verifying your payment.');
      }
    };

    checkPayment();
  }, [searchParams, navigate]);

  return (
    <AppLayout title="Verifying Payment">
      <SEO title="Verifying Payment" description="Verifying your payment for LearnByGenie Pro." />
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
        <div className="bg-white p-8 md:p-12 rounded-2xl shadow-xl max-w-md w-full text-center border border-[var(--border)]">
          {status === 'verifying' && (
            <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
              <Loader2 className="w-16 h-16 text-[var(--accent-green-text)] animate-spin mb-6" />
              <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Verifying Payment</h2>
              <p className="text-[var(--text-secondary)]">
                Please wait while we confirm your payment with the gateway. Do not close this window.
              </p>
            </div>
          )}

          {status === 'success' && (
            <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-6">
                <CheckCircle2 className="w-12 h-12 text-green-600" />
              </div>
              <h2 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Success!</h2>
              <p className="text-[var(--text-secondary)] mb-6">
                Your payment was successful. You are now a Pro member.
              </p>
              <div className="text-sm font-medium text-[var(--accent-green-text)] flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Redirecting to dashboard...
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
              <div className="w-20 h-20 bg-amber-100 rounded-full flex items-center justify-center mb-6">
                <XCircle className="w-12 h-12 text-amber-900" />
              </div>
              <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Verification Failed</h2>
              <p className="text-[var(--text-secondary)] mb-8">
                {errorMessage}
              </p>
              <button
                onClick={() => navigate('/pricing')}
                className="w-full py-3 px-4 bg-[var(--text-primary)] hover:bg-gray-800 text-white font-bold rounded-xl shadow-md transition-all"
              >
                Return to Pricing
              </button>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

export default PaymentVerifyPage;
