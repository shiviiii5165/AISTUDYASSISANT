import { load } from '@cashfreepayments/cashfree-js';
import { api } from '../lib/api';
import { useAuthStore } from '../store/useAuthStore';

export const createCheckoutSession = async (amount: number = 199) => {
  const { session } = useAuthStore.getState();
  if (!session?.access_token) throw new Error('Not authenticated');

  let paymentSessionId;
  try {
    const returnUrl = `${window.location.origin}/payment/verify?order_id={order_id}`;
    const res = await api.post('/api/billing/create-order', { amount, return_url: returnUrl });
    paymentSessionId = res.data.payment_session_id;
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'Failed to create order');
  }

  const cashfree = await load({ mode: "production" });
  if (!cashfree) throw new Error("Cashfree SDK failed to load");

  const checkoutOptions = {
    paymentSessionId: paymentSessionId,
    redirectTarget: "_self"
  };

  cashfree.checkout(checkoutOptions);
};

export const verifyPayment = async (orderId: string) => {
  const { session } = useAuthStore.getState();
  if (!session?.access_token) throw new Error('Not authenticated');

  try {
    const res = await api.post('/api/billing/verify-payment', { order_id: orderId });
    if (res.data.status === 'success') {
      await useAuthStore.getState().initializeAuth();
      return true;
    }
    return false;
  } catch (error) {
    throw new Error('Failed to verify payment');
  }
};
