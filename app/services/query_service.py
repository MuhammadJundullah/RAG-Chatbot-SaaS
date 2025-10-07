from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import sqlparse
from typing import List, Dict, Any, Optional, Set

from app.database.schema import Company
from app.models.schemas import SQLQueryResult
from app import crud
from app.services.connection_manager import external_connection_manager
from app.services.introspection_service import introspection_service
from app.services.gemini_service import gemini_service
from app.utils.security import QueryValidator

class DynamicQueryService:
    def __init__(self):
        self.base_validator = QueryValidator()



    async def process_user_query(
        self, 
        user_query: str, 
        company: Company, 
        db: AsyncSession,
        division_id: Optional[int] = None
    ) -> SQLQueryResult:
        """
        The main orchestration function for the dynamic query process.
        """
        # 1. Check for external DB configuration
        if not company.encrypted_db_connection_string:
            return SQLQueryResult(success=False, error="No external database is configured for this company.")

        # 2. Get the full schema of the external database
        schema_data = await introspection_service.get_schema_for_company(company)
        if schema_data.get("error"):
            return SQLQueryResult(success=False, error=schema_data["error"])

        # Format the schema into a string for the LLM
        full_schema_str = ""
        for table in schema_data.get("schema", []):
            full_schema_str += f"- Table: {table['table_name']}\n"
            for column in table['columns']:
                full_schema_str += f"  - Column: {column}\n"

        # 3. Generate raw SQL query using the LLM
        generated_sql = await gemini_service.generate_raw_sql_query(user_query, full_schema_str)
        if not generated_sql:
            return SQLQueryResult(success=False, error="LLM could not generate a valid SQL query.")

        # 4. Validate the generated SQL
        if not self.base_validator.is_safe_query(generated_sql):
            return SQLQueryResult(success=False, error="Generated SQL is not safe.", query=generated_sql)

        # 5. Execute the query against the external database
        try:
            async with external_connection_manager.get_session(company) as external_session:
                result = await external_session.execute(text(generated_sql))
                data = [dict(row) for row in result.mappings()]
                return SQLQueryResult(success=True, data=data, query=generated_sql)
        except Exception as e:
            return SQLQueryResult(success=False, error=f"Error executing query on external database: {e}", query=generated_sql)

    def format_query_results(self, results: List[Dict]) -> str:
        if not results:
            return "No data found from the database query."
        limited_results = results[:10]
        formatted = "Database query results:\n"
        for i, row in enumerate(limited_results, 1):
            formatted += f"Row {i}: {dict(row)}\n"
        if len(results) > 10:
            formatted += f"... and {len(results) - 10} more rows.\n"
        return formatted

query_service = DynamicQueryService()
