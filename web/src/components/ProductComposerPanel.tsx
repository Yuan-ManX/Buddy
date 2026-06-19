import React, { useState, useEffect } from 'react';

interface ProductComponent {
  component_id: string;
  name: string;
  type: string;
  description: string;
  dependencies: string[];
  required: boolean;
}

interface Product {
  product_id: string;
  name: string;
  description: string;
  status: string;
  version: string;
  component_count: number;
  components: ProductComponent[];
  created_at: number;
}

interface ProductStats {
  total_products: number;
  active_products: number;
  templates: number;
  products: Product[];
  template_list: Product[];
}

export const ProductComposerPanel: React.FC = () => {
  const [stats, setStats] = useState<ProductStats | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '', template_id: '' });
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchStats(); }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/product-composer/stats');
      setStats(await res.json());
    } catch (e) { console.error('Failed to fetch product stats:', e); }
  };

  const createProduct = async () => {
    if (!formData.name) return;
    setLoading(true);
    try {
      await fetch('/api/product-composer/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, agent_id: 'default' }),
      });
      setShowCreate(false);
      setFormData({ name: '', description: '', template_id: '' });
      fetchStats();
    } catch (e) { console.error('Create failed:', e); }
    setLoading(false);
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Product Composer</h2>
          <p style={{ color: '#666', margin: '4px 0 0' }}>Application assembly engine for agent-driven development</p>
        </div>
        <button onClick={() => setShowCreate(true)} style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
          + New Product
        </button>
      </div>

      {stats && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1, background: '#f0fdf4', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>{stats.active_products}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Active Products</div>
          </div>
          <div style={{ flex: 1, background: '#eff6ff', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.templates}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Templates</div>
          </div>
          <div style={{ flex: 1, background: '#fefce8', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#ca8a04' }}>{stats.total_products}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total Products</div>
          </div>
        </div>
      )}

      {showCreate && (
        <div style={{ background: '#f8fafc', borderRadius: 12, padding: 16, marginBottom: 16, border: '1px solid #e2e8f0' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Create New Product</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="Product name" style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }} />
            <select value={formData.template_id} onChange={e => setFormData({ ...formData, template_id: e.target.value })} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd' }}>
              <option value="">From scratch</option>
              {stats?.template_list?.map(t => (
                <option key={t.product_id} value={t.product_id}>{t.name}</option>
              ))}
            </select>
          </div>
          <textarea value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} placeholder="Description" rows={2} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', resize: 'vertical', marginBottom: 8 }} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={createProduct} disabled={loading} style={{ padding: '8px 16px', background: loading ? '#999' : '#16a34a', color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'default' : 'pointer' }}>
              {loading ? 'Creating...' : 'Create'}
            </button>
            <button onClick={() => setShowCreate(false)} style={{ padding: '8px 16px', background: '#e5e7eb', color: '#374151', border: 'none', borderRadius: 8, cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gap: 12 }}>
        {stats?.products?.map(p => (
          <div key={p.product_id} onClick={() => setSelectedProduct(selectedProduct?.product_id === p.product_id ? null : p)} style={{ background: '#fff', borderRadius: 12, padding: 16, border: '1px solid #e2e8f0', cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{p.name}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{p.description}</div>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ background: p.status === 'draft' ? '#fef3c7' : '#d1fae5', color: p.status === 'draft' ? '#92400e' : '#065f46', padding: '2px 8px', borderRadius: 6, fontSize: 11 }}>{p.status}</span>
                <span style={{ fontSize: 11, color: '#888' }}>v{p.version}</span>
              </div>
            </div>
            {selectedProduct?.product_id === p.product_id && (
              <div style={{ marginTop: 12, borderTop: '1px solid #e2e8f0', paddingTop: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Components ({p.component_count})</div>
                {p.components?.map(c => (
                  <div key={c.component_id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: '1px solid #f1f5f9' }}>
                    <span style={{ fontSize: 16 }}>{c.type === 'ui_page' ? '' : c.type === 'api_endpoint' ? '' : c.type === 'database' ? '' : c.type === 'auth' ? '' : c.type === 'deployment' ? '' : ''}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>{c.name}</div>
                      <div style={{ fontSize: 11, color: '#888' }}>{c.type} {c.required && '(required)'}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};