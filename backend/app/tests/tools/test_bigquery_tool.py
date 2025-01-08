"""Tests for BigQuery Tool."""
import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage

from app.core.config import Settings
from app.schemas.agent_schema import AgentAndToolsConfig
from app.schemas.tool_schema import ToolConfig
from app.services.chat_agent.tools.library.bigquery_tool.bigquery_tool import BigQueryTool
from tests.fake.chat_model import FakeMessagesListChatModel


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for testing."""
    test_settings = Settings(
        BIGQUERY_ENABLED=True,
        BIGQUERY_PROJECT_ID="test-project",
        BIGQUERY_DATASET="test-dataset",
        BIGQUERY_CREDENTIALS_PATH="/credentials/orixa-438316-371bcdc57d23.json",
        BIGQUERY_MAX_BYTES_PROCESSED=1000000000
    )
    with patch("app.services.chat_agent.tools.library.bigquery_tool.bigquery_tool.settings", test_settings), \
         patch("app.db.bigquery_database.settings", test_settings):
        yield


@pytest.fixture
def mock_bigquery_database():
    """Mock BigQuery database."""
    mock = AsyncMock()
    mock.execute_query = AsyncMock(return_value=[
        {"users": 100, "sessions": 150},
        {"users": 120, "sessions": 180},
    ])
    with patch("app.db.bigquery_database.BigQueryDatabase", return_value=mock):
        yield mock


@pytest.fixture
def mock_llm():
    """Mock LLM."""
    return FakeMessagesListChatModel(responses=[
        AIMessage(content="user_id, event_name"),  # For fields
        AIMessage(content="```sql\nSELECT * FROM events```"),  # For queries
        AIMessage(content="Valid: yes\nReason: Query returns data"),  # For validation
    ])


@pytest.fixture
def tool_config():
    """Tool configuration."""
    return ToolConfig(
        description="Test BigQuery Tool",
        prompt_message="{{question}}",
        system_context="You are a test system",
        prompt_inputs=[],
    )


@pytest.fixture
def common_config():
    """Common configuration."""
    return AgentAndToolsConfig(
            llm="gpt-4o",
            fast_llm="gpt-4o-mini",
        fast_llm_token_limit=1000,
        max_token_length=2000,
    )


@pytest.fixture
def bigquery_tool(mock_llm, mock_bigquery_database, tool_config, common_config):
    """BigQuery tool instance."""
    tool = BigQueryTool.from_config(
        config=tool_config,
        common_config=common_config,
        llm=mock_llm,
        fast_llm=mock_llm,
    )
    tool.db = mock_bigquery_database
    return tool


@pytest.mark.asyncio
async def test_tool_initialization(bigquery_tool):
    """Test tool initialization."""
    assert bigquery_tool.name == "bigquery_tool"
    assert bigquery_tool.appendix_title == "Analytics Appendix"
    assert bigquery_tool.validate_empty_results is True
    assert bigquery_tool.validate_with_llm is True


@pytest.mark.asyncio
async def test_list_required_fields(bigquery_tool):
    """Test listing required fields."""
    fields = await bigquery_tool._alist_required_fields(
        "Show me events",
        None,
    )
    assert fields == "user_id, event_name"


@pytest.mark.asyncio
async def test_query_execution(bigquery_tool, mock_bigquery_database):
    """Test query execution."""
    # Disable LLM validation for this test
    bigquery_tool.validate_with_llm = False
    
    is_valid, results_str, reason = await bigquery_tool._avalidate_response(
        "Show me events",
        "```sql\nSELECT * FROM events```",
        None,
    )
    assert is_valid is True
    assert mock_bigquery_database.execute_query.called
    assert "total rows: 2" in results_str


@pytest.mark.asyncio
async def test_error_handling(bigquery_tool, mock_bigquery_database):
    """Test error handling."""
    mock_bigquery_database.execute_query.side_effect = Exception("Test error")
    is_valid, results_str, reason = await bigquery_tool._avalidate_response(
        "Show me events",
        "```sql\nSELECT * FROM events```",
        None,
    )
    assert is_valid is False
    assert "Test error" in reason
