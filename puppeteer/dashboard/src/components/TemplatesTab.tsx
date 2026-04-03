import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authenticatedFetch, getUser } from '@/auth';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';

interface TemplateItem {
  id: string;
  name: string;
  creator_id: string;
  visibility: 'private' | 'shared';
  payload: Record<string, unknown>;
  created_at: string;
}

const TemplatesTab = () => {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const currentUser = getUser();

  const loadTemplates = () => {
    setLoading(true);
    authenticatedFetch('/api/job-templates')
      .then(res => (res.ok ? res.json() : []))
      .then(data => setTemplates(Array.isArray(data) ? data : []))
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleLoad = (template: TemplateItem) => {
    navigate(`/jobs?template_id=${template.id}`);
  };

  const handleRenameStart = (template: TemplateItem) => {
    setRenamingId(template.id);
    setRenameValue(template.name);
  };

  const handleRenameConfirm = async (id: string) => {
    if (!renameValue.trim()) {
      setRenamingId(null);
      return;
    }
    try {
      const res = await authenticatedFetch(`/api/job-templates/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: renameValue.trim() }),
      });
      if (res.ok) {
        toast.success('Template renamed');
        loadTemplates();
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || 'Failed to rename template');
      }
    } catch {
      toast.error('Rename error');
    } finally {
      setRenamingId(null);
    }
  };

  const handleVisibilityToggle = async (template: TemplateItem) => {
    const newVisibility = template.visibility === 'private' ? 'shared' : 'private';
    try {
      const res = await authenticatedFetch(`/api/job-templates/${template.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ visibility: newVisibility }),
      });
      if (res.ok) {
        toast.success(`Template is now ${newVisibility}`);
        loadTemplates();
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || 'Failed to update visibility');
      }
    } catch {
      toast.error('Visibility update error');
    }
  };

  const handleDelete = async (template: TemplateItem) => {
    if (!window.confirm(`Delete template "${template.name}"? This cannot be undone.`)) return;
    try {
      const res = await authenticatedFetch(`/api/job-templates/${template.id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        toast.success('Template deleted');
        loadTemplates();
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || 'Failed to delete template');
      }
    } catch {
      toast.error('Delete error');
    }
  };

  const canManage = (template: TemplateItem) => {
    if (!currentUser) return false;
    return currentUser.role === 'admin' || currentUser.sub === template.creator_id;
  };

  if (loading) {
    return <div className="py-12 text-center text-muted-foreground text-sm animate-pulse">Loading templates...</div>;
  }

  if (templates.length === 0) {
    return (
      <div className="py-16 text-center">
        <p className="text-muted-foreground text-sm">No templates saved yet.</p>
        <p className="text-muted-foreground/60 text-xs mt-2">
          Use "Save as Template" in the job dispatch form to reuse configurations.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-muted overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/30">
          <tr className="text-left text-muted-foreground text-xs font-bold uppercase tracking-wider">
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">Visibility</th>
            <th className="px-4 py-3">Creator</th>
            <th className="px-4 py-3">Created</th>
            <th className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {templates.map(template => (
            <tr key={template.id} className="border-t border-muted hover:bg-muted/30 transition-colors">
              <td className="px-4 py-3 text-foreground font-medium">
                {renamingId === template.id ? (
                  <div className="flex items-center gap-2">
                    <input
                      autoFocus
                      type="text"
                      value={renameValue}
                      onChange={e => setRenameValue(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') handleRenameConfirm(template.id);
                        if (e.key === 'Escape') setRenamingId(null);
                      }}
                      className="bg-muted border border-muted/60 rounded px-2 py-1 text-sm text-foreground w-48 focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <button
                      onClick={() => handleRenameConfirm(template.id)}
                      className="text-xs text-green-400 hover:text-green-300 font-bold"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setRenamingId(null)}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  template.name
                )}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                    template.visibility === 'shared'
                      ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                      : 'bg-muted text-muted-foreground border-muted'
                  }`}
                >
                  {template.visibility.toUpperCase()}
                </span>
              </td>
              <td className="px-4 py-3 text-muted-foreground/80 text-xs font-mono">{template.creator_id}</td>
              <td className="px-4 py-3 text-muted-foreground/80 text-xs whitespace-nowrap">
                {template.created_at
                  ? formatDistanceToNow(new Date(template.created_at), { addSuffix: true })
                  : '—'}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2 justify-end">
                  <button
                    onClick={() => handleLoad(template)}
                    className="px-3 py-1 rounded text-xs font-bold bg-primary/20 text-primary hover:bg-primary/30 transition-colors"
                  >
                    Load
                  </button>
                  {canManage(template) && (
                    <>
                      <button
                        onClick={() => handleRenameStart(template)}
                        className="px-3 py-1 rounded text-xs font-bold bg-muted text-muted-foreground hover:bg-muted/70 transition-colors"
                      >
                        Rename
                      </button>
                      <button
                        onClick={() => handleVisibilityToggle(template)}
                        className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
                          template.visibility === 'private'
                            ? 'bg-blue-900/40 text-blue-400 hover:bg-blue-900/60'
                            : 'bg-muted text-muted-foreground hover:bg-muted/70'
                        }`}
                      >
                        {template.visibility === 'private' ? 'Share' : 'Privatise'}
                      </button>
                      <button
                        onClick={() => handleDelete(template)}
                        className="px-3 py-1 rounded text-xs font-bold bg-red-900/30 text-red-400 hover:bg-red-900/50 transition-colors"
                      >
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TemplatesTab;
