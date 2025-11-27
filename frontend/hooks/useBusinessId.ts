import { useEffect, useState } from 'react';
import { businessAPI } from '@/lib/api';

export function useBusinessId() {
  const [businessId, setBusinessId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadBusiness = async () => {
      try {
        // Get the demo business by phone number
        const response = await businessAPI.getByPhone('+15555551234');
        setBusinessId(response.data.id);
      } catch (err) {
        console.error('Error loading business:', err);
        setError('Failed to load business');
        // Use a fallback ID for development
        setBusinessId('demo-business-id');
      } finally {
        setLoading(false);
      }
    };

    loadBusiness();
  }, []);

  return { businessId, loading, error };
}
