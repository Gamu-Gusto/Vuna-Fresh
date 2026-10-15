'use client';

import { useState } from 'react';
import Link from 'next/link';
import Icon from './icons';

// Building blocks for the farmer, driver and admin dashboard home pages.

export const CARD = 'bg-white rounded-3xl border border-[#E4E8E1]';

/** Main column + right-hand rail on wide screens; stacked on smaller ones. */
export function DashboardGrid({ main, rail }) {
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem] items-start">
      <div className="min-w-0 flex flex-col gap-6">{main}</div>
      {/* flex gap, not space-y: a card hidden on small screens leaves no extra margin */}
      <aside className="flex flex-col gap-6">{rail}</aside>
    </div>
  );
}

/**
 * The page's one loud element: a deep-green panel with faint planted rows,
 * carrying the single most useful next step for this person.
 */
export function HeroBanner({ kicker, title, body, action }) {
  return (
    <section className="relative overflow-hidden rounded-3xl bg-[#1E4E1C] text-white px-6 py-7 sm:px-9 sm:py-9">
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-90"
        style={{
          backgroundImage:
            'repeating-linear-gradient(118deg, rgba(255,255,255,0.075) 0 2px, transparent 2px 26px)',
          maskImage: 'linear-gradient(100deg, transparent 30%, black 85%)',
          WebkitMaskImage: 'linear-gradient(100deg, transparent 30%, black 85%)',
        }}
      />
      <div
        aria-hidden="true"
        className="absolute -right-16 -bottom-24 w-72 h-72 rounded-full bg-sprout/25 blur-3xl"
      />
      <div className="relative max-w-xl">
        {kicker && <p className="text-sm text-[#BFE3BB]">{kicker}</p>}
        <h1 className="type-display text-white text-[2.5rem] sm:text-[3.25rem] mt-2">{title}</h1>
        {body && <p className="mt-3 text-[0.9375rem] text-[#DCEFD9] leading-relaxed">{body}</p>}
        {action && (
          <Link
            href={action.href}
            className="mt-6 inline-flex items-center gap-3 rounded-full bg-white text-navy font-semibold text-sm pl-5 pr-1.5 py-1.5 hover:bg-leaf transition-colors"
          >
            {action.label}
            <span className="w-8 h-8 rounded-full bg-navy text-white grid place-items-center">
              <Icon name="arrow" className="w-4 h-4" />
            </span>
          </Link>
        )}
      </div>
    </section>
  );
}

/** Small figure with an icon tile. tone="attention" when it needs action. */
// Side by side even on phones: there the icon sits above a smaller figure.
export function StatTile({ icon, label, value, href, tone = 'normal' }) {
  const attention = tone === 'attention';
  const body = (
    <>
      <span className={`w-10 h-10 sm:w-12 sm:h-12 shrink-0 rounded-2xl grid place-items-center ${attention ? 'bg-amber-100 text-amber-700' : 'bg-leaf text-brand-green'}`}>
        <Icon name={icon} />
      </span>
      <span className="min-w-0">
        <span className="block text-xs sm:text-sm text-gray-500 leading-snug sm:truncate">{label}</span>
        <span className={`block type-display text-[1.5rem] sm:text-[2rem] ${attention ? 'text-amber-700' : 'text-navy'}`}>{value}</span>
      </span>
    </>
  );
  const className = `${CARD} flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 p-3 sm:p-4 sm:pr-5`;
  return href ? (
    <Link href={href} className={`${className} hover:border-brand-green transition-colors`}>{body}</Link>
  ) : (
    <div className={className}>{body}</div>
  );
}

export function StatRow({ children }) {
  return <div className="grid grid-cols-3 gap-2 sm:gap-4">{children}</div>;
}

