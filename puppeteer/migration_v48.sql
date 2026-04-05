-- Migration v48: Add last_built_image column to puppet_templates and seed curated bundles
-- For existing Postgres deployments only (fresh deployments use create_all)

-- Add last_built_image column if not exists
ALTER TABLE puppet_templates ADD COLUMN IF NOT EXISTS last_built_image VARCHAR(255);

-- Seed curated bundles for starter templates
INSERT INTO curated_bundles (id, name, description, ecosystem, os_family, is_active, created_at)
VALUES
  ('bundle-datascience', 'Data Science', 'Python data analysis stack: numpy, pandas, scikit-learn, matplotlib', 'PYPI', 'DEBIAN', true, NOW()),
  ('bundle-webapi', 'Web/API', 'FastAPI/Flask web development: FastAPI, Flask, Django, SQLAlchemy, requests', 'PYPI', 'DEBIAN', true, NOW()),
  ('bundle-network', 'Network Tools', 'Network diagnostics and analysis: curl, nmap, tcpdump, netcat, iperf', 'APT', 'DEBIAN', true, NOW()),
  ('bundle-fileproc', 'File Processing', 'Document and image processing: Pillow, pdf2image, python-docx, openpyxl', 'PYPI', 'DEBIAN', true, NOW()),
  ('bundle-winautom', 'Windows Automation', 'PowerShell and Windows administration: Active Directory, WMI utilities', 'NUGET', 'WINDOWS', true, NOW())
ON CONFLICT DO NOTHING;

-- Seed bundle items
INSERT INTO curated_bundle_items (id, bundle_id, ingredient_name, version_constraint, ecosystem)
VALUES
  -- Data Science bundle
  ('item-ds-1', 'bundle-datascience', 'numpy', '*', 'PYPI'),
  ('item-ds-2', 'bundle-datascience', 'pandas', '*', 'PYPI'),
  ('item-ds-3', 'bundle-datascience', 'scikit-learn', '*', 'PYPI'),
  ('item-ds-4', 'bundle-datascience', 'matplotlib', '*', 'PYPI'),
  -- Web/API bundle
  ('item-api-1', 'bundle-webapi', 'fastapi', '*', 'PYPI'),
  ('item-api-2', 'bundle-webapi', 'flask', '*', 'PYPI'),
  ('item-api-3', 'bundle-webapi', 'django', '*', 'PYPI'),
  ('item-api-4', 'bundle-webapi', 'sqlalchemy', '*', 'PYPI'),
  ('item-api-5', 'bundle-webapi', 'requests', '*', 'PYPI'),
  -- Network Tools bundle
  ('item-net-1', 'bundle-network', 'curl', '*', 'APT'),
  ('item-net-2', 'bundle-network', 'nmap', '*', 'APT'),
  ('item-net-3', 'bundle-network', 'tcpdump', '*', 'APT'),
  ('item-net-4', 'bundle-network', 'netcat', '*', 'APT'),
  ('item-net-5', 'bundle-network', 'iperf3', '*', 'APT'),
  -- File Processing bundle
  ('item-fp-1', 'bundle-fileproc', 'Pillow', '*', 'PYPI'),
  ('item-fp-2', 'bundle-fileproc', 'pdf2image', '*', 'PYPI'),
  ('item-fp-3', 'bundle-fileproc', 'python-docx', '*', 'PYPI'),
  ('item-fp-4', 'bundle-fileproc', 'openpyxl', '*', 'PYPI'),
  -- Windows Automation bundle
  ('item-wa-1', 'bundle-winautom', 'ActiveDirectory', '*', 'NUGET')
ON CONFLICT DO NOTHING;
