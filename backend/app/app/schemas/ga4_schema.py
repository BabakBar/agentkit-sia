from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class GA4Field(BaseModel):
    """GA4 field definition with type and description."""
    name: str
    field_type: str
    mode: str = "NULLABLE"
    description: Optional[str] = None


class GA4EventParameter(BaseModel):
    """GA4 event parameter structure."""
    key: str
    value: Dict[str, str]  # Type can be string_value, int_value, float_value, double_value


class GA4UserProperty(BaseModel):
    """GA4 user property structure."""
    key: str
    value: Dict[str, str]


class GA4Event(BaseModel):
    """GA4 event structure matching BigQuery schema."""
    event_date: str = Field(..., description="The date when the event was logged (YYYYMMDD)")
    event_timestamp: int = Field(..., description="Timestamp when the event was logged (microseconds)")
    event_name: str = Field(..., description="The name of the event")
    event_params: List[GA4EventParameter] = Field(default_factory=list, description="Event parameters")
    user_pseudo_id: str = Field(..., description="Pseudonymous user identifier")
    user_properties: List[GA4UserProperty] = Field(default_factory=list, description="User properties")
    privacy_info: Optional[Dict[str, str]] = Field(None, description="Privacy related information")
    user_first_touch_timestamp: Optional[int] = Field(None, description="Timestamp of first user interaction")
    
    # Common dimensions
    platform: Optional[str] = None
    stream_id: Optional[str] = None
    page_location: Optional[str] = None
    page_title: Optional[str] = None
    source: Optional[str] = None
    medium: Optional[str] = None
    campaign: Optional[str] = None

    class Config:
        """Pydantic config."""
        allow_population_by_field_name = True


class GA4Schema:
    """GA4 schema definitions and utilities."""
    
    # Standard GA4 tables
    EVENTS_TABLE = "events_*"
    EVENTS_INTRADAY_TABLE = "events_intraday_*"
    
    # Common event names
    PAGE_VIEW = "page_view"
    SCROLL = "scroll"
    CLICK = "click"
    USER_ENGAGEMENT = "user_engagement"
    SESSION_START = "session_start"
    
    # Standard metrics calculations
    METRICS = {
        "total_users": """
            COUNT(DISTINCT user_pseudo_id) as total_users
        """,
        "total_sessions": """
            COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(session_id as STRING))) as total_sessions
        """,
        "total_pageviews": """
            COUNT(CASE WHEN event_name = 'page_view' THEN 1 END) as total_pageviews
        """,
        "avg_session_duration": """
            AVG(engagement_time_msec) / 1000 as avg_session_duration_seconds
        """,
    }
    
    # Common dimension extractions
    DIMENSION_EXTRACTORS = {
        "page_path": """
            (SELECT value.string_value 
             FROM UNNEST(event_params) 
             WHERE key = 'page_location') as page_path
        """,
        "session_id": """
            (SELECT value.int_value 
             FROM UNNEST(event_params) 
             WHERE key = 'ga_session_id') as session_id
        """,
        "engagement_time": """
            (SELECT value.int_value 
             FROM UNNEST(event_params) 
             WHERE key = 'engagement_time_msec') as engagement_time_msec
        """,
    }
    
    @staticmethod
    def get_date_range_condition(start_date: str, end_date: str) -> str:
        """Generate date range condition for table suffix."""
        return f"_TABLE_SUFFIX BETWEEN '{start_date}' AND '{end_date}'"
    
    @staticmethod
    def extract_custom_dimension(dimension_name: str) -> str:
        """Generate SQL to extract custom dimension from event_params."""
        return f"""
            (SELECT value.string_value 
             FROM UNNEST(event_params) 
             WHERE key = '{dimension_name}') as {dimension_name}
        """
    
    @staticmethod
    def extract_custom_metric(metric_name: str) -> str:
        """Generate SQL to extract custom metric from event_params."""
        return f"""
            (SELECT value.int_value 
             FROM UNNEST(event_params) 
             WHERE key = '{metric_name}') as {metric_name}
        """
