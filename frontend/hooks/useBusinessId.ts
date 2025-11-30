import { useEffect, useState } from 'react';
import { businessAPI } from '@/lib/api';

export function useBusinessId() {
  const [businessId, setBusinessId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadBusiness = async () => {
      try {
        // List all businesses and use the first one
        const listResponse = await businessAPI.list();
        if (listResponse.data && listResponse.data.length > 0) {
          setBusinessId(listResponse.data[0].id);
          console.log('Business loaded:', listResponse.data[0]);
        } else {
          setError('No businesses found. Create one in Settings.');
        }
      } catch (err) {
        console.error('Error loading business:', err);
        setError('Failed to load business. Is the backend running?');
      } finally {
        setLoading(false);
      }
    };

    loadBusiness();
  }, []);

  return { businessId, loading, error };
}
