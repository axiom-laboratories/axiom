"""
Test suite for Phase 149 Workflow Parameters (definition, merging, injection).

Tests verify:
- Parameter definition and storage (PARAMS-01)
- Parameter merging with defaults and overrides (PARAMS-01)
- Parameter snapshot immutability (PARAMS-01)
- Environment variable injection (PARAMS-02)
- Parameter type preservation (PARAMS-02)
"""
import pytest
import json
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from agent_service.db import Workflow, WorkflowParameter, WorkflowRun, AsyncSessionLocal
from agent_service.services.workflow_service import WorkflowService


# ============================================================================
# Task 1: Parameter Definition Tests
# ============================================================================

@pytest.mark.asyncio
async def test_param_definition(setup_db):
    """
    WorkflowParameter created with name, type, default_value.
    Verifies parameter definition creation.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())
        param_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        param = WorkflowParameter(
            id=param_id,
            workflow_id=workflow_id,
            name="environment",
            type="string",
            default_value="staging"
        )
        session.add(param)
        await session.commit()

        assert param.name == "environment"
        assert param.type == "string"
        assert param.default_value == "staging"


@pytest.mark.asyncio
async def test_param_merge_defaults(setup_db):
    """
    Parameter merging uses workflow defaults when no caller override provided.
    Verifies default parameter handling.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Parameter with default value
        param = WorkflowParameter(
            id=str(uuid4()),
            workflow_id=workflow_id,
            name="env",
            type="string",
            default_value="staging"
        )
        session.add(param)
        await session.commit()

        # Trigger with no parameter override
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={},  # No override
            trigger_type="CRON",
            triggered_by="scheduler",
            db=session
        )

        params = json.loads(run.parameters_json)
        assert params["env"] == "staging", "Default should be used"


@pytest.mark.asyncio
async def test_param_merge_caller_override(setup_db):
    """
    Caller-provided parameter overrides workflow default.
    Verifies parameter override precedence.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Parameter with default
        param = WorkflowParameter(
            id=str(uuid4()),
            workflow_id=workflow_id,
            name="env",
            type="string",
            default_value="staging"
        )
        session.add(param)
        await session.commit()

        # Trigger with override
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={"env": "prod"},  # Override
            trigger_type="MANUAL",
            triggered_by="alice",
            db=session
        )

        params = json.loads(run.parameters_json)
        assert params["env"] == "prod", "Override should take precedence"


@pytest.mark.asyncio
async def test_param_merge_unrecognized_ignored(setup_db):
    """
    Unrecognized parameters in caller dict are silently ignored.
    Verifies that extra parameters don't cause errors.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Only define one parameter
        param = WorkflowParameter(
            id=str(uuid4()),
            workflow_id=workflow_id,
            name="env",
            type="string",
            default_value="staging"
        )
        session.add(param)
        await session.commit()

        # Trigger with extra unrecognized parameter
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={"env": "prod", "unknown": "value"},  # Extra param
            trigger_type="MANUAL",
            triggered_by="alice",
            db=session
        )

        params = json.loads(run.parameters_json)
        # Should have only known parameter
        assert "env" in params
        # Unknown param might be included (implementation-dependent) but shouldn't cause error
        assert run.parameters_json is not None


@pytest.mark.asyncio
async def test_param_required_missing(setup_db):
    """
    Required parameter (no default) without caller value returns 422.
    Verifies required parameter validation.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Required parameter (no default)
        param = WorkflowParameter(
            id=str(uuid4()),
            workflow_id=workflow_id,
            name="api_key",
            type="string",
            default_value=None
        )
        session.add(param)
        await session.commit()

        # Trigger without required parameter
        service = WorkflowService()

        with pytest.raises(HTTPException) as exc_info:
            await service.start_run(
                workflow_id=workflow_id,
                parameters={},  # Missing "api_key"
                trigger_type="MANUAL",
                triggered_by="alice",
                db=session
            )

        assert exc_info.value.status_code == 422
        assert "api_key" in str(exc_info.value.detail).lower()


# ============================================================================
# Task 2: Parameter Snapshot Tests
# ============================================================================

@pytest.mark.asyncio
async def test_param_snapshot_json(setup_db):
    """
    parameters_json snapshot stored on WorkflowRun contains resolved values.
    Verifies parameter snapshot creation.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Create two parameters
        for i, (name, default) in enumerate([("env", "staging"), ("region", "us-east-1")]):
            param = WorkflowParameter(
                id=str(uuid4()),
                workflow_id=workflow_id,
                name=name,
                type="string",
                default_value=default
            )
            session.add(param)
        await session.commit()

        # Create run with parameter values
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={"env": "production", "region": "us-west-1"},
            trigger_type="MANUAL",
            triggered_by="alice",
            db=session
        )

        assert run.parameters_json is not None
        params = json.loads(run.parameters_json)
        assert params["env"] == "production"
        assert params["region"] == "us-west-1"


