import StatusText from './StatusText';

// For the order's `payment.status` (see OrderSerializer.get_payment on the backend).
const STATUSES = {
  paid: { label: 'Paid', tone: 'done' },
  proof_submitted: { label: 'Payment being checked', tone: 'normal' },
  awaiting_payment: { label: 'Not paid yet', tone: 'action' },
  unpaid: { label: 'Not paid yet', tone: 'action' },
  credit: { label: 'On account', tone: 'quiet' },
};

export default function PaymentStatusBadge({ status }) {
  const s = STATUSES[status];
  if (!s) return null;
  return <StatusText label={s.label} tone={s.tone} />;
}
