"""BigQuery Tool for GA4 Analytics."""
from __future__ import annotations

import logging
from typing import Any, Optional

from langchain.callbacks.manager import AsyncCallbackManagerForToolRun
from langchain.schema import HumanMessage, SystemMessage

from app.core.config import settings
from app.db.bigquery_database import BigQueryDatabase
from app.schemas.agent_schema import AgentAndToolsConfig
from app.schemas.streaming_schema import StreamingDataTypeEnum
from app.schemas.tool_schema import ToolConfig, ToolInputSchema
from app.services.chat_agent.helpers.llm import get_llm
from app.services.chat_agent.tools.ExtendedBaseTool import ExtendedBaseTool

logger = logging.getLogger(__name__)



from pydantic.v1 import Extra

class BigQueryTool(ExtendedBaseTool):
    """GA4 Analytics Tool using BigQuery."""

    name: str = "bigquery_tool"
    appendix_title: str = "Analytics Appendix"

    class Config:
        """Pydantic config."""
        extra = Extra.allow

    # Configuration
    nb_example_rows: int = 3
    validate_empty_results: bool = True
    validate_with_llm: bool = True
    always_limit_query: bool = False
    max_bytes_processed: Optional[int] = None
    db: Optional[BigQueryDatabase] = None

    def __init__(self, **kwargs: Any):
        """Initialize BigQuery tool."""
        super().__init__(**kwargs)
        self.db = BigQueryDatabase()

    @classmethod
    def from_config(
        cls,
        config: ToolConfig,
        common_config: AgentAndToolsConfig,
        **kwargs: Any,
    ) -> BigQueryTool:
        """Create tool from config."""
        llm = kwargs.get("llm", get_llm(common_config.llm))
        fast_llm = kwargs.get("fast_llm", get_llm(common_config.fast_llm))
        fast_llm_token_limit = kwargs.get(
            "fast_llm_token_limit",
            common_config.fast_llm_token_limit,
        )

        if not settings.BIGQUERY_ENABLED:
            raise ValueError("BigQuery is not enabled in settings")

        return cls(
            llm=llm,
            fast_llm=fast_llm,
            fast_llm_token_limit=fast_llm_token_limit,
            description=config.description.format(**{e.name: e.content for e in config.prompt_inputs}),
            prompt_message=config.prompt_message.format(**{e.name: e.content for e in config.prompt_inputs}),
            system_context=config.system_context.format(**{e.name: e.content for e in config.prompt_inputs}),
            prompt_selection=config.prompt_selection.format(**{e.name: e.content for e in config.prompt_inputs})
            if config.prompt_selection
            else None,
            system_context_selection=config.system_context_selection.format(**{e.name: e.content for e in config.prompt_inputs})
            if config.system_context_selection
            else None,
            prompt_validation=config.prompt_validation.format(**{e.name: e.content for e in config.prompt_inputs})
            if config.prompt_validation
            else None,
            system_context_validation=config.system_context_validation.format(**{e.name: e.content for e in config.prompt_inputs})
            if config.system_context_validation
            else None,
            prompt_refinement=config.prompt_refinement.format(**{e.name: e.content for e in config.prompt_inputs})
            if config.prompt_refinement
            else None,
        )

    def _run(
        self,
        *args: Any,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> str:
        """Synchronous execution not supported."""
        raise NotImplementedError("Tool does not support sync")

    async def _arun(
        self,
        *args: Any,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> str:
        """Execute GA4 analytics query."""
        query = kwargs.get("query", args[0])
        query = ToolInputSchema.parse_raw(query)

        try:
            # Get required fields
            fields = await self._alist_required_fields(
                query.latest_human_message,
                run_manager,
            )

            # Generate and validate query
            query_response = await self._agenerate_query(
                query.latest_human_message,
                fields,
                run_manager,
            )

            result: str | None = None
            retries: int = 0
            is_valid = False

            while result is None and retries <= 3:
                is_valid, results_str, complaints = await self._avalidate_response(
                    query.latest_human_message,
                    query_response,
                    run_manager,
                )

                if is_valid:
                    result = query_response
                else:
                    query_response = await self._aimprove_query(
                        query.latest_human_message,
                        query_response,
                        complaints,
                        fields,
                        run_manager,
                    )
                    retries += 1

            if run_manager is not None:
                if is_valid:
                    await run_manager.on_text(
                        result,
                        data_type=StreamingDataTypeEnum.APPENDIX,
                        tool=self.name,
                        step=1,
                        title=self.appendix_title,
                    )
                    return self._construct_final_response(query_response, results_str)
                await run_manager.on_text(
                    "no_data",
                    data_type=StreamingDataTypeEnum.ACTION,
                    tool=self.name,
                    step=1,
                    result=result,
                )
            return result or "no_data"

        except Exception as e:
            if run_manager is not None:
                await run_manager.on_tool_error(e, tool=self.name)
                return repr(e)
            raise e

    async def _alist_required_fields(
        self,
        question: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """List required GA4 fields for query."""
        if run_manager is not None:
            await run_manager.on_text(
                "list_fields",
                data_type=StreamingDataTypeEnum.ACTION,
                tool=self.name,
                step=1,
            )

        messages = [
            SystemMessage(content=self.system_context_selection or ""),
            HumanMessage(content=self.prompt_selection.format(question=question) if self.prompt_selection else ""),
        ]

        response = await self._agenerate_response(messages, discard_fast_llm=True)
        fields = [x.strip() for x in response.split(",")]
        logger.info(f"Required fields: {fields}")
        return ", ".join(fields)

    async def _agenerate_query(
        self,
        question: str,
        fields: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Generate BigQuery SQL from question."""
        if run_manager is not None:
            await run_manager.on_text(
                "generate_query",
                data_type=StreamingDataTypeEnum.ACTION,
                tool=self.name,
                step=1,
            )

        messages = [
            SystemMessage(content=self.system_context),
            HumanMessage(
                content=self.prompt_message.format(
                    ga4_schema=fields,
                    question=question,
                )
            ),
        ]

        response = await self._agenerate_response(messages, discard_fast_llm=True)
        return response

    async def _avalidate_response(
        self,
        question: str,
        response: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> tuple[bool, str, str]:
        """Validate query and results."""
        try:
            # Extract query
            query_start = response.find("```sql") + 6
            query_end = response.find("```", query_start)
            if query_start == -1 or query_end == -1:
                return False, "", "Could not parse SQL query from response"
            
            query = response[query_start:query_end].strip()

            # Execute query
            results = await self.db.execute_query(query)
            if not results:
                return False, "", "Query returned no results"

            if self.validate_empty_results and len(results) == 0:
                return False, "", "Query executed but returned no rows"

            # Format results
            sample_rows = results[:self.nb_example_rows]
            results_str = f"total rows: {len(results)}, first {len(sample_rows)} rows: {sample_rows}"

            # Validate with LLM if configured
            if self.validate_with_llm:
                messages = [
                    SystemMessage(content=self.system_context_validation or ""),
                    HumanMessage(
                        content=self.prompt_validation.format(
                            query=response,
                            result=results_str,
                            question=question,
                        ) if self.prompt_validation else ""
                    ),
                ]
                validation_response = await self._agenerate_response(messages)
                return await self._parse_validation(validation_response)

            return True, results_str, ""

        except Exception as e:
            if run_manager is not None:
                await run_manager.on_tool_error(e, tool=self.name)
            return False, "", str(e)

    async def _aimprove_query(
        self,
        question: str,
        previous_query: str,
        feedback: str,
        fields: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Improve query based on feedback."""
        if run_manager is not None:
            await run_manager.on_text(
                "improve_query",
                data_type=StreamingDataTypeEnum.ACTION,
                tool=self.name,
                step=1,
            )

        messages = [
            SystemMessage(content=self.system_context),
            HumanMessage(
                content=self.prompt_refinement.format(
                    ga4_schema=fields,
                    question=question,
                    previous_query=previous_query,
                    feedback=feedback,
                ) if self.prompt_refinement else ""
            ),
        ]

        return await self._agenerate_response(messages)

    @staticmethod
    async def _parse_validation(response: str) -> tuple[bool, str, str]:
        """Parse validation response."""
        lines = response.strip().split("\n")
        is_valid = False
        reason = ""

        for line in lines:
            if line.startswith("Valid:"):
                is_valid = "yes" in line.lower()
            elif line.startswith("Reason:"):
                reason = line.replace("Reason:", "").strip()

        return is_valid, "", reason

    @staticmethod
    def _construct_final_response(query_response: str, results_str: str) -> str:
        """Format final response with query and results."""
        return f"{query_response}\n\nResults: {results_str}"
