'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { apiClient } from '@/lib/api';
import Logo from '@/components/Logo';
import Icon from './icons';

/**
 * Sidebar layout for the farmer, driver and admin portals.
 *
 * sections:  [{ label, items: [{ href, label, icon }] }] — the sidebar menu.
 *            The first item of the first section is the home page.
 * shortcuts: extra destinations for the "jump to" search, e.g. "Add a product".
 */
export default function DashboardShell({
  sections, shortcuts = [], notificationsHref, supportHref, loginHref, roleLabel, children,
}) {
  const pathname = usePathname();
  // The phone menu remembers the page it was opened on, so it closes itself
  // as soon as a link takes you to another page.
  const [drawerOpenedOn, setDrawerOpenedOn] = useState(null);
  const drawerOpen = drawerOpenedOn === pathname;
  const homeHref = sections[0].items[0].href;

  return (
    <div className="min-h-screen bg-brand-bg lg:grid lg:grid-cols-[15.5rem_1fr]">
      <aside className="hidden lg:flex lg:flex-col sticky top-0 h-screen bg-white border-r border-[#E4E8E1]">
        <Sidebar sections={sections} homeHref={homeHref} loginHref={loginHref} pathname={pathname} />
      </aside>

      {drawerOpen && (
        <MobileDrawer onClose={() => setDrawerOpenedOn(null)}>
          <Sidebar sections={sections} homeHref={homeHref} loginHref={loginHref} pathname={pathname} />
        </MobileDrawer>
      )}

      <div className="min-w-0 flex flex-col">
        <TopBar
          sections={sections}
          shortcuts={shortcuts}
          notificationsHref={notificationsHref}
          supportHref={supportHref}
          roleLabel={roleLabel}
          onOpenMenu={() => setDrawerOpenedOn(pathname)}
        />
        <main className="flex-1 w-full max-w-[90rem] px-4 sm:px-6 lg:px-8 pb-10">{children}</main>
      </div>
    </div>
  );
}

// An item may list extra path prefixes it owns in `match`, e.g. the driver's
// Deliveries home (/driver/dashboard) also owns /driver/deliveries/<id>.
function isActive(item, homeHref, pathname) {
  const under = prefix => pathname === prefix || pathname.startsWith(`${prefix}/`);
  if ((item.match ?? []).some(under)) return true;
  return item.href === homeHref ? pathname === item.href : under(item.href);
}

