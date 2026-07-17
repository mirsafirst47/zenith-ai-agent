import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, authAPI } from '@/lib/api';

/**
 * Protects dashboard pages. Resolution order:
 * 1. Backend reports auth_enabled=false (local dev) -> allow through.
 * 2. Valid token -> allow through.
 * 3. Otherwise -> redirect to /login.
 */
export function useAuthGuard() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [authEnabled, setAuthEnabled] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const health = await api.get('/health');
        if (cancelled) return;

        if (health.data?.auth_enabled === false) {
          setAuthEnabled(false);
          setChecking(false);
          return;
        }

        const token = localStorage.getItem('zenith_token');
        if (!token) {
          router.replace('/login');
          return;
        }

        // Validate the token; the api interceptor won't redirect for
        // /api/auth/ URLs, so handle the failure here.
        try {
          await authAPI.me();
          if (!cancelled) setChecking(false);
        } catch {
          if (!cancelled) {
            authAPI.clearToken();
            router.replace('/login');
          }
        }
      } catch {
        // Backend unreachable — let the page render; its own data
        // fetches will surface the connection error.
        if (!cancelled) setChecking(false);
      }
    };

    check();
    return () => {
      cancelled = true;
    };
  }, [router]);

  return { checking, authEnabled };
}
