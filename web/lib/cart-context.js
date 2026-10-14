'use client';

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiClient } from './api';
import { useAuth } from './auth-context';

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { user } = useAuth();
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchCart = useCallback(async () => {
    if (!user || user.role !== 'customer') return;
    setLoading(true);
    try {
      const data = await apiClient.get('/cart/');
      setCart(data);
    } catch {
      setCart(null);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  const addItem = useCallback(async (productId, quantity = 1) => {
    const data = await apiClient.post('/cart/add_item/', { product_id: productId, quantity });
    await fetchCart();
    return data;
  }, [fetchCart]);

  const updateItem = useCallback(async (itemId, quantity) => {
    await apiClient.patch(`/cart/items/${itemId}/`, { quantity });
    await fetchCart();
  }, [fetchCart]);

  const removeItem = useCallback(async (itemId) => {
    await apiClient.delete(`/cart/items/${itemId}/`);
    await fetchCart();
  }, [fetchCart]);

  const itemCount = cart?.items?.reduce((sum, i) => sum + i.quantity, 0) ?? 0;

  return (
    <CartContext.Provider value={{ cart, loading, fetchCart, addItem, updateItem, removeItem, itemCount }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used inside CartProvider');
  return ctx;
}
