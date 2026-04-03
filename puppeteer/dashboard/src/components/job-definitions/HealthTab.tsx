import { useState, useEffect } from 'react';
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { authenticatedFetch } from '@/auth';

interface DefinitionHealthRow {
  id: string;
  name: string;
  fired: number;
  skipped: number;
  failed: number;
  missed: number;
  health: 'ok' | 'warning' | 'error';
}

interface SchedulingHealthResponse {
  window: string;
  aggregate: { fired: number; skipped: number; failed: number; late: number; missed: number };
  definitions: DefinitionHealthRow[];
}

type Window = '24h' | '7d' | '30d';

const HealthIcon = ({ health }: { health: 'ok' | 'warning' | 'error' }) => {
  if (health === 'ok') {
    return <span className="inline-block h-3 w-3 rounded-full bg-green-500" title="Healthy" />;
  }
  if (health === 'warning') {
    return <span className="inline-block h-3 w-3 rounded-full bg-amber-400" title="Warning" />;
  }
  return <span className="inline-block h-3 w-3 rounded-full bg-red-500" title="Error" />;
};

const makeSparklineData = (row: DefinitionHealthRow) => {
  // Generate a simple 3-bucket placeholder sparkline from aggregate counts
  const total = row.fired + row.missed + row.skipped;
  if (total === 0) {
    return [
      { fired: 0, missed: 0, skipped: 0 },
      { fired: 0, missed: 0, skipped: 0 },
      { fired: 0, missed: 0, skipped: 0 },
    ];
  }
  // Spread evenly across 3 buckets as a rough approximation
  const f3 = Math.floor(row.fired / 3);
  const m3 = Math.floor(row.missed / 3);
  const s3 = Math.floor(row.skipped / 3);
  return [
    { fired: f3, missed: m3, skipped: s3 },
    { fired: f3, missed: m3, skipped: s3 },
    { fired: row.fired - f3 * 2, missed: row.missed - m3 * 2, skipped: row.skipped - s3 * 2 },
  ];
};

