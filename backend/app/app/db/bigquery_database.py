import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from google.cloud import bigquery
from google.oauth2 import service_account

from app.core.config import settings

# Cost per TB processed by BigQuery
COST_PER_TB = 6.25


class QueryCostError(Exception):
    """Raised when a query would exceed cost limits."""
    pass


class BigQueryDatabase:
    """BigQuery database implementation focusing on GA4 specifics."""
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        pool_size: int = 10
    ):
        """Initialize BigQuery connection with configuration from settings."""
        if not settings.BIGQUERY_ENABLED:
            raise ValueError("BigQuery is not enabled in settings")
            
        self.project_id = project_id or settings.BIGQUERY_PROJECT_ID
        if not self.project_id:
            raise ValueError("BigQuery project ID is required")
            
        self.dataset_id = dataset_id or settings.BIGQUERY_DATASET
        if not self.dataset_id:
            raise ValueError("BigQuery dataset ID is required")
            
        self.credentials_path = credentials_path or settings.BIGQUERY_CREDENTIALS_PATH
        if not self.credentials_path:
            raise ValueError("BigQuery credentials path is required")
        
        # Initialize credentials and client
        self.credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        self._pool = ThreadPoolExecutor(max_workers=pool_size)
        self.client = bigquery.Client(
            project=self.project_id,
            credentials=self.credentials
        )
        self.dataset = self.client.dataset(self.dataset_id)
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute BigQuery query with cost estimation."""
        # Dry run for cost estimation
        job_config = bigquery.QueryJobConfig(dry_run=True)
        query_job = self.client.query(query, job_config=job_config)
        
        # Check if estimated cost is within limits
        if query_job.total_bytes_processed > settings.BIGQUERY_MAX_BYTES_PROCESSED:
            raise QueryCostError(
                f"Query would process {query_job.total_bytes_processed} bytes"
            )
        
        # Execute actual query
        future = self._pool.submit(self._execute_query_sync, query, params)
        results = await asyncio.wrap_future(future)
        return [dict(row.items()) for row in results]
    
    def _execute_query_sync(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> bigquery.table.RowIterator:
        """Synchronous query execution with parameterization."""
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(k, "STRING", v)
                for k, v in (params or {}).items()
            ]
        )
        return self.client.query(query, job_config=job_config).result()
    
    def test_connection(self) -> bool:
        """Test the BigQuery connection."""
        try:
            # Simple query to test connection
            query = "SELECT 1"
            self.client.query(query).result()
            return True
        except Exception:
            return False
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a specific table."""
        table = self.client.get_table(f"{self.project_id}.{self.dataset_id}.{table_name}")
        return {
            "fields": [
                {
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description
                }
                for field in table.schema
            ]
        }
    
    async def paginated_query(
        self,
        query: str,
        page_size: int = 1000,
        max_pages: Optional[int] = None
    ):
        """Execute a query with pagination."""
        query_job = self.client.query(query)
        page_token = None
        page_count = 0
        
        while True:
            page = query_job.result(
                page_size=page_size,
                page_token=page_token
            )
            yield [dict(row.items()) for row in page]
            
            page_token = page.next_page_token
            if not page_token or (max_pages and page_count >= max_pages):
                break
            page_count += 1
    
    def close(self):
        """Clean up resources."""
        if self._pool:
            self._pool.shutdown(wait=True)
