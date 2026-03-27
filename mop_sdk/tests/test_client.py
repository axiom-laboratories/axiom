import pytest
from unittest.mock import patch, MagicMock
from mop_sdk.client import MOPClient

@patch("httpx.Client.request")
def test_push_job(mock_request):
    mock_request.return_value = MagicMock(
        status_code=200,
        json=lambda: {"id": "job123", "status": "DRAFT"}
    )
    
    client = MOPClient("http://test")
    client.token = "jwt123"
    
    result = client.push_job(
        script_content="print('hi')",
        signature="sig123",
        signature_id="key123",
        name="my-job"
    )
    
    assert result["id"] == "job123"
    assert result["status"] == "DRAFT"
    
    # Verify call
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == "http://test/api/jobs/push"
    assert kwargs["json"]["name"] == "my-job"
    assert kwargs["headers"]["Authorization"] == "Bearer jwt123"

@patch("httpx.Client.request")
def test_create_job_definition(mock_request):
    mock_request.return_value = MagicMock(
        status_code=200,
        json=lambda: {"id": "job456", "status": "ACTIVE"}
    )
    
    client = MOPClient("http://test")
    client.token = "jwt123"
    
    result = client.create_job_definition(
        name="active-job",
        script_content="print('hi')",
        signature="sig123",
        signature_id="key123",
        schedule_cron="* * * * *"
    )
    
    assert result["id"] == "job456"
    assert result["status"] == "ACTIVE"
    
    # Verify call
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1] == "http://test/jobs/definitions"
    assert kwargs["json"]["is_active"] is True

def test_client_from_store():
    mock_store = MagicMock()
    mock_store.load.return_value = {
        "base_url": "http://test",
        "access_token": "token123"
    }
    
    client = MOPClient.from_store(store=mock_store)
    assert client.base_url == "http://test"
    assert client.token == "token123"

def test_client_from_store_not_logged_in():
    mock_store = MagicMock()
    mock_store.load.return_value = None

    with pytest.raises(Exception, match="Not logged in"):
        MOPClient.from_store(store=mock_store)


# --- New methods: register_signature, list_signatures, get_me ---

@patch("httpx.Client.request")
def test_register_signature(mock_request):
    """register_signature POSTs to /signatures and returns the response dict."""
    mock_request.return_value = MagicMock(
        status_code=201,
        json=lambda: {
            "id": "sig-abc",
            "name": "alice@host",
            "public_key": "---PEM---",
            "uploaded_by": "alice",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )

    client = MOPClient("http://test")
    client.token = "jwt123"

    result = client.register_signature(name="alice@host", public_key="---PEM---")

    assert result["id"] == "sig-abc"
    assert result["name"] == "alice@host"

    # Verify the POST was made to /signatures
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert "/signatures" in args[1]
    assert kwargs["json"]["name"] == "alice@host"
    assert kwargs["json"]["public_key"] == "---PEM---"


@patch("httpx.Client.request")
def test_list_signatures(mock_request):
    """list_signatures GETs /signatures and returns the list."""
    mock_request.return_value = MagicMock(
        status_code=200,
        json=lambda: [{"id": "sig-abc", "name": "alice@host"}],
    )

    client = MOPClient("http://test")
    client.token = "jwt123"

    result = client.list_signatures()

    assert isinstance(result, list)
    assert result[0]["id"] == "sig-abc"

    args, kwargs = mock_request.call_args
    assert args[0] == "GET"
    assert "/signatures" in args[1]