const HealthTab = () => {
  const [window, setWindow] = useState<Window>('24h');
  const [health, setHealth] = useState<SchedulingHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDef, setSelectedDef] = useState<DefinitionHealthRow | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    setLoading(true);
    authenticatedFetch(`/api/health/scheduling?window=${window}`)
      .then(res => (res.ok ? res.json() : null))
      .then(data => setHealth(data))
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, [window]);

  const handleRowClick = (row: DefinitionHealthRow) => {
    if (row.health === 'error') {
      setSelectedDef(row);
      setDrawerOpen(true);
    }
  };

  return (
    <div className="space-y-4">
      {/* Window switcher */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground font-bold uppercase tracking-widest mr-2">Window</span>
        {(['24h', '7d', '30d'] as Window[]).map(w => (
          <button
            key={w}
            onClick={() => setWindow(w)}
            className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
              window === w
                ? 'bg-primary text-white'
                : 'bg-muted text-muted-foreground hover:text-foreground'
            }`}
          >
            {w}
          </button>
        ))}
      </div>

      {loading && (
        <div className="py-12 text-center text-muted-foreground text-sm animate-pulse">Loading health data...</div>
      )}

      {!loading && health && (
        <>
          {/* Aggregate summary row */}
          <div className="rounded-xl border border-muted bg-muted/20 px-6 py-4 flex flex-wrap gap-8">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400 tabular-nums">{health.aggregate.fired}</div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Fired</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-amber-400 tabular-nums">{health.aggregate.skipped}</div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Skipped</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-400 tabular-nums">{health.aggregate.failed}</div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Failed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-400 tabular-nums">{health.aggregate.late}</div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Late</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-foreground/80 tabular-nums">{health.aggregate.missed}</div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider mt-1">Missed</div>
            </div>
          </div>

          {/* Per-definition table */}
          {health.definitions.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground text-sm italic">
              No scheduled job definitions found for this window.
            </div>
          ) : (
            <div className="rounded-xl border border-muted overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/30">
                  <tr className="text-left text-muted-foreground text-xs font-bold uppercase tracking-wider">
                    <th className="px-4 py-3 w-8"></th>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3 text-right tabular-nums">Fired</th>
                    <th className="px-4 py-3 text-right tabular-nums">Skipped</th>
                    <th className="px-4 py-3 text-right tabular-nums">Failed</th>
                    <th className="px-4 py-3 text-right tabular-nums">Missed</th>
                    <th className="px-4 py-3 w-28">Trend</th>
                  </tr>
                </thead>
                <tbody>
                  {health.definitions.map(row => (
                    <tr
                      key={row.id}
                      onClick={() => handleRowClick(row)}
                      className={`border-t border-muted transition-colors ${
                        row.health === 'error'
                          ? 'cursor-pointer hover:bg-red-950/20'
                          : 'hover:bg-muted/30'
                      }`}
                    >
                      <td className="px-4 py-3">
                        <HealthIcon health={row.health} />
                      </td>
                      <td className="px-4 py-3 text-foreground font-medium">{row.name}</td>
                      <td className="px-4 py-3 text-right text-green-400 tabular-nums font-mono">{row.fired}</td>
                      <td className="px-4 py-3 text-right text-amber-400 tabular-nums font-mono">{row.skipped}</td>
                      <td className="px-4 py-3 text-right text-red-400 tabular-nums font-mono">{row.failed}</td>
                      <td className="px-4 py-3 text-right text-muted-foreground/80 tabular-nums font-mono">{row.missed}</td>
                      <td className="px-4 py-3">
                        <ResponsiveContainer width="100%" height={40}>
                          <AreaChart data={makeSparklineData(row)}>
                            <Area type="monotone" dataKey="fired" stroke="#22c55e" fill="#22c55e20" dot={false} strokeWidth={1.5} />
                            <Area type="monotone" dataKey="missed" stroke="#ef4444" fill="#ef444420" dot={false} strokeWidth={1.5} />
                            <Area type="monotone" dataKey="skipped" stroke="#f59e0b" fill="#f59e0b20" dot={false} strokeWidth={1.5} />
                            <Tooltip
                              contentStyle={{ background: '#18181b', border: '1px solid #27272a', fontSize: 11 }}
                              itemStyle={{ color: '#a1a1aa' }}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {!loading && !health && (
        <div className="py-12 text-center text-muted-foreground text-sm italic">
          Unable to load scheduling health data. The health endpoint may not be available.
        </div>
      )}

      {/* Detail drawer for error definitions */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent side="right" className="w-[480px] sm:w-[540px] overflow-y-auto bg-background border-muted">
          <SheetHeader>
            <SheetTitle className="text-foreground">Definition Health Detail</SheetTitle>
          </SheetHeader>
          {selectedDef && (
            <div className="mt-6 space-y-6">
              <div>
                <h3 className="text-base font-bold text-foreground">{selectedDef.name}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <HealthIcon health={selectedDef.health} />
                  <span className="text-xs text-red-400 font-medium uppercase tracking-wider">
                    {selectedDef.health === 'error' ? 'Unhealthy' : selectedDef.health}
                  </span>
                </div>
              </div>

              <div className="rounded-lg border border-muted bg-card overflow-hidden">
                <table className="w-full text-sm">
                  <tbody>
                    <tr className="border-b border-muted">
                      <td className="px-4 py-3 text-muted-foreground text-xs font-bold uppercase tracking-wider">Fired</td>
                      <td className="px-4 py-3 text-green-400 font-mono tabular-nums">{selectedDef.fired}</td>
                    </tr>
                    <tr className="border-b border-muted">
                      <td className="px-4 py-3 text-muted-foreground text-xs font-bold uppercase tracking-wider">Skipped</td>
                      <td className="px-4 py-3 text-amber-400 font-mono tabular-nums">{selectedDef.skipped}</td>
                    </tr>
                    <tr className="border-b border-muted">
                      <td className="px-4 py-3 text-muted-foreground text-xs font-bold uppercase tracking-wider">Failed</td>
                      <td className="px-4 py-3 text-red-400 font-mono tabular-nums">{selectedDef.failed}</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-muted-foreground text-xs font-bold uppercase tracking-wider">Missed</td>
                      <td className="px-4 py-3 text-foreground/80 font-mono tabular-nums">{selectedDef.missed}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="rounded-lg border border-red-900/40 bg-red-950/20 px-4 py-4">
                <p className="text-sm text-red-300 leading-relaxed">
                  <span className="font-bold">{selectedDef.missed}</span> scheduled fire
                  {selectedDef.missed !== 1 ? 's were' : ' was'} missed during the selected window.
                  This may indicate no eligible nodes were available at dispatch time, or the previous run
                  was still active with overlap disabled.
                </p>
                {selectedDef.failed > 0 && (
                  <p className="text-sm text-red-300 leading-relaxed mt-2">
                    Additionally, <span className="font-bold">{selectedDef.failed}</span> run
                    {selectedDef.failed !== 1 ? 's' : ''} failed during execution. Check the execution
                    history on the Definitions tab for details.
                  </p>
                )}
              </div>

              <div className="text-xs text-muted-foreground">
                Tip: Check node availability and the allow_overlap setting for this definition.
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default HealthTab;
