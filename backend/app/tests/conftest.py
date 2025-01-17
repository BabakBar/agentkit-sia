# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.db.bigquery_database import BigQueryDatabase
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from langchain.agents import AgentExecutor
from langchain.base_language import BaseLanguageModel
from langchain.callbacks.manager import AsyncCallbackManagerForToolRun
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.api.deps import get_jwt
from app.api.v1.endpoints.chat import get_meta_agent_with_api_key
from app.deps.agent_deps import set_global_tool_context
from app.main import app
from app.schemas.agent_schema import AgentConfig
from app.schemas.tool_schema import ToolInputSchema
from app.services.chat_agent.meta_agent import create_meta_agent
from app.utils import uuid7
from app.utils.config_loader import get_agent_config
from app.utils.fastapi_globals import g
from tests.fake.chat_model import FakeMessagesListChatModel


def pytest_configure():
    run_id = str(uuid7())
    g.tool_context = {}
    g.query_context = {
        "run_id": run_id,
    }
    
    # Set required environment variables for tests
    import os
    os.environ.update({
        "TESTING": "true",
        "BIGQUERY_ENABLED": "true",
        "BIGQUERY_PROJECT_ID": "orixa-438316",
        "BIGQUERY_DATASET": "analytics_386787868",
        "BIGQUERY_CREDENTIALS_PATH": "/credentials/orixa-438316-371bcdc57d23.json",
        "BIGQUERY_MAX_BYTES_PROCESSED": "1000000000",
        "PROJECT_NAME": "test",
        "OPENAI_API_KEY": "test",
        "DATABASE_USER": "postgres",
        "DATABASE_PASSWORD": "postgres",
        "DATABASE_HOST": "database",
        "DATABASE_PORT": "5432",
        "DATABASE_NAME": "fastapi_db",
        "REDIS_HOST": "redis_server",
        "REDIS_PORT": "6379",
        "MINIO_ROOT_USER": "test",
        "MINIO_ROOT_PASSWORD": "test",
        "MINIO_URL": "test",
        "MINIO_BUCKET": "test",
        "BACKEND_CORS_ORIGINS": '["*"]',
        "PDF_TOOL_EXTRACTION_CONFIG_PATH": "test",
        "AGENT_CONFIG_PATH": "tests/config/agent-test.yml",
        "SQL_TOOL_DB_ENABLED": "false",
        "SQL_TOOL_DB_INFO_PATH": "test",
        "SQL_TOOL_DB_URI": "",
        "PDF_TOOL_ENABLED": "false",
        "PDF_TOOL_DATA_PATH": "test",
        "PDF_TOOL_DATABASE": "test"
    })


@pytest.fixture(autouse=True)
def mock_redis_client_sync():
    with patch(
        "app.services.chat_agent.helpers.run_helper.get_redis_client", new_callable=AsyncMock
    ) as mock_helpers_redis_client:
        mock_helpers_redis_client.get.return_value = "mocked_redis_get_value"
        mock_helpers_redis_client.set.return_value = True

        yield


@pytest.fixture
def messages() -> list:
    return [
        SystemMessage(content="You are a test user."),
        HumanMessage(content="Hello, I am a test user."),
    ]


@pytest.fixture
def llm() -> BaseLanguageModel:
    fake_llm = FakeMessagesListChatModel(responses=[HumanMessage(content=f"{i}") for i in range(100)])
    return fake_llm


@pytest.fixture(autouse=True)
def mock_llm_call(llm: BaseLanguageModel):  # pylint: disable=redefined-outer-name
    with patch("app.services.chat_agent.tools.library.basellm_tool.basellm_tool.get_llm", return_value=llm):
        yield


@pytest.fixture
def tool_input() -> str:
    return ToolInputSchema(
        chat_history=[
            HumanMessage(content="This is a test memory"),
            AIMessage(content="This is the AI message response"),
        ],
        latest_human_message="This is a test message. ",
        intermediate_steps={},
    ).json()


@pytest.fixture
def agent_config() -> AgentConfig:
    return get_agent_config()


@pytest.fixture
def meta_agent(llm: BaseLanguageModel) -> AgentExecutor:  # pylint: disable=redefined-outer-name
    agent_config = get_agent_config()
    return create_meta_agent(
        agent_config=agent_config, get_llm_hook=lambda type, key: llm  # pylint: disable=unused-argument
    )


@pytest.fixture
def test_client(meta_agent: AgentExecutor) -> TestClient:  # pylint: disable=redefined-outer-name
    FastAPICache.init(None, enable=False)

    app.dependency_overrides[set_global_tool_context] = lambda: None
    app.dependency_overrides[get_jwt] = lambda: {}
    app.dependency_overrides[get_meta_agent_with_api_key] = lambda: meta_agent

    return TestClient(app)


@pytest.fixture
def run_manager() -> AsyncCallbackManagerForToolRun:
    return MagicMock(spec=AsyncCallbackManagerForToolRun)


# Integration test fixtures
@pytest.fixture(scope="session")
def real_db():
    """Create test database instance with real credentials."""
    from app.core.config import Settings
    
    # Create test settings with BigQuery enabled
    test_settings = Settings(
        BIGQUERY_ENABLED=True,
        BIGQUERY_PROJECT_ID="orixa-438316",
        BIGQUERY_DATASET="analytics_386787868",
            BIGQUERY_CREDENTIALS_PATH="/credentials/orixa-438316-371bcdc57d23.json",
        BIGQUERY_MAX_BYTES_PROCESSED=1000000000
    )
    
    # Create database instance with test settings
    with patch("app.db.bigquery_database.settings", test_settings):
        db = BigQueryDatabase()
        return db


@pytest.fixture(scope="session")
def test_data_config():
    """Configuration for test data parameters."""
    return {
        "start_date": "20250103",  # Match sample data date
        "end_date": "20250103",    # Match sample data date
        "test_timeout": 30,  # seconds
        "max_pages": 3,
        "page_size": 100
    }
