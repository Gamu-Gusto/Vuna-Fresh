'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import AddToCartButton from '@/components/AddToCartButton';
import Spinner from '@/components/Spinner';
import ErrorMessage from '@/components/ErrorMessage';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import ProductReviews from '@/components/ProductReviews';
import SubscribeForm from '@/components/SubscribeForm';

export default function ProductDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quantity, setQuantity] = useState(1);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.get(`/products/${id}/`);
        setProduct(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!product) return null;

  return (
    <div>
      <Link href="/products" className="text-sm text-gray-600 hover:text-navy underline underline-offset-4">
        All produce
      </Link>
      <div className="mt-6 grid gap-10 md:grid-cols-2 md:items-start">
        <div className="aspect-square rounded bg-white ring-1 ring-hairline flex items-center justify-center">
          {product.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element -- farmer uploads live on R2, not a fixed host
            <img src={product.image_url} alt={product.name} className="h-full w-full object-contain p-8" />
          ) : (
            <span className="text-sm text-gray-500">No photo yet</span>
          )}
        </div>

        <div>
          <p className="text-gray-600">Grown by {product.farm_name}</p>
          <h1 className="type-display text-6xl mt-1">{product.name}</h1>
          <p className="mt-5">
            <span className="text-3xl font-bold text-navy font-mono">R{Number(product.price).toFixed(2)}</span>
            <span className="text-gray-600"> per {product.unit}</span>
          </p>
          {product.description && <p className="mt-4 max-w-prose text-gray-700 leading-relaxed">{product.description}</p>}
          <p className="mt-2 text-sm text-gray-600">
            {product.is_low_stock
              ? <span className="text-amber-800">Only {product.stock_quantity} {product.unit} left</span>
              : <>In stock</>}
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-4">
            <div className="inline-flex items-center border border-gray-300 rounded bg-white">
              <button
                onClick={() => setQuantity(q => Math.max(1, q - 1))}
                aria-label="One less"
                className="w-10 h-10 text-lg text-gray-700 hover:bg-gray-100"
              >
                −
              </button>
              <span className="w-10 text-center font-semibold font-mono" aria-live="polite">{quantity}</span>
              <button
                onClick={() => setQuantity(q => Math.min(product.stock_quantity, q + 1))}
                aria-label="One more"
                className="w-10 h-10 text-lg text-gray-700 hover:bg-gray-100"
              >
                +
              </button>
            </div>
            <AddToCartButton productId={product.id} quantity={quantity} className="px-6 py-2.5" />
          </div>
          {user?.role === 'customer' && product.is_available && <SubscribeForm product={product} quantity={quantity} />}
        </div>
      </div>

      <ProductReviews productId={product.id} />
    </div>
  );
}
