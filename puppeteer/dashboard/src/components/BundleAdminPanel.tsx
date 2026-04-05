import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Pencil, ChevronDown, ChevronUp, Loader2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { authenticatedFetch } from '../auth';

interface CuratedBundleItem {
  id: string;
  bundle_id: string;
  ingredient_name: string;
  version_constraint: string;
  ecosystem: string;
}

interface CuratedBundle {
  id: string;
  name: string;
  description?: string;
  ecosystem: string;
  os_family: string;
  is_active: boolean;
  created_at: string;
  items: CuratedBundleItem[];
}

interface BundleFormData {
  name: string;
  description?: string;
  ecosystem: string;
  os_family: string;
  is_active?: boolean;
}

interface BundleItemFormData {
  ingredient_name: string;
  version_constraint: string;
  ecosystem: string;
}

export const BundleAdminPanel = () => {
  const queryClient = useQueryClient();
  const [expandedBundles, setExpandedBundles] = useState<Set<string>>(new Set());
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [itemDialogOpen, setItemDialogOpen] = useState(false);
  const [deleteAlertOpen, setDeleteAlertOpen] = useState(false);
  const [deleteItemAlertOpen, setDeleteItemAlertOpen] = useState(false);
  const [selectedBundle, setSelectedBundle] = useState<CuratedBundle | null>(null);
  const [selectedItem, setSelectedItem] = useState<CuratedBundleItem | null>(null);
  const [formData, setFormData] = useState<BundleFormData>({
    name: '',
    description: '',
    ecosystem: 'PYPI',
    os_family: 'DEBIAN',
    is_active: true,
  });
  const [itemFormData, setItemFormData] = useState<BundleItemFormData>({
    ingredient_name: '',
    version_constraint: '*',
    ecosystem: 'PYPI',
  });

  const ecosystemOptions = ['PYPI', 'APT', 'APK', 'CONDA', 'NUGET', 'OCI', 'NPM'];
  const osFamilyOptions = ['DEBIAN', 'ALPINE', 'WINDOWS'];

  // Fetch bundles
  const { data: bundles = [], isLoading, error } = useQuery({
    queryKey: ['bundles'],
    queryFn: async () => {
      const response = await authenticatedFetch('/api/admin/bundles');
      if (!response.ok) throw new Error('Failed to fetch bundles');
      return response.json();
    },
  });

  // Create bundle mutation
  const createBundleMutation = useMutation({
    mutationFn: async (data: BundleFormData) => {
      const response = await authenticatedFetch('/api/admin/bundles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error('Failed to create bundle');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bundles'] });
      setCreateDialogOpen(false);
      setFormData({ name: '', description: '', ecosystem: 'PYPI', os_family: 'DEBIAN', is_active: true });
      toast.success('Bundle created successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to create bundle: ${error.message}`);
    },
  });

  // Update bundle mutation
  const updateBundleMutation = useMutation({
    mutationFn: async (data: BundleFormData) => {
      if (!selectedBundle) throw new Error('No bundle selected');
      const response = await authenticatedFetch(`/api/admin/bundles/${selectedBundle.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error('Failed to update bundle');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bundles'] });
      setEditDialogOpen(false);
      setSelectedBundle(null);
      setFormData({ name: '', description: '', ecosystem: 'PYPI', os_family: 'DEBIAN', is_active: true });
      toast.success('Bundle updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update bundle: ${error.message}`);
    },
  });

  // Delete bundle mutation
  const deleteBundleMutation = useMutation({
    mutationFn: async (bundleId: string) => {
      const response = await authenticatedFetch(`/api/admin/bundles/${bundleId}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete bundle');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bundles'] });
      setDeleteAlertOpen(false);
      setSelectedBundle(null);
      toast.success('Bundle deleted successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to delete bundle: ${error.message}`);
    },
  });

  // Add item to bundle
  const addItemMutation = useMutation({
    mutationFn: async (data: BundleItemFormData) => {
      if (!selectedBundle) throw new Error('No bundle selected');
      const response = await authenticatedFetch(`/api/admin/bundles/${selectedBundle.id}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error('Failed to add item');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bundles'] });
      setItemDialogOpen(false);
      setItemFormData({ ingredient_name: '', version_constraint: '*', ecosystem: 'PYPI' });
      toast.success('Item added successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to add item: ${error.message}`);
    },
  });

  // Delete item from bundle
  const deleteItemMutation = useMutation({
    mutationFn: async (itemId: string) => {
      if (!selectedBundle) throw new Error('No bundle selected');
      const response = await authenticatedFetch(`/api/admin/bundles/${selectedBundle.id}/items/${itemId}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete item');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bundles'] });
      setDeleteItemAlertOpen(false);
      setSelectedItem(null);
      toast.success('Item removed successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to remove item: ${error.message}`);
    },
  });

  const handleCreateClick = () => {
    setFormData({ name: '', description: '', ecosystem: 'PYPI', os_family: 'DEBIAN', is_active: true });
    setSelectedBundle(null);
    setCreateDialogOpen(true);
  };

  const handleEditClick = (bundle: CuratedBundle) => {
    setSelectedBundle(bundle);
    setFormData({
      name: bundle.name,
      description: bundle.description || '',
      ecosystem: bundle.ecosystem,
      os_family: bundle.os_family,
      is_active: bundle.is_active,
    });
    setEditDialogOpen(true);
  };

  const handleDeleteClick = (bundle: CuratedBundle) => {
    setSelectedBundle(bundle);
    setDeleteAlertOpen(true);
  };

  const handleAddItemClick = (bundle: CuratedBundle) => {
    setSelectedBundle(bundle);
    setItemFormData({ ingredient_name: '', version_constraint: '*', ecosystem: bundle.ecosystem });
    setItemDialogOpen(true);
  };

  const handleDeleteItemClick = (bundle: CuratedBundle, item: CuratedBundleItem) => {
    setSelectedBundle(bundle);
    setSelectedItem(item);
    setDeleteItemAlertOpen(true);
  };

  const toggleExpandBundle = (bundleId: string) => {
    const newExpanded = new Set(expandedBundles);
    if (newExpanded.has(bundleId)) {
      newExpanded.delete(bundleId);
    } else {
      newExpanded.add(bundleId);
    }
    setExpandedBundles(newExpanded);
  };

  const handleCreateSubmit = () => {
    createBundleMutation.mutate(formData);
  };

  const handleEditSubmit = () => {
    updateBundleMutation.mutate(formData);
  };

  const handleAddItemSubmit = () => {
    addItemMutation.mutate(itemFormData);
  };

  if (error) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="pt-6 flex items-center gap-2 text-red-600">
          <AlertCircle className="h-4 w-4" />
          <span>Failed to load bundles</span>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center h-32">
          <Loader2 className="h-4 w-4 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">Curated Bundles</h3>
          <p className="text-sm text-muted-foreground">Manage pre-built package bundles for node provisioning</p>
        </div>
        <Button onClick={handleCreateClick} className="gap-2">
          <Plus className="h-4 w-4" />
          Create Bundle
        </Button>
      </div>

      {bundles.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground mb-4">No bundles created yet</p>
            <Button onClick={handleCreateClick} variant="outline" className="gap-2">
              <Plus className="h-4 w-4" />
              Create Your First Bundle
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2 border rounded-lg divide-y">
          {bundles.map((bundle: CuratedBundle) => (
            <div key={bundle.id}>
              <div className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors">
                <button
                  onClick={() => toggleExpandBundle(bundle.id)}
                  className="flex items-center gap-3 flex-1 text-left"
                >
                  {expandedBundles.has(bundle.id) ? (
                    <ChevronUp className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  )}
                  <div className="flex-1">
                    <div className="font-semibold">{bundle.name}</div>
                    <div className="text-sm text-muted-foreground">{bundle.description}</div>
                  </div>
                </button>
                <div className="flex items-center gap-2 ml-4">
                  <Badge variant="outline" className="font-mono text-xs">{bundle.ecosystem}</Badge>
                  <Badge variant="outline" className="font-mono text-xs">{bundle.os_family}</Badge>
                  <Badge variant="outline" className="font-mono text-xs">{bundle.items.length} items</Badge>
                </div>
                <div className="flex gap-2 ml-4">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEditClick(bundle)}
                    className="gap-1"
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDeleteClick(bundle)}
                    className="gap-1 text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {expandedBundles.has(bundle.id) && (
                <div className="bg-muted/30 border-t p-4 space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <h4 className="font-semibold text-sm">Items ({bundle.items.length})</h4>
                      <Button
                        size="sm"
                        onClick={() => handleAddItemClick(bundle)}
                        className="gap-1"
                      >
                        <Plus className="h-3 w-3" />
                        Add Item
                      </Button>
                    </div>
                    {bundle.items.length === 0 ? (
                      <p className="text-xs text-muted-foreground">No items in this bundle</p>
                    ) : (
                      <div className="space-y-2">
                        {bundle.items.map((item: CuratedBundleItem) => (
                          <div key={item.id} className="flex items-center justify-between bg-background p-2 rounded border">
                            <div className="text-sm">
                              <div className="font-mono">{item.ingredient_name}</div>
                              <div className="text-xs text-muted-foreground">{item.version_constraint} • {item.ecosystem}</div>
                            </div>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDeleteItemClick(bundle, item)}
                              className="text-red-600 hover:text-red-700"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Bundle Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Bundle</DialogTitle>
            <DialogDescription>Create a new curated bundle for node provisioning</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Bundle Name</Label>
              <Input
                id="name"
                placeholder="e.g., Data Science"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Brief description of the bundle"
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="resize-none"
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ecosystem">Ecosystem</Label>
              <Select value={formData.ecosystem} onValueChange={(value) => setFormData({ ...formData, ecosystem: value })}>
                <SelectTrigger id="ecosystem">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ecosystemOptions.map(eco => (
                    <SelectItem key={eco} value={eco}>{eco}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="os_family">OS Family</Label>
              <Select value={formData.os_family} onValueChange={(value) => setFormData({ ...formData, os_family: value })}>
                <SelectTrigger id="os_family">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {osFamilyOptions.map(os => (
                    <SelectItem key={os} value={os}>{os}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateSubmit} disabled={!formData.name || createBundleMutation.isPending}>
              {createBundleMutation.isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Bundle Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Bundle</DialogTitle>
            <DialogDescription>Update bundle details</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Bundle Name</Label>
              <Input
                id="edit-name"
                placeholder="e.g., Data Science"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                placeholder="Brief description of the bundle"
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="resize-none"
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-ecosystem">Ecosystem</Label>
              <Select value={formData.ecosystem} onValueChange={(value) => setFormData({ ...formData, ecosystem: value })}>
                <SelectTrigger id="edit-ecosystem">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ecosystemOptions.map(eco => (
                    <SelectItem key={eco} value={eco}>{eco}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-os_family">OS Family</Label>
              <Select value={formData.os_family} onValueChange={(value) => setFormData({ ...formData, os_family: value })}>
                <SelectTrigger id="edit-os_family">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {osFamilyOptions.map(os => (
                    <SelectItem key={os} value={os}>{os}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleEditSubmit} disabled={!formData.name || updateBundleMutation.isPending}>
              {updateBundleMutation.isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Update
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Item Dialog */}
      <Dialog open={itemDialogOpen} onOpenChange={setItemDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Item to Bundle</DialogTitle>
            <DialogDescription>Add a package to the bundle</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ingredient">Package Name</Label>
              <Input
                id="ingredient"
                placeholder="e.g., numpy"
                value={itemFormData.ingredient_name}
                onChange={(e) => setItemFormData({ ...itemFormData, ingredient_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="version">Version Constraint</Label>
              <Input
                id="version"
                placeholder="e.g., * or ==1.0.0"
                value={itemFormData.version_constraint}
                onChange={(e) => setItemFormData({ ...itemFormData, version_constraint: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="item-ecosystem">Ecosystem</Label>
              <Select value={itemFormData.ecosystem} onValueChange={(value) => setItemFormData({ ...itemFormData, ecosystem: value })}>
                <SelectTrigger id="item-ecosystem">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ecosystemOptions.map(eco => (
                    <SelectItem key={eco} value={eco}>{eco}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setItemDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAddItemSubmit} disabled={!itemFormData.ingredient_name || addItemMutation.isPending}>
              {addItemMutation.isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Add Item
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Bundle Alert Dialog */}
      <AlertDialog open={deleteAlertOpen} onOpenChange={setDeleteAlertOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Bundle</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{selectedBundle?.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => selectedBundle && deleteBundleMutation.mutate(selectedBundle.id)}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Item Alert Dialog */}
      <AlertDialog open={deleteItemAlertOpen} onOpenChange={setDeleteItemAlertOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Item</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove "{selectedItem?.ingredient_name}" from this bundle?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => selectedItem && deleteItemMutation.mutate(selectedItem.id)}
              className="bg-red-600 hover:bg-red-700"
            >
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
