'use client';

import { useState, useRef } from 'react';
import { uploadFile } from '@/lib/api';

export function ProductFormFields({ form, onChange, categories }) {
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
      <Field label="Product name" name="name" value={form.name} onChange={onChange} required />

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

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
        <select
          name="category"
          value={form.category}
          onChange={onChange}
          required
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent"
        >
          <option value="">Select a category…</option>
          {categories.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Price (R)" name="price" type="number" step="0.01" min="0" value={form.price} onChange={onChange} required />
        <Field label="Unit" name="unit" placeholder="kg, each, bunch…" value={form.unit} onChange={onChange} required />
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
