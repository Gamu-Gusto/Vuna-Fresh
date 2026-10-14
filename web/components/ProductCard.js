import Link from 'next/link';
import AddToCartButton from './AddToCartButton';

// Produce first: a large photo (farm photos are usually shot on white), then
// name, farm and price. No card chrome around the text.
export default function ProductCard({ product }) {
  return (
    <article className="flex flex-col">
      <Link href={`/products/${product.id}`} className="group block">
        <div className="aspect-[4/3] rounded-lg bg-white ring-1 ring-hairline overflow-hidden flex items-center justify-center">
          {product.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element -- farmer uploads live on R2, not a fixed host
            <img src={product.image_url} alt="" className="h-full w-full object-contain p-4" />
          ) : (
            <span className="text-sm text-brand-green/70">No photo yet</span>
          )}
        </div>
        <h3 className="mt-3 text-lg font-semibold leading-snug group-hover:text-brand-green transition-colors">{product.name}</h3>
      </Link>
      <p className="text-sm text-gray-500">{product.farm_name}</p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p>
          <span className="text-xl font-bold text-navy font-mono">R{Number(product.price).toFixed(2)}</span>
          <span className="text-sm text-gray-500"> per {product.unit}</span>
        </p>
        <AddToCartButton productId={product.id} className="shrink-0" />
      </div>
      {product.is_low_stock && <p className="mt-1 text-xs text-ember">Only {product.stock_quantity} left</p>}
    </article>
  );
}
