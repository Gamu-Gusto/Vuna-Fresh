'use client';

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  apiClient,
  setAccessToken,
  storeRefreshToken,
  getRefreshToken,
  clearTokens,
  ApiError,
} from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // null = haven't checked yet, false = checked and not logged in
  const [loading, setLoading] = useState(true);

  // On mount, try to restore session from the stored refresh token
  useEffect(() => {
    async function restoreSession() {
      const refresh = getRefreshToken();
      if (!refresh) {
        setLoading(false);
        return;
      }
      try {
        const data = await apiClient.post('/auth/token/refresh/', { refresh });
        setAccessToken(data.access);
        if (data.refresh) storeRefreshToken(data.refresh);
        const me = await apiClient.get('/users/me/');
        setUser(me);
      } catch {
        clearTokens();
      } finally {
        setLoading(false);
      }
    }
    restoreSession();
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await apiClient.post('/auth/token/', { email, password });
    setAccessToken(data.access);
    storeRefreshToken(data.refresh);
    const me = await apiClient.get('/users/me/');
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (fields) => {
    await apiClient.post('/auth/register/', fields);
    return login(fields.email, fields.password);
  }, [login]);

  // Business buyers go through a separate signup endpoint (creates User +
  // Address + BuyerProfile(business) + BusinessBuyerDetails in one call) —
  // see apps/buyers/views.py BusinessBuyerSignupView on the backend.
  const registerBusiness = useCallback(async (fields) => {
    await apiClient.post('/buyers/business/signup/', fields);
    return login(fields.email, fields.password);
  }, [login]);

  const logout = useCallback(async () => {
    try {
      const refresh = getRefreshToken();
      if (refresh) await apiClient.post('/auth/token/blacklist/', { refresh });
    } catch {}
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, registerBusiness, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
