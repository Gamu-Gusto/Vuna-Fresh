'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import OrderStatusBadge from '@/components/OrderStatusBadge';
import Icon from '@/components/dashboard/icons';
import {
  DashboardGrid, DashboardError, DashboardLoading, GreetingCard, HeroBanner, Panel,
  RailItem, StatRow, StatTile, WeeklyBars, weeklyTotals,
} from '@/components/dashboard/widgets';

const rand = n => `R${Number(n).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function FarmerDashboard() {
  const { user } = useAuth();
  const router = useRouter();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const profile = await apiClient.get('/users/me/profile/farmer/');
        if (!profile.is_approved) {
          router.replace('/farmer/pending');
          return;
        }
        const [products, orders, payouts, reviews] = await Promise.all([
          apiClient.get(`/products/?farmer=${profile.id}`),
          apiClient.get('/orders/'),
          apiClient.get('/payments/payouts/'),
          apiClient.get('/reviews/my_products/').catch(() => ({ results: [] })),
        ]);
        setData({ profile, products, orders: orders.results ?? [], payouts: payouts.results ?? [], reviews: reviews.results ?? [] });
      } catch (err) {
        setError(err.message);
      }
    }
    load();
  }, [router]);

  if (error) return <DashboardError message={error} />;
  if (!data) return <DashboardLoading />;

  const { profile, products, orders, payouts, reviews } = data;
  const productList = products.results ?? [];
  const toPrepare = orders.filter(o => o.status === 'placed');
  const packing = orders.filter(o => o.status === 'preparing');
  const waitingToBePaid = payouts.filter(p => p.status === 'pending').reduce((s, p) => s + Number(p.net_amount), 0);
  const lowStock = productList.filter(p => p.stock_quantity <= p.low_stock_threshold);
  const myShare = order => order.items
    .filter(i => i.farmer === profile.id)
    .reduce((s, i) => s + Number(i.line_total), 0);

  return (
    <DashboardGrid
      main={
        <>
          <FarmerHero
            profile={profile}
            productCount={products.count ?? 0}
            toPrepare={toPrepare}
            packing={packing}
          />

          <StatRow>
            <StatTile icon="sprout" label="Products for sale" value={products.count ?? 0} href="/farmer/inventory" />
            <StatTile
              icon="basket"
              label="Orders to prepare"
              value={toPrepare.length + packing.length}
              href="/farmer/orders"
              tone={toPrepare.length + packing.length > 0 ? 'attention' : 'normal'}
            />
            <StatTile icon="wallet" label="Waiting to be paid" value={rand(waitingToBePaid)} href="/farmer/payouts" />
          </StatRow>

          <Panel title="Your products" action={{ href: '/farmer/inventory', label: 'See all' }}>
            {productList.length === 0 ? (
              <EmptyRow text="Nothing listed yet. Add what you're harvesting this week." href="/farmer/inventory/new" cta="Add a product" />
            ) : (
              // A swipeable row on phones, a grid from tablet up
              <div className="flex gap-3 overflow-x-auto snap-x snap-mandatory -mx-5 px-5 pb-1 sm:mx-0 sm:px-0 sm:pb-0 sm:grid sm:gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {[...lowStock, ...productList.filter(p => !lowStock.includes(p))].slice(0, 3).map(p => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Recent orders" action={{ href: '/farmer/orders', label: 'See all' }}>
            {orders.length === 0 ? (
              <EmptyRow text="No paid orders yet. They appear here as soon as a buyer's payment clears." />
            ) : (
              <div className="overflow-x-auto -mx-5 sm:-mx-6">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 border-b border-[#EEF1EC]">
                      <th className="font-medium px-5 sm:px-6 py-2">Order</th>
                      <th className="font-medium px-3 py-2 hidden sm:table-cell">Placed</th>
                      <th className="font-medium px-3 py-2">Status</th>
                      <th className="font-medium px-5 sm:px-6 py-2 text-right">Your share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EEF1EC]">
                    {orders.slice(0, 5).map(order => (
                      <tr key={order.id} className="hover:bg-brand-bg/60">
                        <td className="px-5 sm:px-6 py-3">
                          <Link href={`/farmer/orders/${order.id}`} className="font-semibold text-navy hover:text-brand-green tabular-nums">
                            #{order.id}
                          </Link>
                        </td>
                        <td className="px-3 py-3 text-gray-500 hidden sm:table-cell">{new Date(order.created_at).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })}</td>
                        <td className="px-3 py-3"><OrderStatusBadge status={order.status} /></td>
                        <td className="px-5 sm:px-6 py-3 text-right font-semibold text-navy tabular-nums">{rand(myShare(order))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </>
      }
      rail={
        <>
          <GreetingCard user={user} line={[profile.farm_name, profile.farm_location].filter(Boolean).join(', ')} />

          <Panel>
            <WeeklyBars
              title="Sales per week"
              emptyText="Your weekly sales show here once buyers' payments start coming in."
              data={weeklyTotals(payouts, {
                dateOf: p => p.created_at,
                valueOf: p => Number(p.gross_amount),
                format: v => `R${Math.round(v).toLocaleString('en-ZA')}`,
              })}
            />
          </Panel>

          <Panel title="Latest reviews" action={reviews.length ? { href: '/farmer/reviews', label: 'See all' } : undefined}>
            {reviews.length === 0 ? (
              <p className="text-sm text-gray-500">Buyers can review your products after delivery.</p>
            ) : (
              <ul className="divide-y divide-[#EEF1EC] -my-3">
                {reviews.slice(0, 4).map(r => (
                  <RailItem
                    key={r.id}
                    badge={<Stars rating={r.rating} />}
                    title={r.product_name}
                    subtitle={r.comment || `${r.buyer_name || 'A buyer'} left no comment`}
                  />
                ))}
              </ul>
            )}
          </Panel>
        </>
      }
    />
  );
}

function FarmerHero({ profile, productCount, toPrepare, packing }) {
  const kicker = profile.farm_name;
  if (toPrepare.length > 0) {
    return (
      <HeroBanner
        kicker={kicker}
        title={`${toPrepare.length} paid ${toPrepare.length === 1 ? 'order' : 'orders'} to prepare`}
        body="The buyers' payments have cleared. Pack the produce and mark each order ready for the driver."
        action={{ href: toPrepare.length === 1 ? `/farmer/orders/${toPrepare[0].id}` : '/farmer/orders', label: 'Start preparing' }}
      />
    );
  }
  if (packing.length > 0) {
    return (
      <HeroBanner
        kicker={kicker}
        title={`${packing.length} ${packing.length === 1 ? 'order' : 'orders'} being packed`}
        body="Mark each one ready for pickup as soon as it's packed, so a driver can be sent."
        action={{ href: '/farmer/orders', label: 'Open orders' }}
      />
    );
  }
  if (productCount === 0) {
    return (
      <HeroBanner
        kicker={kicker}
        title="List your first harvest"
        body="Pick a product from the catalogue, add a price and how much you have, and buyers can order it straight away."
        action={{ href: '/farmer/inventory/new', label: 'Add a product' }}
      />
    );
  }
  return (
    <HeroBanner
      kicker={kicker}
      title="Your stall is open"
      body={`${productCount} ${productCount === 1 ? 'product is' : 'products are'} on sale. Keep stock up to date so buyers only order what you can supply.`}
      action={{ href: '/farmer/inventory/new', label: 'Add a product' }}
    />
  );
}

function ProductCard({ product }) {
  const low = product.stock_quantity <= product.low_stock_threshold;
  return (
    <Link href={`/farmer/inventory/${product.id}`} className="group block shrink-0 w-[72%] snap-start sm:w-auto rounded-2xl border border-[#EEF1EC] p-2 hover:border-brand-green transition-colors">
      <div className={`${product.image_url ? 'aspect-[4/3]' : 'aspect-[16/7]'} rounded-xl bg-leaf overflow-hidden grid place-items-center`}>
        {product.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={product.image_url} alt="" className="w-full h-full object-cover" />
        ) : (
          <span className="text-brand-green/60"><Icon name="sprout" className="w-10 h-10" /></span>
        )}
      </div>
      <div className="px-2 pt-3 pb-1">
        <span className="inline-block text-xs text-gray-500">{product.category_name}</span>
        <p className="font-semibold text-navy leading-snug mt-0.5">{product.name}</p>
        <p className="mt-2 flex items-center justify-between text-sm">
          <span className="font-semibold text-navy tabular-nums">{rand(product.price)} <span className="font-normal text-gray-500">/ {product.unit}</span></span>
          <span className={`tabular-nums ${low ? 'text-amber-700 font-semibold' : 'text-gray-500'}`}>
            {product.stock_quantity} left
          </span>
        </p>
        {!product.is_available && <p className="mt-1 text-xs text-gray-500">Hidden from buyers</p>}
      </div>
    </Link>
  );
}

function Stars({ rating }) {
  return (
    <span className="w-14 shrink-0 text-amber-500 text-xs" aria-label={`${rating} out of 5 stars`}>
      {'★'.repeat(rating)}<span className="text-gray-300">{'★'.repeat(5 - rating)}</span>
    </span>
  );
}

function EmptyRow({ text, href, cta }) {
  return (
    <div className="rounded-2xl bg-brand-bg px-5 py-8 text-center">
      <p className="text-sm text-gray-600">{text}</p>
      {href && (
        <Link href={href} className="mt-3 inline-block btn-primary text-sm px-4 py-2">{cta}</Link>
      )}
    </div>
  );
}