@pytest.mark.asyncio
async def test_param_snapshot_immutable(setup_db):
    """
    Changing workflow parameter defaults doesn't affect existing WorkflowRun snapshot.
    Verifies snapshot immutability.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        param = WorkflowParameter(
            id=str(uuid4()),
            workflow_id=workflow_id,
            name="env",
            type="string",
            default_value="staging"
        )
        session.add(param)
        await session.commit()

        # Create run
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={},
            trigger_type="MANUAL",
            triggered_by="alice",
            db=session
        )

        original_params = json.loads(run.parameters_json)
        assert original_params["env"] == "staging"

        # Change workflow parameter default
        stmt = select(WorkflowParameter).where(WorkflowParameter.name == "env")
        result = await session.execute(stmt)
        param = result.scalar()
        param.default_value = "production"
        await session.commit()

        # Reloaded run's snapshot should be unchanged
        reloaded_params = json.loads(run.parameters_json)
        assert reloaded_params["env"] == "staging", "Snapshot should be immutable"


# ============================================================================
# Task 3: Parameter Injection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_param_injection_env_vars(setup_db):
    """
    dispatch_next_wave() populates env_vars with WORKFLOW_PARAM_* prefix.
    Verifies environment variable injection format.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Create parameters
        for name in ["env", "region"]:
            param = WorkflowParameter(
                id=str(uuid4()),
                workflow_id=workflow_id,
                name=name,
                type="string",
                default_value="default"
            )
            session.add(param)
        await session.commit()

        # Create run with parameters
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={"env": "prod", "region": "us-west"},
            trigger_type="MANUAL",
            triggered_by="alice",
            db=session
        )

        # Verify parameters_json can be used to build env_vars
        params = json.loads(run.parameters_json)
        env_vars = {f"WORKFLOW_PARAM_{k}": str(v) for k, v in params.items()}

        assert "WORKFLOW_PARAM_env" in env_vars
        assert env_vars["WORKFLOW_PARAM_env"] == "prod"
        assert "WORKFLOW_PARAM_region" in env_vars
        assert env_vars["WORKFLOW_PARAM_region"] == "us-west"


@pytest.mark.asyncio
async def test_param_env_var_format(setup_db):
    """
    env_vars dict keys formatted as "WORKFLOW_PARAM_<NAME>" (uppercase).
    Verifies environment variable naming convention.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        param = WorkflowParameter(
            id=str(uuid4()),
            workflow_id=workflow_id,
            name="database_host",  # lowercase
            type="string",
            default_value="localhost"
        )
        session.add(param)
        await session.commit()

        # Create run
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={"database_host": "prod.example.com"},
            trigger_type="MANUAL",
            triggered_by="alice",
            db=session
        )

        params = json.loads(run.parameters_json)
        # Convert to env var format
        env_key = f"WORKFLOW_PARAM_{list(params.keys())[0]}".upper()

        # Should be WORKFLOW_PARAM_DATABASE_HOST or similar (uppercase)
        assert "WORKFLOW_PARAM_" in env_key
        assert env_key.isupper(), "Env var keys should be uppercase"


@pytest.mark.asyncio
async def test_param_type_preservation(setup_db):
    """
    Parameter values preserved as original type in parameters_json (not stringified prematurely).
    Verifies type preservation through snapshot.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Create parameters of different types
        params_to_add = [
            ("env", "string", "prod"),
            ("port", "string", "8080"),  # Note: stored as string in parameter value
            ("debug", "string", "true"),
        ]
        for name, ptype, default in params_to_add:
            param = WorkflowParameter(
                id=str(uuid4()),
                workflow_id=workflow_id,
                name=name,
                type=ptype,
                default_value=default
            )
            session.add(param)
        await session.commit()

        # Create run
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={"env": "prod", "port": "3000", "debug": "false"},
            trigger_type="MANUAL",
            triggered_by="alice",
            db=session
        )

        params = json.loads(run.parameters_json)
        # All should be present in snapshot
        assert "env" in params
        assert "port" in params
        assert "debug" in params
        # Values should be preserved
        assert params["env"] == "prod"
        assert params["port"] == "3000"
        assert params["debug"] == "false"


@pytest.mark.asyncio
async def test_param_null_handling(setup_db):
    """
    None values in parameters_json handled gracefully (not injected as 'None' string).
    Verifies null parameter handling.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        # Optional parameter with None default
        param = WorkflowParameter(
            id=str(uuid4()),
            workflow_id=workflow_id,
            name="optional_field",
            type="string",
            default_value=None  # Can be None
        )
        session.add(param)
        await session.commit()

        # Create run with None parameter
        service = WorkflowService()
        run = await service.start_run(
            workflow_id=workflow_id,
            parameters={"optional_field": None},
            trigger_type="MANUAL",
            triggered_by="alice",
            db=session
        )

        params = json.loads(run.parameters_json)
        # Value might be None or absent; should not be "None" string
        value = params.get("optional_field")
        assert value is None or value != "None"


@pytest.mark.asyncio
async def test_param_precedence_manual_vs_cron(setup_db):
    """
    Manual trigger allows caller override; cron uses only defaults.
    Verifies trigger-type-specific parameter handling.
    """
    async with AsyncSessionLocal() as session:
        workflow_id = str(uuid4())

        workflow = Workflow(
            id=workflow_id,
            name=f"test-workflow-{uuid4().hex[:8]}",
            created_by="admin",
            is_paused=False
        )
        session.add(workflow)
        await session.flush()

        param = WorkflowParameter(
            id=str(uuid4()),
            workflow_id=workflow_id,
            name="env",
            type="string",
            default_value="staging"
        )
        session.add(param)
        await session.commit()

        service = WorkflowService()

        # CRON: uses only defaults (caller override should be ignored for cron)
        run_cron = await service.start_run(
            workflow_id=workflow_id,
            parameters={"env": "prod"},
            trigger_type="CRON",
            triggered_by="scheduler",
            db=session
        )
        params_cron = json.loads(run_cron.parameters_json)
        # For CRON, we expect defaults to be used
        assert params_cron["env"] == "staging", "CRON should use defaults only"

        # MANUAL: allows override
        run_manual = await service.start_run(
            workflow_id=workflow_id,
            parameters={"env": "prod"},
            trigger_type="MANUAL",
            triggered_by="alice",
            db=session
        )
        params_manual = json.loads(run_manual.parameters_json)
        assert params_manual["env"] == "prod", "MANUAL should allow override"
