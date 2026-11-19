'use client';
import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { chromaApi } from '@/lib/api';
import { PageHeader } from '@/components/ui';
import toast from 'react-hot-toast';
import { Search } from 'lucide-react';

export default function VectorSearchPage() {
  const [query,    setQuery]    = useState('');
  const [results,  setResults]  = useState<Array<Record<string,unknown>>>([]);
  const [stats,    setStats]    = useState<Record<string,unknown> | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [category, setCategory] = useState('');
  const [n,        setN]        = useState(5);
  const demoDisabled = true;

  useEffect(() => {
    if (demoDisabled) return;
    chromaApi.stats().then(r => setStats(r.data)).catch(() => {});
  }, [demoDisabled]);

  const initKB = async () => {
    toast.loading('Initializing knowledge base…', { id: 'init' });
    try {
      await chromaApi.init();
      toast.success('Knowledge base ready!', { id: 'init' });
      const r = await chromaApi.stats();
      setStats(r.data);
    } catch { toast.error('Init failed', { id: 'init' }); }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (demoDisabled) return;
    if (!query.trim()) { toast.error('Enter a search query'); return; }
    setLoading(true);
    try {
      const r = await chromaApi.search(query, n, category || undefined);
      setResults(r.data.results);
      if (r.data.results.length === 0) toast('No results found. Try a different query.');
    } catch { toast.error('Search failed. Ensure ChromaDB is running and knowledge base is initialized.'); }
    finally { setLoading(false); }
  };

  if (demoDisabled) {
    return (
      <DashboardLayout>
        <div className="card border-dashed border-amber-300 bg-amber-50">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Knowledge Search is disabled for this demo</h1>
          <p className="text-sm text-gray-600">The MySQL-first CrisisLink demo is running without optional vector search services. Core disaster-response workflows remain available.</p>
        </div>
      </DashboardLayout>
    );
  }

  const EXAMPLES = [
    'flood evacuation procedure',
    'medical supplies for disaster relief',
    'people trapped during heavy rainfall',
    'emergency shelter management',
    'rescue boat deployment',
    'chemical leak evacuation',
    'earthquake response and triage',
    'communication during disaster',
  ];

  const CATEGORIES = ['', 'flood', 'medical', 'cyclone', 'shelter', 'food', 'water', 'earthquake', 'landslide', 'coordination', 'industrial', 'survival', 'communication'];

  return (
    <DashboardLayout>
      <PageHeader
        title="ChromaDB – Semantic Vector Search"
        subtitle="Natural language search over disaster knowledge using AI embeddings (Unit 4 – Vector Databases)"
        action={<button onClick={initKB} className="btn-ghost text-sm">⚡ Init Knowledge Base</button>}
      />

      {/* Explanation */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-5 text-sm text-indigo-800">
        <p className="font-semibold mb-1">📚 Unit 4 – Vector Databases (ChromaDB)</p>
        <p className="mb-1">ChromaDB converts text into high-dimensional <strong>vector embeddings</strong> using the
        <code className="bg-indigo-100 px-1 rounded"> all-MiniLM-L6-v2</code> sentence transformer model.
        Queries are also embedded and the <strong>cosine similarity</strong> between query and document vectors determines relevance.</p>
        <p>This enables <strong>semantic search</strong> — finding conceptually similar content even without exact keyword matches.</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="card mb-5">
          <div className="flex items-center justify-between">
            <div>
              <span className="font-semibold text-gray-700">Knowledge Base: </span>
              <span className="text-indigo-700 font-bold">{stats.total_documents as number} documents</span>
              <span className="text-gray-500 text-sm ml-2">• Model: {stats.embedding_model as string}</span>
            </div>
            <div className="flex gap-2 flex-wrap">
              {Object.entries((stats.categories as Record<string,number>) || {}).map(([cat, count]) => (
                <span key={cat} className="bg-indigo-50 text-indigo-700 text-xs px-2 py-0.5 rounded-full font-medium">
                  {cat}: {count}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Search form */}
      <form onSubmit={handleSearch} className="card mb-5">
        <div className="flex gap-3 mb-3">
          <div className="flex-1">
            <label className="label">Natural Language Query</label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
              <input className="input pl-9 text-base" placeholder="e.g. flood evacuation for people trapped in buildings"
                value={query} onChange={e => setQuery(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="label">Category Filter</label>
            <select className="input" value={category} onChange={e => setCategory(e.target.value)}>
              {CATEGORIES.map(c => <option key={c} value={c}>{c || 'All categories'}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Results</label>
            <select className="input" value={n} onChange={e => setN(parseInt(e.target.value))}>
              {[3,5,8,10].map(v => <option key={v} value={v}>{v} results</option>)}
            </select>
          </div>
        </div>
        <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
          {loading
            ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            : <Search className="w-4 h-4" />
          }
          {loading ? 'Searching…' : 'Semantic Search'}
        </button>
      </form>

      {/* Example queries */}
      <div className="mb-5">
        <p className="text-xs text-gray-500 mb-2 font-medium">Try these example queries:</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map(ex => (
            <button key={ex} onClick={() => setQuery(ex)}
              className="text-xs bg-gray-100 hover:bg-indigo-50 hover:text-indigo-700 text-gray-700 px-3 py-1.5 rounded-full border border-gray-200 hover:border-indigo-300 transition-colors">
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-3">
            Found <span className="text-indigo-700 font-bold">{results.length}</span> semantically similar documents
          </p>
          <div className="space-y-3">
            {results.map((r, i) => (
              <div key={r.id as string}
                className="card border-l-4 border-l-indigo-500 hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 bg-indigo-600 text-white rounded-full text-xs font-bold flex items-center justify-center">
                      {i + 1}
                    </span>
                    <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded font-medium">
                      {(r.metadata as Record<string,string>)?.category}
                    </span>
                    <span className="text-xs text-gray-500">
                      {(r.metadata as Record<string,string>)?.type}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-500">Similarity</div>
                    <div className={`text-sm font-bold ${
                      (r.similarity as number) > 0.7 ? 'text-green-600' :
                      (r.similarity as number) > 0.4 ? 'text-orange-600' : 'text-red-600'
                    }`}>
                      {((r.similarity as number) * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed">{r.text as string}</p>
                <p className="text-xs text-gray-400 mt-2 font-mono">id: {r.id as string}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
