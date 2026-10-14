'use client';

import { useState } from 'react';
import { useCart } from '@/lib/cart-context';

export default function CartItemRow({ item }) {
  const { updateItem, removeItem } = useCart();
  const [qty, setQty] = useState(item.quantity);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleQtyChange(newQty) {
    if (newQty < 1) return;
    const prevQty = qty;
    setQty(newQty);
    setSaving(true);
    setError('');
    try {
      await updateItem(item.id, newQty);
    } catch (err) {
      setQty(prevQty);
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove() {
    setError('');
    try {
      await removeItem(item.id);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="py-4 border-b border-hairline last:border-0">
      <div className="flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-800 truncate">{item.product_name}</p>
          <p className="text-sm text-gray-400">{item.product_unit}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleQtyChange(qty - 1)}
            className="w-7 h-7 rounded-full border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100"
          >
            −
          </button>
          <span className="w-8 text-center text-sm font-medium font-mono">{saving ? '…' : qty}</span>
          <button
            onClick={() => handleQtyChange(qty + 1)}
            className="w-7 h-7 rounded-full border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-100"
          >
            +
          </button>
        </div>
        <div className="w-24 text-right">
          <p className="font-semibold text-gray-800 font-mono">
            R{Number(item.line_total).toFixed(2)}
          </p>
          <p className="text-xs text-gray-400 font-mono">@ R{Number(item.price_at_add).toFixed(2)}</p>
        </div>
        <button onClick={handleRemove} className="text-gray-300 hover:text-red-400 transition-colors text-xl leading-none">
          ×
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-ember">{error}</p>}
    </div>
  );
}
