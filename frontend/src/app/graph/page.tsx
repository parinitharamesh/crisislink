'use client';
import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { neo4jApi } from '@/lib/api';
import { PageHeader, LoadingState } from '@/components/ui';
import toast from 'react-hot-toast';

export default function GraphPage() {
  const [stats,     setStats]     = useState<{ nodes: Array<Record<string,unknown>>; relationships: Array<Record<string,unknown>> } | null>(null);
  const [trace,     setTrace]     = useState<Array<Record<string,unknown>>>([]);
  const [orgs,      setOrgs]      = useState<Array<Record<string,unknown>>>([]);
  const [locations, setLocations] = useState<Array<Record<string,unknown>>>([]);
  const [loading,   setLoading]   = useState(true);
  const [traceLoading, setTraceLoading] = useState(false);
  const [incidentId, setIncidentId] = useState('1');
  const [tab, setTab] = useState<'overview'|'trace'|'orgs'|'locations'>('overview');
  const demoDisabled = true;

  useEffect(() => {
    if (demoDisabled) return;
    neo4jApi.stats()
      .then(r => setStats(r.data))
      .catch(() => toast.error('Neo4j not available or not synced'))
      .finally(() => setLoading(false));
  }, [demoDisabled]);

  const syncNeo4j = async () => {
    if (demoDisabled) return;
    toast.loading('Syncing MySQL → Neo4j…', { id: 'sync' });
    try {
      await neo4jApi.sync();
      toast.success('Neo4j synchronized!', { id: 'sync' });
      const r = await neo4jApi.stats();
      setStats(r.data);
    } catch { toast.error('Sync failed', { id: 'sync' }); }
  };

  const traceIncident = async () => {
    if (demoDisabled) return;
    if (!incidentId) return;
    setTraceLoading(true);
    try {
      const [traceRes, orgRes] = await Promise.all([
        neo4jApi.traceIncident(parseInt(incidentId)),
        neo4jApi.orgsByIncident(parseInt(incidentId)),
      ]);
      setTrace(traceRes.data.trace);
      setOrgs(orgRes.data.organizations);
      const locRes = await neo4jApi.connectedLocations();
      setLocations(locRes.data.connected_locations);
      setTab('trace');
    } catch { toast.error('Graph query failed'); }
    finally { setTraceLoading(false); }
  };

  if (demoDisabled) {
    return (
      <DashboardLayout>
        <div className="card border-dashed border-amber-300 bg-amber-50">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Neo4j Graph is disabled for this demo</h1>
          <p className="text-sm text-gray-600">This environment is running the MySQL-backed disaster-response system only. Graph-based analytics remain available in the source code but are not connected for this demonstration.</p>
        </div>
      </DashboardLayout>
    );
  }

  if (loading) return <DashboardLayout><LoadingState /></DashboardLayout>;

  return (
    <DashboardLayout>
      <PageHeader
        title="Neo4j – Graph Database Exploration"
        subtitle="Visualize relationships between incidents, requests, resources and organizations (Unit 4 – Graph Databases)"
        action={
          <button onClick={syncNeo4j} className="btn-primary text-sm">⚡ Sync MySQL → Neo4j</button>
        }
      />

      {/* Explanation */}
      <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-5 text-sm text-purple-800">
        <p className="font-semibold mb-1">📚 Unit 4 – Graph Databases (Neo4j)</p>
        <p>Neo4j stores entities as <strong>nodes</strong> (Organization, Incident, Resource, etc.) and
        relationships as <strong>edges</strong> (ORGANIZATION_OWNS_RESOURCE, INCIDENT_GENERATES_REQUEST, etc.).
        Cypher queries traverse these paths to answer questions impossible with simple SQL joins.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-5 border-b border-gray-200">
        {([['overview','🗂️ Graph Stats'],['trace','🔍 Incident Trace'],['orgs','🏢 Organizations'],['locations','📍 Locations']] as const).map(([t,l]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-purple-600 text-purple-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>{l}</button>
        ))}
      </div>

      {tab === 'overview' && stats && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="card">
            <h3 className="font-semibold text-gray-800 mb-4">Node Counts</h3>
            {stats.nodes.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <p className="mb-3">No graph data yet.</p>
                <button onClick={syncNeo4j} className="btn-primary text-sm">Sync Now</button>
              </div>
            ) : (
              <div className="space-y-2">
                {stats.nodes.map((n, i) => (
                  <div key={i} className="flex justify-between items-center py-1.5 border-b border-gray-100">
                    <span className="font-medium text-sm text-purple-800">:{n.node_type as string}</span>
                    <span className="bg-purple-100 text-purple-800 text-sm font-bold px-3 py-0.5 rounded-full">
                      {n.count as number}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="card">
            <h3 className="font-semibold text-gray-800 mb-4">Relationships</h3>
            <div className="space-y-2">
              {stats.relationships.map((r, i) => (
                <div key={i} className="flex justify-between items-center py-1.5 border-b border-gray-100">
                  <span className="text-xs font-mono text-blue-800">-[:{r.relationship_type as string}]-&gt;</span>
                  <span className="bg-blue-100 text-blue-800 text-sm font-bold px-3 py-0.5 rounded-full">
                    {r.count as number}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {(tab === 'trace' || tab === 'orgs' || tab === 'locations') && (
        <div className="card mb-5">
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="label">Incident ID to trace</label>
              <input type="number" min={1} className="input" value={incidentId}
                onChange={e => setIncidentId(e.target.value)} placeholder="e.g. 1" />
            </div>
            <button onClick={traceIncident} disabled={traceLoading}
              className="btn-primary flex items-center gap-2">
              {traceLoading
                ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                : '🔍'
              } Trace Incident
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2 font-mono">
            MATCH (i:Incident)→(er:EmergencyRequest)→(a:Assignment)→(r:Resource) RETURN ...
          </p>
        </div>
      )}

      {tab === 'trace' && (
        <div>
          {trace.length === 0
            ? <div className="card text-center py-10 text-gray-400">Run a trace query above.</div>
            : (
              <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
                <table className="min-w-full text-xs divide-y divide-gray-200">
                  <thead className="table-header">
                    <tr>
                      {['Incident','Severity','Request #','Type','Priority','Assignment','Resource','Shelter'].map(h =>
                        <th key={h} className="px-3 py-2 text-left">{h}</th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {trace.map((row, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-3 py-2 font-medium">{row.incident_title as string}</td>
                        <td className="px-3 py-2">{row.severity as string}</td>
                        <td className="px-3 py-2">#{row.request_id as number}</td>
                        <td className="px-3 py-2">{row.request_type as string}</td>
                        <td className="px-3 py-2">{row.priority as string}</td>
                        <td className="px-3 py-2">#{row.assignment_id as number}</td>
                        <td className="px-3 py-2">{(row.resource_name as string) || '—'}</td>
                        <td className="px-3 py-2">{(row.shelter_name as string) || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </div>
      )}

      {tab === 'orgs' && (
        <div className="space-y-3">
          {orgs.length === 0
            ? <div className="card text-center py-10 text-gray-400">Run a trace query first.</div>
            : orgs.map((o, i) => (
              <div key={i} className="card flex justify-between items-center">
                <div>
                  <p className="font-semibold text-gray-800">{o.org_name as string}</p>
                  <p className="text-xs text-gray-500">Type: {o.org_type as string}</p>
                </div>
                <div className="flex gap-4 text-sm text-center">
                  <div><p className="font-bold text-blue-700">{o.resources_deployed as number}</p><p className="text-xs text-gray-500">Resources</p></div>
                  <div><p className="font-bold text-purple-700">{o.assignments as number}</p><p className="text-xs text-gray-500">Assignments</p></div>
                </div>
              </div>
            ))
          }
        </div>
      )}

      {tab === 'locations' && (
        <div className="grid md:grid-cols-2 gap-4">
          {locations.length === 0
            ? <div className="col-span-2 card text-center py-10 text-gray-400">Run a trace query first.</div>
            : locations.map((l, i) => (
              <div key={i} className="card">
                <p className="font-semibold text-gray-800">{l.area_name as string}</p>
                <p className="text-xs text-gray-500 mb-2">{l.state as string}</p>
                <div className="flex gap-2 flex-wrap">
                  {((l.incident_types as string[]) || []).map((t: string) => (
                    <span key={t} className="bg-red-50 text-red-700 text-xs px-2 py-0.5 rounded">{t}</span>
                  ))}
                </div>
                <p className="text-xs text-gray-600 mt-2">{l.incident_count as number} incidents</p>
              </div>
            ))
          }
        </div>
      )}
    </DashboardLayout>
  );
}
