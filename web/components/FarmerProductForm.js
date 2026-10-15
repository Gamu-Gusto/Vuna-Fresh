'use client';

import { useState, useRef, useMemo } from 'react';
import Link from 'next/link';
import { uploadFile } from '@/lib/api';

/**
 * `catalogue` is the list from GET /catalogue/. When `lockedItem` is given
 * (editing a listing that already has a catalogue product), the product is
 * shown read-only: a listing's product can't be changed after it's created.
 */
export function ProductFormFields({ form, onChange, catalogue, lockedItem }) {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef(null);

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError('');
    try {
      const { url } = await uploadFile('/products/upload_image/', file);
      onChange({ target: { name: 'image_url', value: url } });
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  function handleRemoveImage() {
    onChange({ target: { name: 'image_url', value: '' } });
    setUploadError('');
  }

  return (
    <>
      {lockedItem ? (
        <div>
          <span className="block text-sm font-medium text-gray-700 mb-1">Product</span>
          <p className="text-sm text-gray-800">
            {lockedItem.name}{' '}
            <span className="text-gray-400">· {categoryPath(lockedItem)}</span>
          </p>
          <p className="mt-1 text-xs text-gray-400">To sell a different product, add a new one.</p>
        </div>
      ) : (
        <CataloguePicker
          catalogue={catalogue}
          value={form.catalogue_item}
          onSelect={item => {
            onChange({ target: { name: 'catalogue_item', value: String(item.id) } });
            // Pre-fill the unit unless the farmer has already typed their own
            const previous = catalogue.find(c => String(c.id) === String(form.catalogue_item));
            if (!form.unit || form.unit === previous?.default_unit) {
              onChange({ target: { name: 'unit', value: item.default_unit } });
            }
          }}
        />
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
        <textarea
          name="description"
          value={form.description}
          onChange={onChange}
          rows={3}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Price (R)" name="price" type="number" step="0.01" min="0" value={form.price} onChange={onChange} required />
        <Field label="Unit (price is per unit)" name="unit" placeholder="kg, 5 kg bag, 200 g pack…" value={form.unit} onChange={onChange} required />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Stock quantity" name="stock_quantity" type="number" min="0" value={form.stock_quantity} onChange={onChange} required />
        <Field label="Low-stock threshold" name="low_stock_threshold" type="number" min="0" value={form.low_stock_threshold} onChange={onChange} required />
      </div>

      {/* Image upload */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Product image (optional)</label>

        {form.image_url ? (
          <div className="flex items-start gap-4">
            <img
              src={form.image_url}
              alt="Product preview"
              className="w-24 h-24 object-cover rounded-lg border border-hairline bg-gray-50"
            />
            <div className="space-y-2 pt-1">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="block text-sm text-brand-green hover:underline disabled:opacity-50"
              >
                {uploading ? 'Uploading…' : 'Change image'}
              </button>
              <button
                type="button"
                onClick={handleRemoveImage}
                className="block text-sm text-red-400 hover:text-red-600"
              >
                Remove image
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 border border-dashed border-gray-300 rounded-lg px-4 py-3 text-sm text-gray-500 hover:border-brand-green hover:text-brand-green transition-colors disabled:opacity-50"
          >
            {uploading ? (
              <>
                <span className="w-4 h-4 border-2 border-gray-300 border-t-brand-green rounded-full animate-spin" />
                Uploading…
              </>
            ) : (
              'Choose image'
            )}
          </button>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          onChange={handleFileChange}
          className="hidden"
        />

        {!uploading && !form.image_url && (
          <p className="mt-1 text-xs text-gray-400">JPEG, PNG, WebP or GIF, up to 5 MB</p>
        )}

        {uploadError && (
          <p className="mt-1 text-xs text-red-500">{uploadError}</p>
        )}
      </div>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          name="is_available"
          checked={form.is_available}
          onChange={onChange}
          className="w-4 h-4 accent-brand-green"
        />
        <span className="text-sm font-medium text-gray-700">List as available for purchase</span>
      </label>
    </>
  );
}

function categoryPath(item) {
  return item.parent_category_name
    ? `${item.parent_category_name} › ${item.category_name}`
    : item.category_name;
}

function CataloguePicker({ catalogue, value, onSelect }) {
  const [query, setQuery] = useState('');
  const selected = catalogue.find(c => String(c.id) === String(value));

  // Group matches under "Category › Subcategory", in that order
  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const byGroup = new Map();
    for (const item of catalogue) {
      if (q && !item.name.toLowerCase().includes(q) && !categoryPath(item).toLowerCase().includes(q)) continue;
      const group = categoryPath(item);
      if (!byGroup.has(group)) byGroup.set(group, []);
      byGroup.get(group).push(item);
    }
    return [...byGroup.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [catalogue, query]);

  return (
    <div>
      <label htmlFor="catalogue-search" className="block text-sm font-medium text-gray-700 mb-1">Product</label>
      <input
        id="catalogue-search"
        type="search"
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Search, e.g. spinach, citrus, eggs…"
        className="w-full border border-gray-300 rounded-t-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
      />
      <select
        name="catalogue_item"
        aria-label="Product"
        size={8}
        value={value}
        onChange={e => {
          const item = catalogue.find(c => String(c.id) === e.target.value);
          if (item) onSelect(item);
        }}
        required
        className="w-full border border-t-0 border-gray-300 rounded-b-lg px-1 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
      >
        {/* Matches the empty value, so nothing looks chosen until the farmer picks.
            Without it React highlights the first product, and clicking that
            product changes nothing, so the form is sent with no product. */}
        <option value="" disabled hidden>Choose a product</option>
        {groups.map(([group, items]) => (
          <optgroup key={group} label={group}>
            {items.map(item => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </optgroup>
        ))}
      </select>
      <p className="mt-1 text-xs text-gray-500">
        {selected
          ? <>Selected: <span className="font-medium text-gray-800">{selected.name}</span> · {categoryPath(selected)}</>
          : catalogue.length && !groups.length ? 'No products match your search.' : 'Pick the product you are selling.'}
      </p>
      <p className="mt-1 text-xs text-gray-400">
        Can&apos;t find your product?{' '}
        <Link href="/farmer/support" className="text-brand-green hover:underline">Ask us to add it</Link>.
      </p>
    </div>
  );
}

function Field({ label, name, type = 'text', value, onChange, required, placeholder, step, min }) {
  return (
    <div>
      <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        id={name}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        placeholder={placeholder}
        step={step}
        min={min}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
      />
    </div>
  );
}
