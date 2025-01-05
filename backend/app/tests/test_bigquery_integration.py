import time
import pytest
from google.cloud import bigquery
from app.core.config import settings
from app.schemas.ga4_schema import GA4Schema

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
class TestBigQueryIntegration:
    """Real connection tests for BigQuery integration."""
    
    async def test_real_connection(self, real_db):
        """Test actual connection to BigQuery."""
        assert real_db.test_connection() is True
        
    async def test_basic_event_query(self, real_db, test_data_config):
        """Test querying basic event data."""
        # Use date from sample data
        query = f"""
            SELECT event_name, COUNT(*) as count
            FROM `{real_db.dataset}.{GA4Schema.EVENTS_TABLE}`
            WHERE _TABLE_SUFFIX = '20250103'
            GROUP BY event_name
            LIMIT 5
        """
        results = await real_db.execute_query(query)
        assert len(results) > 0
        assert "event_name" in results[0]
        assert "count" in results[0]

    async def test_table_schema_validation(self, real_db):
        """Test retrieving and validating actual table schema."""
        schema = real_db.get_table_schema(GA4Schema.EVENTS_TABLE)
        required_fields = ["event_date", "event_timestamp", "event_name"]
        for field in required_fields:
            assert any(f["name"] == field for f in schema["fields"])

    async def test_query_performance(self, real_db, test_data_config):
        """Test query performance with real data."""
        start_time = time.time()
        query = f"""
            SELECT 
                COUNT(DISTINCT user_pseudo_id) as total_users,
                COUNT(CASE WHEN event_name = 'page_view' THEN 1 END) as total_pageviews,
                COUNT(CASE WHEN event_name = 'session_start' THEN 1 END) as total_sessions
            FROM `{real_db.dataset}.{GA4Schema.EVENTS_TABLE}`
            WHERE _TABLE_SUFFIX = '20250103'
        """
        results = await real_db.execute_query(query)
        execution_time = time.time() - start_time
        assert execution_time < test_data_config['test_timeout']
        assert "total_users" in results[0]
        assert "total_pageviews" in results[0]

    async def test_real_pagination(self, real_db, test_data_config):
        """Test pagination with actual data."""
        query = f"""
            SELECT event_date, event_name
            FROM `{real_db.dataset}.{GA4Schema.EVENTS_TABLE}`
            WHERE _TABLE_SUFFIX = '20250103'
            ORDER BY event_timestamp DESC
        """
        page_count = 0
        total_rows = 0
        async for page in real_db.paginated_query(query, page_size=test_data_config['page_size']):
            page_count += 1
            total_rows += len(page)
            if page_count >= test_data_config['max_pages']:
                break
        assert page_count > 0
        assert total_rows > 0

    async def test_invalid_query_handling(self, real_db):
        """Test handling of invalid queries."""
        with pytest.raises(Exception):
            await real_db.execute_query("SELECT * FROM nonexistent_table")

    async def test_cost_estimation(self, real_db):
        """Test that we can get query cost estimates."""
        query = f"""
            SELECT event_name 
            FROM `{real_db.dataset}.{GA4Schema.EVENTS_TABLE}`
            WHERE _TABLE_SUFFIX = '20250103'
        """
        
        # Get cost estimate using dry run
        job = real_db.client.query(query, job_config=bigquery.QueryJobConfig(dry_run=True))
        
        # Verify we can get byte count and it's reasonable
        assert job.total_bytes_processed > 0
        assert job.total_bytes_processed < settings.BIGQUERY_MAX_BYTES_PROCESSED
