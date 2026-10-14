import StatusText from './StatusText';

const STATUSES = {
  placed: { label: 'Placed', tone: 'normal' },
  preparing: { label: 'Being prepared', tone: 'normal' },
  ready_for_pickup: { label: 'Ready for pickup', tone: 'action' },
  out_for_delivery: { label: 'Out for delivery', tone: 'normal' },
  delivered: { label: 'Delivered', tone: 'done' },
  cancelled: { label: 'Cancelled', tone: 'problem' },
};

export default function OrderStatusBadge({ status }) {
  const s = STATUSES[status] ?? { label: status, tone: 'normal' };
  return <StatusText label={s.label} tone={s.tone} />;
}
