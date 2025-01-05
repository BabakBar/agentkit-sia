import pytest
from pydantic import ValidationError
from app.core.config import Settings

def test_config_loading():
    """Test basic config loading with Pydantic v2 style"""
    settings = Settings(
        PROJECT_NAME="test",
        OPENAI_API_KEY="test",
        DATABASE_USER="user",
        DATABASE_PASSWORD="pass",
        DATABASE_HOST="localhost",
        DATABASE_PORT=5432,
        DATABASE_NAME="testdb",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        MINIO_ROOT_USER="user",
        MINIO_ROOT_PASSWORD="pass",
        MINIO_URL="localhost",
        MINIO_BUCKET="bucket",
        PDF_TOOL_EXTRACTION_CONFIG_PATH="path",
        AGENT_CONFIG_PATH="path",
        SQL_TOOL_DB_ENABLED=False,
        SQL_TOOL_DB_INFO_PATH="path",
        SQL_TOOL_DB_URI="",
        PDF_TOOL_ENABLED=False,
        PDF_TOOL_DATA_PATH="path",
        PDF_TOOL_DATABASE="db",
        BACKEND_CORS_ORIGINS=["http://localhost"]
    )
    assert settings.API_VERSION == "v1"
    assert settings.API_V1_STR == "/api/v1"
    assert isinstance(settings.SECRET_KEY, str)
    assert len(settings.SECRET_KEY) >= 32
    assert settings.model_config["case_sensitive"] is True

def test_database_uri_assembly():
    """Test database URI assembly with Pydantic v2 validation"""
    settings = Settings(
        PROJECT_NAME="test",
        OPENAI_API_KEY="test",
        DATABASE_USER="user",
        DATABASE_PASSWORD="pass",
        DATABASE_HOST="localhost",
        DATABASE_PORT=5432,
        DATABASE_NAME="testdb",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        MINIO_ROOT_USER="user",
        MINIO_ROOT_PASSWORD="pass",
        MINIO_URL="localhost",
        MINIO_BUCKET="bucket",
        PDF_TOOL_EXTRACTION_CONFIG_PATH="path",
        AGENT_CONFIG_PATH="path",
        SQL_TOOL_DB_ENABLED=False,
        SQL_TOOL_DB_INFO_PATH="path",
        SQL_TOOL_DB_URI="",
        PDF_TOOL_ENABLED=False,
        PDF_TOOL_DATA_PATH="path",
        PDF_TOOL_DATABASE="db",
        BACKEND_CORS_ORIGINS=["http://localhost"]
    )
    assert settings.ASYNC_DATABASE_URI.startswith("postgresql+asyncpg://")
    assert "localhost:5432" in settings.ASYNC_DATABASE_URI
    assert "testdb" in settings.ASYNC_DATABASE_URI

def test_cors_origins_validation():
    """Test CORS origins validation with Pydantic v2"""
    base_settings = {
        "PROJECT_NAME": "test",
        "OPENAI_API_KEY": "test",
        "DATABASE_USER": "user",
        "DATABASE_PASSWORD": "pass",
        "DATABASE_HOST": "localhost",
        "DATABASE_PORT": 5432,
        "DATABASE_NAME": "testdb",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": 6379,
        "MINIO_ROOT_USER": "user",
        "MINIO_ROOT_PASSWORD": "pass",
        "MINIO_URL": "localhost",
        "MINIO_BUCKET": "bucket",
        "PDF_TOOL_EXTRACTION_CONFIG_PATH": "path",
        "AGENT_CONFIG_PATH": "path",
        "SQL_TOOL_DB_ENABLED": False,
        "SQL_TOOL_DB_INFO_PATH": "path",
        "SQL_TOOL_DB_URI": "",
        "PDF_TOOL_ENABLED": False,
        "PDF_TOOL_DATA_PATH": "path",
        "PDF_TOOL_DATABASE": "db"
    }
    
    # Test string input
    settings = Settings(**base_settings, BACKEND_CORS_ORIGINS="http://localhost,https://example.com")
    assert len(settings.BACKEND_CORS_ORIGINS) == 2
    assert "http://localhost" in settings.BACKEND_CORS_ORIGINS
    assert "https://example.com" in settings.BACKEND_CORS_ORIGINS

    # Test list input
    settings = Settings(**base_settings, BACKEND_CORS_ORIGINS=["http://localhost", "https://example.com"])
    assert len(settings.BACKEND_CORS_ORIGINS) == 2

    # Test invalid input
    with pytest.raises(ValidationError):
        Settings(**base_settings, BACKEND_CORS_ORIGINS=123)

def test_required_fields():
    """Test required fields validation with Pydantic v2"""
    with pytest.raises(ValidationError):
        Settings(
            PROJECT_NAME="test",
            DATABASE_USER=None,  # type: ignore
            DATABASE_PASSWORD="pass",
            DATABASE_HOST="localhost",
            DATABASE_PORT=5432,
            DATABASE_NAME="testdb"
        )

def test_pdf_tool_config():
    """Test PDF tool configuration with Pydantic v2"""
    settings = Settings(
        PROJECT_NAME="test",
        OPENAI_API_KEY="test",
        DATABASE_USER="user",
        DATABASE_PASSWORD="pass",
        DATABASE_HOST="localhost",
        DATABASE_PORT=5432,
        DATABASE_NAME="testdb",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        MINIO_ROOT_USER="user",
        MINIO_ROOT_PASSWORD="pass",
        MINIO_URL="localhost",
        MINIO_BUCKET="bucket",
        PDF_TOOL_EXTRACTION_CONFIG_PATH="path",
        AGENT_CONFIG_PATH="path",
        SQL_TOOL_DB_ENABLED=False,
        SQL_TOOL_DB_INFO_PATH="path",
        SQL_TOOL_DB_URI="",
        PDF_TOOL_ENABLED=True,
        PDF_TOOL_DATA_PATH="/data",
        PDF_TOOL_DATABASE="pdfdb",
        BACKEND_CORS_ORIGINS=["http://localhost"]
    )
    assert settings.PDF_TOOL_ENABLED is True
    assert settings.PDF_TOOL_DATA_PATH == "/data"
    assert settings.PDF_TOOL_DATABASE == "pdfdb"

def test_sql_tool_config():
    """Test SQL tool configuration with Pydantic v2"""
    settings = Settings(
        PROJECT_NAME="test",
        OPENAI_API_KEY="test",
        DATABASE_USER="user",
        DATABASE_PASSWORD="pass",
        DATABASE_HOST="localhost",
        DATABASE_PORT=5432,
        DATABASE_NAME="testdb",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        MINIO_ROOT_USER="user",
        MINIO_ROOT_PASSWORD="pass",
        MINIO_URL="localhost",
        MINIO_BUCKET="bucket",
        PDF_TOOL_EXTRACTION_CONFIG_PATH="path",
        AGENT_CONFIG_PATH="path",
        SQL_TOOL_DB_ENABLED=True,
        SQL_TOOL_DB_INFO_PATH="/info",
        SQL_TOOL_DB_URI="postgresql://localhost/test",
        PDF_TOOL_ENABLED=False,
        PDF_TOOL_DATA_PATH="path",
        PDF_TOOL_DATABASE="db",
        BACKEND_CORS_ORIGINS=["http://localhost"]
    )
    assert settings.SQL_TOOL_DB_ENABLED is True
    assert settings.SQL_TOOL_DB_INFO_PATH == "/info"
    assert settings.SQL_TOOL_DB_URI == "postgresql://localhost/test"