function Sidebar({ sections, homeHref, loginHref, pathname }) {
  const { logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push(loginHref);
  }

  return (
    <div className="flex flex-col h-full px-4 py-6">
      <Link href={homeHref} className="px-3 mb-8 inline-flex">
        <Logo dark={false} className="h-7 w-auto" />
      </Link>

      <nav aria-label="Main" className="flex-1 overflow-y-auto space-y-7">
        {sections.map(section => (
          <div key={section.label}>
            <p className="px-3 mb-2 text-xs font-medium text-gray-400">{section.label}</p>
            <ul className="space-y-1">
              {section.items.map(item => {
                const active = isActive(item, homeHref, pathname);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      aria-current={active ? 'page' : undefined}
                      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-[0.9375rem] transition-colors ${
                        active
                          ? 'bg-leaf text-navy font-semibold'
                          : 'text-gray-600 hover:bg-brand-bg hover:text-navy'
                      }`}
                    >
                      <span className={active ? 'text-brand-green' : 'text-gray-400'}>
                        <Icon name={item.icon} />
                      </span>
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <button
        onClick={handleLogout}
        className="mt-6 flex items-center gap-3 rounded-xl px-3 py-2.5 text-[0.9375rem] text-ember hover:bg-red-50 transition-colors"
      >
        <Icon name="logout" />
        Log out
      </button>
    </div>
  );
}

function MobileDrawer({ onClose, children }) {
  const panelRef = useRef(null);

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose(); }
    document.addEventListener('keydown', onKey);
    const { overflow } = document.body.style;
    document.body.style.overflow = 'hidden';
    panelRef.current?.querySelector('a, button')?.focus();
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
    };
  }, [onClose]);

  return (
    <div className="lg:hidden fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Menu">
      <button aria-label="Close menu" onClick={onClose} className="absolute inset-0 bg-navy/40" />
      <div ref={panelRef} className="relative h-full w-72 max-w-[85vw] bg-white shadow-xl">
        <button
          onClick={onClose}
          aria-label="Close menu"
          className="absolute right-3 top-5 p-2 rounded-lg text-gray-500 hover:bg-brand-bg"
        >
          <Icon name="close" />
        </button>
        {children}
      </div>
    </div>
  );
}

function TopBar({ sections, shortcuts, notificationsHref, supportHref, roleLabel, onOpenMenu }) {
  const { user } = useAuth();
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    apiClient.get('/notifications/unread_count/')
      .then(data => setUnread(data.count))
      .catch(() => {});
  }, [pathname]);

  const name = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.email;
  const initials = ((user?.first_name?.[0] ?? '') + (user?.last_name?.[0] ?? '')).toUpperCase() || '?';

  return (
    <header className="sticky top-0 z-30 bg-brand-bg/90 backdrop-blur px-4 sm:px-6 lg:px-8 py-4 flex items-center gap-3">
      <button
        onClick={onOpenMenu}
        aria-label="Open menu"
        className="lg:hidden p-2.5 rounded-full bg-white border border-[#E4E8E1] text-navy"
      >
        <Icon name="menu" />
      </button>

      <JumpSearch sections={sections} shortcuts={shortcuts} />

      <div className="flex items-center gap-2 sm:gap-3 ml-auto">
        <Link
          href={supportHref}
          aria-label="Support"
          className="hidden sm:inline-flex p-2.5 rounded-full bg-white border border-[#E4E8E1] text-navy hover:border-brand-green transition-colors"
        >
          <Icon name="chat" />
        </Link>
        <Link
          href={notificationsHref}
          aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
          className="relative inline-flex p-2.5 rounded-full bg-white border border-[#E4E8E1] text-navy hover:border-brand-green transition-colors"
        >
          <Icon name="bell" />
          {unread > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[1.25rem] h-5 px-1 rounded-full bg-ember text-white text-[0.6875rem] font-semibold leading-5 text-center">
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </Link>
        <span className="hidden sm:block w-px h-8 bg-[#DCE1D8] mx-1" aria-hidden="true" />
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-full bg-navy text-white grid place-items-center text-sm font-semibold" aria-hidden="true">
            {initials}
          </span>
          <span className="hidden md:block leading-tight">
            <span className="block text-sm font-semibold text-navy">{name}</span>
            <span className="block text-xs text-gray-500">{roleLabel}</span>
          </span>
        </div>
      </div>
    </header>
  );
}

// Type to jump to any page in the portal ("orders", "payouts", "add product").
// "/" focuses it from anywhere.
function JumpSearch({ sections, shortcuts }) {
  const router = useRouter();
  const inputRef = useRef(null);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  const destinations = useMemo(
    () => [...sections.flatMap(s => s.items), ...shortcuts],
    [sections, shortcuts],
  );
  const q = query.trim().toLowerCase();
  const matches = q ? destinations.filter(d => d.label.toLowerCase().includes(q)) : destinations;

  useEffect(() => {
    function onKey(e) {
      const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
      if (e.key === '/' && !typing) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  function go(destination) {
    setQuery('');
    setOpen(false);
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    router.push(destination.href);
  }

  function onKeyDown(e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setHighlight(h => Math.min(h + 1, matches.length - 1)); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setHighlight(h => Math.max(h - 1, 0)); }
    if (e.key === 'Enter' && matches[highlight]) { e.preventDefault(); go(matches[highlight]); }
    if (e.key === 'Escape') { setOpen(false); e.currentTarget.blur(); }
  }

  return (
    <div className="relative flex-1 max-w-xl">
      <label htmlFor="jump-search" className="sr-only">Jump to a page</label>
      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
        <Icon name="search" className="w-[1.125rem] h-[1.125rem]" />
      </span>
      <input
        ref={inputRef}
        id="jump-search"
        type="search"
        role="combobox"
        aria-expanded={open}
        aria-controls="jump-search-results"
        aria-activedescendant={open && matches[highlight] ? `jump-${highlight}` : undefined}
        autoComplete="off"
        value={query}
        placeholder="Jump to a page"
        onChange={e => { setQuery(e.target.value); setHighlight(0); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
        className="w-full rounded-full bg-white border border-[#E4E8E1] pl-11 pr-4 sm:pr-10 py-2.5 text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:border-brand-green focus:ring-2 focus:ring-brand-green/20"
      />
      <kbd className="hidden sm:block absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-[#E4E8E1] px-1.5 text-xs text-gray-400 font-sans pointer-events-none" aria-hidden="true">/</kbd>
      {open && (
        <ul
          id="jump-search-results"
          role="listbox"
          className="absolute z-40 mt-2 w-full rounded-2xl bg-white border border-[#E4E8E1] shadow-lg py-2 max-h-80 overflow-y-auto"
        >
          {matches.length === 0 ? (
            <li className="px-4 py-2 text-sm text-gray-500">No page called &ldquo;{query}&rdquo;.</li>
          ) : matches.map((d, i) => (
            <li
              key={d.href + d.label}
              id={`jump-${i}`}
              role="option"
              aria-selected={i === highlight}
              onMouseDown={e => { e.preventDefault(); go(d); }}
              onMouseEnter={() => setHighlight(i)}
              className={`flex items-center gap-3 px-4 py-2 text-sm cursor-pointer ${i === highlight ? 'bg-leaf text-navy' : 'text-gray-700'}`}
            >
              <span className="text-gray-400"><Icon name={d.icon} className="w-4 h-4" /></span>
              {d.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
