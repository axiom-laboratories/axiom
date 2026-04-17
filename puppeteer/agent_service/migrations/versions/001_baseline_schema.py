"""Baseline schema migration representing full current database state.

This migration captures all tables created by SQLAlchemy Base.metadata.create_all,
squashing all 48+ prior SQL migration files into a single Alembic revision.

Revision ID: 001
Revises: None
Create Date: 2025-04-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # jobs table
    op.create_table(
        'jobs',
        sa.Column('guid', sa.String(), nullable=False),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
        sa.Column('node_id', sa.String(), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('scheduled_job_id', sa.String(), nullable=True),
        sa.Column('target_tags', sa.Text(), nullable=True),
        sa.Column('capability_requirements', sa.Text(), nullable=True),
        sa.Column('telemetry', sa.Text(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retry_after', sa.DateTime(), nullable=True),
        sa.Column('backoff_multiplier', sa.Float(), nullable=False, server_default='2.0'),
        sa.Column('timeout_minutes', sa.Integer(), nullable=True),
        sa.Column('depends_on', sa.Text(), nullable=True),
        sa.Column('job_run_id', sa.String(36), nullable=True),
        sa.Column('env_tag', sa.String(32), nullable=True),
        sa.Column('signature_hmac', sa.String(64), nullable=True),
        sa.Column('runtime', sa.String(32), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('originating_guid', sa.String(), nullable=True),
        sa.Column('target_node_id', sa.String(), nullable=True),
        sa.Column('dispatch_timeout_minutes', sa.Integer(), nullable=True),
        sa.Column('memory_limit', sa.String(), nullable=True),
        sa.Column('cpu_limit', sa.String(), nullable=True),
        sa.Column('workflow_step_run_id', sa.String(), nullable=True),
        sa.Column('depth', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('guid'),
        sa.Index('ix_jobs_status_created_at', 'status', 'created_at'),
    )

    # signatures table
    op.create_table(
        'signatures',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('uploaded_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # scheduled_jobs table
    op.create_table(
        'scheduled_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('script_content', sa.Text(), nullable=False),
        sa.Column('signature_id', sa.String(), nullable=False),
        sa.Column('signature_payload', sa.Text(), nullable=False),
        sa.Column('schedule_cron', sa.String(), nullable=True),
        sa.Column('target_node_id', sa.String(), nullable=True),
        sa.Column('target_tags', sa.Text(), nullable=True),
        sa.Column('capability_requirements', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='ACTIVE'),
        sa.Column('pushed_by', sa.String(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('backoff_multiplier', sa.Float(), nullable=False, server_default='2.0'),
        sa.Column('timeout_minutes', sa.Integer(), nullable=True),
        sa.Column('memory_limit', sa.String(), nullable=True),
        sa.Column('cpu_limit', sa.String(), nullable=True),
        sa.Column('env_tag', sa.String(32), nullable=True),
        sa.Column('runtime', sa.String(32), nullable=True, server_default='python'),
        sa.Column('allow_overlap', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('dispatch_timeout_minutes', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # tokens table
    op.create_table(
        'tokens',
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('template_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('token'),
    )

    # config table
    op.create_table(
        'config',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )

    # users table
    op.create_table(
        'users',
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='admin'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('username'),
    )

    # nodes table
    op.create_table(
        'nodes',
        sa.Column('node_id', sa.String(), nullable=False),
        sa.Column('hostname', sa.String(), nullable=False),
        sa.Column('ip', sa.String(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('base_os_family', sa.String(), nullable=True),
        sa.Column('stats', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('operator_tags', sa.Text(), nullable=True),
        sa.Column('capabilities', sa.Text(), nullable=True),
        sa.Column('expected_capabilities', sa.Text(), nullable=True),
        sa.Column('tamper_details', sa.Text(), nullable=True),
        sa.Column('pending_upgrade', sa.Text(), nullable=True),
        sa.Column('upgrade_history', sa.Text(), nullable=True),
        sa.Column('machine_id', sa.String(), nullable=True),
        sa.Column('node_secret_hash', sa.String(), nullable=True),
        sa.Column('client_cert_pem', sa.Text(), nullable=True),
        sa.Column('template_id', sa.String(36), nullable=True),
        sa.Column('env_tag', sa.String(32), nullable=True),
        sa.Column('operator_env_tag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('job_memory_limit', sa.String(), nullable=True),
        sa.Column('job_cpu_limit', sa.String(), nullable=True),
        sa.Column('detected_cgroup_version', sa.String(), nullable=True),
        sa.Column('cgroup_raw', sa.Text(), nullable=True),
        sa.Column('execution_mode', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('node_id'),
    )

    # alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # revoked_certs table
    op.create_table(
        'revoked_certs',
        sa.Column('serial_number', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('serial_number'),
    )

    # node_stats table
    op.create_table(
        'node_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('cpu', sa.Float(), nullable=True),
        sa.Column('ram', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # execution_records table
    op.create_table(
        'execution_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_guid', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('output_log', sa.Text(), nullable=True),
        sa.Column('truncated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('stdout', sa.Text(), nullable=True),
        sa.Column('stderr', sa.Text(), nullable=True),
        sa.Column('script_hash', sa.String(64), nullable=True),
        sa.Column('hash_mismatch', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('attempt_number', sa.Integer(), nullable=True),
        sa.Column('job_run_id', sa.String(36), nullable=True),
        sa.Column('attestation_bundle', sa.Text(), nullable=True),
        sa.Column('attestation_signature', sa.Text(), nullable=True),
        sa.Column('attestation_verified', sa.String(16), nullable=True),
        sa.Column('pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_execution_records_job_guid', 'job_guid'),
        sa.Index('ix_execution_records_started_at', 'started_at'),
        sa.Index('ix_execution_records_node_started', 'node_id', 'started_at'),
        sa.Index('ix_execution_records_job_started', 'job_guid', 'started_at'),
    )

    # scheduled_fire_log table
    op.create_table(
        'scheduled_fire_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scheduled_job_id', sa.String(), nullable=False),
        sa.Column('expected_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='fired'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_fire_log_job_expected', 'scheduled_job_id', 'expected_at'),
    )

    # job_templates table
    op.create_table(
        'job_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('creator_id', sa.String(), nullable=False),
        sa.Column('visibility', sa.String(), nullable=False, server_default='private'),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # signals table
    op.create_table(
        'signals',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('name'),
    )

    # pings table
    op.create_table(
        'pings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # blueprints table
    op.create_table(
        'blueprints',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('definition', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('os_family', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # puppet_templates table
    op.create_table(
        'puppet_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('friendly_name', sa.String(), nullable=True),
        sa.Column('runtime_blueprint_id', sa.String(), nullable=True),
        sa.Column('network_blueprint_id', sa.String(), nullable=True),
        sa.Column('canonical_id', sa.String(), nullable=True),
        sa.Column('current_image_uri', sa.String(), nullable=True),
        sa.Column('last_built_image', sa.String(), nullable=True),
        sa.Column('last_built_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_compliant', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('bom_captured', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_starter', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )

    # capability_matrix table
    op.create_table(
        'capability_matrix',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('base_os_family', sa.String(), nullable=False),
        sa.Column('tool_id', sa.String(), nullable=False),
        sa.Column('injection_recipe', sa.Text(), nullable=True),
        sa.Column('validation_cmd', sa.Text(), nullable=True),
        sa.Column('artifact_id', sa.String(), nullable=True),
        sa.Column('runtime_dependencies', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
    )

    # approved_os table
    op.create_table(
        'approved_os',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('image_uri', sa.String(), nullable=False),
        sa.Column('os_family', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # approved_ingredients table
    op.create_table(
        'approved_ingredients',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version_constraint', sa.String(255), nullable=True),
        sa.Column('sha256', sa.String(64), nullable=True),
        sa.Column('os_family', sa.String(50), nullable=False),
        sa.Column('ecosystem', sa.String(20), nullable=False, server_default='PYPI'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_vulnerable', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('vulnerability_report', sa.Text(), nullable=True),
        sa.Column('mirror_status', sa.String(20), nullable=True, server_default='PENDING'),
        sa.Column('mirror_path', sa.String(), nullable=True),
        sa.Column('mirror_log', sa.Text(), nullable=True),
        sa.Column('auto_discovered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # ingredient_dependencies table
    op.create_table(
        'ingredient_dependencies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.String(36), nullable=False),
        sa.Column('child_id', sa.String(36), nullable=False),
        sa.Column('dependency_type', sa.String(50), nullable=False),
        sa.Column('version_constraint', sa.String(255), nullable=True),
        sa.Column('ecosystem', sa.String(20), nullable=False),
        sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_ingredient_dependencies_parent_id', 'parent_id'),
        sa.Index('ix_ingredient_dependencies_child_id', 'child_id'),
        sa.UniqueConstraint('parent_id', 'child_id', 'ecosystem', name='uq_ingredient_dep'),
    )

    # curated_bundles table
    op.create_table(
        'curated_bundles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ecosystem', sa.String(20), nullable=False),
        sa.Column('os_family', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # curated_bundle_items table
    op.create_table(
        'curated_bundle_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bundle_id', sa.String(36), nullable=False),
        sa.Column('ingredient_name', sa.String(255), nullable=False),
        sa.Column('version_constraint', sa.String(255), nullable=False, server_default='*'),
        sa.Column('ecosystem', sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['bundle_id'], ['curated_bundles.id'], ondelete='CASCADE'),
        sa.Index('ix_curated_bundle_items_bundle_id', 'bundle_id'),
    )

    # image_bom table
    op.create_table(
        'image_bom',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.String(), nullable=False),
        sa.Column('packages', sa.Text(), nullable=True),
        sa.Column('layers', sa.Text(), nullable=True),
        sa.Column('captured_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_image_bom_template_id', 'template_id'),
    )

    # package_index table
    op.create_table(
        'package_index',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('template_id', sa.String(), nullable=True),
        sa.Column('image_uri', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # triggers table
    op.create_table(
        'triggers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('job_definition_id', sa.String(), nullable=False),
        sa.Column('secret_token', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    # audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # role_permissions table
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('permission', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role', 'permission', name='uq_role_permission'),
    )

    # user_signing_keys table
    op.create_table(
        'user_signing_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('public_key_pem', sa.Text(), nullable=False),
        sa.Column('encrypted_private_key', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # user_api_keys table
    op.create_table(
        'user_api_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('key_prefix', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # service_principals table
    op.create_table(
        'service_principals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=False),
        sa.Column('client_secret_hash', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('client_id'),
    )

    # script_analysis_requests table
    op.create_table(
        'script_analysis_requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('requester_id', sa.String(), nullable=False),
        sa.Column('package_name', sa.String(), nullable=False),
        sa.Column('ecosystem', sa.String(20), nullable=False),
        sa.Column('detected_import', sa.String(), nullable=False),
        sa.Column('source_script_hash', sa.String(64), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('review_reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('requester_id', 'package_name', 'ecosystem', 'source_script_hash', name='uq_analysis_request'),
    )

    # workflows table
    op.create_table(
        'workflows',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_paused', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('schedule_cron', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.username']),
    )

    # workflow_steps table
    op.create_table(
        'workflow_steps',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('scheduled_job_id', sa.String(), nullable=True),
        sa.Column('node_type', sa.String(), nullable=False),
        sa.Column('config_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
        sa.ForeignKeyConstraint(['scheduled_job_id'], ['scheduled_jobs.id']),
    )

    # workflow_edges table
    op.create_table(
        'workflow_edges',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('from_step_id', sa.String(), nullable=False),
        sa.Column('to_step_id', sa.String(), nullable=False),
        sa.Column('branch_name', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
        sa.ForeignKeyConstraint(['from_step_id'], ['workflow_steps.id']),
        sa.ForeignKeyConstraint(['to_step_id'], ['workflow_steps.id']),
    )

    # workflow_parameters table
    op.create_table(
        'workflow_parameters',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('default_value', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
    )

    # workflow_webhooks table
    op.create_table(
        'workflow_webhooks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('secret_hash', sa.String(), nullable=False),
        sa.Column('secret_plaintext', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
    )

    # workflow_runs table
    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('trigger_type', sa.String(), nullable=True),
        sa.Column('triggered_by', sa.String(), nullable=True),
        sa.Column('parameters_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
    )

    # workflow_step_runs table
    op.create_table(
        'workflow_step_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_run_id', sa.String(), nullable=False),
        sa.Column('workflow_step_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_run_id'], ['workflow_runs.id']),
        sa.ForeignKeyConstraint(['workflow_step_id'], ['workflow_steps.id']),
    )


def downgrade() -> None:
    # Downgrade by dropping all tables (cascade deletes all constraints and indexes)
    op.drop_table('workflow_step_runs')
    op.drop_table('workflow_runs')
    op.drop_table('workflow_webhooks')
    op.drop_table('workflow_parameters')
    op.drop_table('workflow_edges')
    op.drop_table('workflow_steps')
    op.drop_table('workflows')
    op.drop_table('script_analysis_requests')
    op.drop_table('service_principals')
    op.drop_table('user_api_keys')
    op.drop_table('user_signing_keys')
    op.drop_table('role_permissions')
    op.drop_table('audit_log')
    op.drop_table('triggers')
    op.drop_table('package_index')
    op.drop_table('image_bom')
    op.drop_table('curated_bundle_items')
    op.drop_table('curated_bundles')
    op.drop_table('ingredient_dependencies')
    op.drop_table('approved_ingredients')
    op.drop_table('approved_os')
    op.drop_table('capability_matrix')
    op.drop_table('puppet_templates')
    op.drop_table('blueprints')
    op.drop_table('pings')
    op.drop_table('signals')
    op.drop_table('job_templates')
    op.drop_table('scheduled_fire_log')
    op.drop_table('execution_records')
    op.drop_table('node_stats')
    op.drop_table('revoked_certs')
    op.drop_table('alerts')
    op.drop_table('nodes')
    op.drop_table('users')
    op.drop_table('config')
    op.drop_table('tokens')
    op.drop_table('scheduled_jobs')
    op.drop_table('signatures')
    op.drop_table('jobs')
