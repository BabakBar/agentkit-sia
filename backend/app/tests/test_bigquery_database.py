from unittest.mock import Mock, patch

import pytest
from google.cloud.bigquery import QueryJob
from google.cloud.bigquery.table import RowIterator

from app.core.config import settings
from app.db.bigquery_database import BigQueryDatabase, QueryCostError
from app.schemas.ga4_schema import GA4Schema


@pytest.fixture
def mock_credentials():
    """Mock credentials for testing."""
    with patch("google.oauth2.service_account.Credentials") as mock:
        yield mock


@pytest.fixture
def mock_client():
    """Mock BigQuery client for testing."""
    with patch("google.cloud.bigquery.Client") as mock:
        yield mock


@pytest.fixture
def bigquery_settings(tmp_path):
    """Setup test settings for BigQuery."""
    # Create a temporary credentials file
    creds_file = tmp_path / "fake_credentials.json"
    creds_file.write_text("{}")
    
    # Create a new settings instance with test values
    test_settings = settings.model_copy(update={
        "BIGQUERY_ENABLED": True,
        "BIGQUERY_PROJECT_ID": "test-project",
        "BIGQUERY_DATASET": "test_dataset",
        "BIGQUERY_CREDENTIALS_PATH": str(creds_file),
        "BIGQUERY_MAX_BYTES_PROCESSED": 1000000  # 1MB for testing
    })
    
    return test_settings


@pytest.fixture
def db(monkeypatch, bigquery_settings, mock_credentials, mock_client):
    """Create test database instance."""
    monkeypatch.setattr("app.db.bigquery_database.settings", bigquery_settings)
    return BigQueryDatabase()


def test_init_without_settings(monkeypatch):
    """Test initialization fails when BigQuery is not enabled."""
    test_settings = settings.model_copy(update={"BIGQUERY_ENABLED": False})
    monkeypatch.setattr("app.db.bigquery_database.settings", test_settings)
    with pytest.raises(ValueError, match="BigQuery is not enabled"):
        BigQueryDatabase()


def test_init_missing_project_id(monkeypatch, bigquery_settings):
    """Test initialization fails with missing project ID."""
    test_settings = bigquery_settings.model_copy(update={"BIGQUERY_PROJECT_ID": None})
    monkeypatch.setattr("app.db.bigquery_database.settings", test_settings)
    with pytest.raises(ValueError, match="project ID is required"):
        BigQueryDatabase()


def test_init_missing_dataset(monkeypatch, bigquery_settings):
    """Test initialization fails with missing dataset."""
    test_settings = bigquery_settings.model_copy(update={"BIGQUERY_DATASET": None})
    monkeypatch.setattr("app.db.bigquery_database.settings", test_settings)
    with pytest.raises(ValueError, match="dataset ID is required"):
        BigQueryDatabase()


def test_init_missing_credentials(monkeypatch, bigquery_settings):
    """Test initialization fails with missing credentials."""
    test_settings = bigquery_settings.model_copy(update={"BIGQUERY_CREDENTIALS_PATH": None})
    monkeypatch.setattr("app.db.bigquery_database.settings", test_settings)
    with pytest.raises(ValueError, match="credentials path is required"):
        BigQueryDatabase()


@pytest.mark.asyncio
async def test_execute_query_cost_limit(db, mock_client, bigquery_settings):
    """Test query cost estimation limit."""
    # Mock query job with high bytes processed
    query_job = Mock(spec=QueryJob)
    query_job.total_bytes_processed = bigquery_settings.BIGQUERY_MAX_BYTES_PROCESSED + 1
    mock_client.return_value.query.return_value = query_job
    
    with pytest.raises(QueryCostError):
        await db.execute_query("SELECT * FROM large_table")


@pytest.mark.asyncio
async def test_execute_query_success(db, mock_client, bigquery_settings):
    """Test successful query execution."""
    # Mock query job with acceptable cost
    query_job = Mock(spec=QueryJob)
    query_job.total_bytes_processed = bigquery_settings.BIGQUERY_MAX_BYTES_PROCESSED - 1
    
    # Mock query results
    mock_row = Mock()
    mock_row.items.return_value = [("column1", "value1")]
    mock_results = Mock(spec=RowIterator)
    mock_results.__iter__ = Mock(return_value=iter([mock_row]))
    
    # Setup mock query execution
    mock_client.return_value.query.return_value = query_job
    mock_client.return_value.query.return_value.result.return_value = mock_results
    
    results = await db.execute_query("SELECT * FROM test_table")
    assert len(results) == 1
    assert results[0] == {"column1": "value1"}


def test_test_connection_success(db, mock_client):
    """Test successful connection test."""
    mock_client.return_value.query.return_value.result.return_value = True
    assert db.test_connection() is True


def test_test_connection_failure(db, mock_client):
    """Test failed connection test."""
    mock_client.return_value.query.side_effect = Exception("Connection failed")
    assert db.test_connection() is False


def test_get_table_schema(db, mock_client):
    """Test getting table schema."""
    # Mock table schema
    mock_field = Mock()
    mock_field.name = "event_date"
    mock_field.field_type = "STRING"
    mock_field.mode = "NULLABLE"
    mock_field.description = "Event date"
    
    mock_table = Mock()
    mock_table.schema = [mock_field]
    
    mock_client.return_value.get_table.return_value = mock_table
    
    schema = db.get_table_schema("events")
    assert len(schema["fields"]) == 1
    assert schema["fields"][0]["name"] == "event_date"
    assert schema["fields"][0]["type"] == "STRING"


@pytest.mark.asyncio
async def test_paginated_query(db, mock_client):
    """Test paginated query execution."""
    # Mock first page results
    mock_row1 = Mock()
    mock_row1.items.return_value = [("column1", "value1")]
    mock_page1 = Mock(spec=RowIterator)
    mock_page1.__iter__ = Mock(return_value=iter([mock_row1]))
    mock_page1.next_page_token = "page2"
    
    # Mock second page results
    mock_row2 = Mock()
    mock_row2.items.return_value = [("column1", "value2")]
    mock_page2 = Mock(spec=RowIterator)
    mock_page2.__iter__ = Mock(return_value=iter([mock_row2]))
    mock_page2.next_page_token = None
    
    # Setup mock pagination
    mock_client.return_value.query.return_value.result.side_effect = [
        mock_page1,
        mock_page2
    ]
    
    results = []
    async for page in db.paginated_query("SELECT * FROM test_table", page_size=1):
        results.extend(page)
    
    assert len(results) == 2
    assert results[0] == {"column1": "value1"}
    assert results[1] == {"column1": "value2"}


def test_ga4_schema_integration():
    """Test GA4Schema integration with BigQuery queries."""
    # Test date range condition
    condition = GA4Schema.get_date_range_condition("20240101", "20240131")
    assert "_TABLE_SUFFIX BETWEEN '20240101' AND '20240131'" in condition
    
    # Test custom dimension extraction
    dimension = GA4Schema.extract_custom_dimension("page_type")
    assert "FROM UNNEST(event_params)" in dimension
    assert "key = 'page_type'" in dimension
    
    # Test metrics query composition
    metrics = [
        GA4Schema.METRICS["total_users"],
        GA4Schema.METRICS["total_pageviews"]
    ]
    query = f"""
        SELECT
            {','.join(metrics)}
        FROM `test-project.test_dataset.{GA4Schema.EVENTS_TABLE}`
        WHERE {GA4Schema.get_date_range_condition('20240101', '20240131')}
    """
    assert "COUNT(DISTINCT user_pseudo_id)" in query
    assert "COUNT(CASE WHEN event_name = 'page_view'" in query