/** White panel with a heading and an optional "see all" style link. */
export function Panel({ title, action, children, className = '' }) {
  return (
    <section className={`${CARD} p-5 sm:p-6 ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-3 mb-4">
          {title && <h2 className="text-lg font-semibold text-navy">{title}</h2>}
          {action && (
            <Link href={action.href} className="text-sm font-medium text-brand-green hover:underline underline-offset-4">
              {action.label}
            </Link>
          )}
        </div>
      )}
      {children}
    </section>
  );
}

export function timeOfDayGreeting(date = new Date()) {
  const hour = date.getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

/** Top of the right-hand rail: who's signed in and a one-line status. */
export function GreetingCard({ user, line, children }) {
  const initials = ((user?.first_name?.[0] ?? '') + (user?.last_name?.[0] ?? '')).toUpperCase() || '?';
  return (
    // Only on wide screens: stacked under the page it would come last, and the
    // top bar already shows who's signed in.
    <section className={`${CARD} p-6 text-center hidden xl:block`}>
      <span className="mx-auto w-20 h-20 rounded-full bg-leaf ring-4 ring-white outline outline-2 outline-brand-green/30 grid place-items-center type-display text-3xl text-brand-green" aria-hidden="true">
        {initials}
      </span>
      <p className="mt-4 text-lg font-semibold text-navy">
        {timeOfDayGreeting()}, {user?.first_name || 'there'}
      </p>
      {line && <p className="mt-1 text-sm text-gray-500">{line}</p>}
      {children}
    </section>
  );
}

/**
 * Single-series column chart (e.g. sales per week). data: [{ label, value, display }].
 * Columns grow from one baseline with 4px rounded tops; hover or focus a column
 * for its value. The latest column is labelled when nothing is hovered. A
 * screen-reader table carries the same numbers.
 */
export function WeeklyBars({ title, data, emptyText }) {
  const [active, setActive] = useState(null);
  const max = Math.max(...data.map(d => d.value), 0);
  const hasData = max > 0;
  const counts = data.every(d => Number.isInteger(d.value));
  let top = hasData ? niceCeiling(max) : 1;
  if (counts && !Number.isInteger(top / 2)) top = Math.max(2, Math.ceil(top / 2) * 2); // no "0.5 orders"
  const ticks = [top, top / 2, 0];
  const lastIndex = data.length - 1;

  return (
    <div>
      <h3 className="text-sm font-semibold text-navy mb-4">{title}</h3>
      {!hasData ? (
        <p className="text-sm text-gray-500 py-8 text-center">{emptyText}</p>
      ) : (
        <>
          <div className="relative h-40 grid grid-cols-[2.5rem_1fr]">
            <div className="relative" aria-hidden="true">
              {ticks.map(t => (
                <span
                  key={t}
                  className="absolute right-2 -translate-y-1/2 text-[0.6875rem] text-gray-400 tabular-nums"
                  style={{ top: `${100 - (t / top) * 100}%` }}
                >
                  {formatTick(t)}
                </span>
              ))}
            </div>
            <div className="relative">
              {ticks.map(t => (
                <span key={t} aria-hidden="true" className="absolute inset-x-0 h-px bg-[#EEF1EC]" style={{ top: `${100 - (t / top) * 100}%` }} />
              ))}
              <div className="absolute inset-0 flex items-end justify-around gap-0.5">
                {data.map((d, i) => {
                  const highlighted = active === i || (active === null && i === lastIndex);
                  return (
                    // The whole column slot is the hover/focus target, wider than the bar
                    <button
                      key={d.label}
                      type="button"
                      aria-label={`${d.label}: ${d.display}`}
                      onMouseEnter={() => setActive(i)}
                      onMouseLeave={() => setActive(null)}
                      onFocus={() => setActive(i)}
                      onBlur={() => setActive(null)}
                      className="relative h-full flex-1 flex items-end justify-center rounded-md"
                    >
                      {highlighted && d.value > 0 && (
                        <span
                          aria-hidden="true"
                          className="absolute -translate-y-full -mt-1 px-1.5 py-0.5 rounded-md bg-navy text-white text-[0.6875rem] font-semibold whitespace-nowrap tabular-nums"
                          style={{ bottom: `${(d.value / top) * 100}%` }}
                        >
                          {d.display}
                        </span>
                      )}
                      <span
                        aria-hidden="true"
                        className={`block w-full max-w-6 rounded-t ${highlighted ? 'bg-brand-green' : 'bg-brand-green/45'}`}
                        style={{ height: `${Math.max((d.value / top) * 100, d.value > 0 ? 2 : 0)}%` }}
                      />
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="grid grid-cols-[2.5rem_1fr] mt-2" aria-hidden="true">
            <span />
            <div className="flex justify-around gap-0.5">
              {data.map(d => (
                <span key={d.label} className="flex-1 text-center text-[0.6875rem] text-gray-500 whitespace-nowrap">{d.label}</span>
              ))}
            </div>
          </div>
          <table className="sr-only">
            <caption>{title}</caption>
            <tbody>
              {data.map(d => (
                <tr key={d.label}><th scope="row">{d.label}</th><td>{d.display}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function niceCeiling(value) {
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const steps = [1, 2, 2.5, 5, 10];
  const step = steps.find(s => s * magnitude >= value) ?? 10;
  return step * magnitude;
}

function formatTick(value) {
  if (value >= 1000) return `${Math.round(value / 100) / 10}k`;
  return String(Math.round(value * 10) / 10);
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Last `weeks` calendar weeks (Mon–Sun) ending this week, summing `valueOf(row)`
 * by the week `dateOf(row)` falls in. Returns [{ label, value, display }].
 */
export function weeklyTotals(rows, { weeks = 6, dateOf, valueOf, format }) {
  const startOfWeek = d => {
    const x = new Date(d);
    x.setHours(0, 0, 0, 0);
    x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
    return x;
  };
  const thisWeek = startOfWeek(new Date());
  const buckets = Array.from({ length: weeks }, (_, i) => {
    const start = new Date(thisWeek);
    start.setDate(start.getDate() - 7 * (weeks - 1 - i));
    return { start, value: 0 };
  });
  for (const row of rows) {
    const t = startOfWeek(dateOf(row)).getTime();
    const bucket = buckets.find(b => b.start.getTime() === t);
    if (bucket) bucket.value += valueOf(row);
  }
  return buckets.map((b, i) => ({
    label: i === weeks - 1 ? 'Now' : `${b.start.getDate()} ${MONTHS[b.start.getMonth()]}`,
    value: b.value,
    display: format(b.value),
  }));
}

/** Row in a rail list: leading badge, two lines of text, optional trailing action. */
export function RailItem({ badge, title, subtitle, action }) {
  return (
    <li className="flex items-center gap-3 py-3">
      {badge}
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-navy truncate">{title}</span>
        {subtitle && <span className="block text-xs text-gray-500 truncate">{subtitle}</span>}
      </span>
      {action}
    </li>
  );
}

export function DashboardLoading() {
  return <div className="text-center py-24 text-gray-400 text-sm">Loading your dashboard…</div>;
}

export function DashboardError({ message }) {
  return (
    <div className="text-center py-24 text-sm">
      <p className="text-ember">{message}</p>
      <button onClick={() => window.location.reload()} className="mt-3 text-brand-green font-medium hover:underline">
        Try again
      </button>
    </div>
  );
}
