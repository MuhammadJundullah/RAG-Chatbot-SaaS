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

    def _filter_schema_by_permissions(self, schema_str: str, permissions: list) -> tuple[str, set]:
        """Filters the full schema string based on division permissions."""
        if not permissions:
            return "No tables are accessible for this division.", set()

        allowed_tables = {p.table_name for p in permissions}
        allowed_cols_map = {p.table_name: p.allowed_columns.split(',') for p in permissions}
        
        permitted_schema_lines = []
        full_schema_lines = schema_str.split('\n')
        current_table = None

        for line in full_schema_lines:
            if line.startswith("- Table:"):
                table_name = line.split(":")[1].strip()
                if table_name in allowed_tables:
                    current_table = table_name
                    permitted_schema_lines.append(line)
                else:
                    current_table = None
            elif current_table and line.strip().startswith("- Column:"):
                column_name = line.split(":")[1].strip().split(" ")[0]
                allowed_cols = allowed_cols_map.get(current_table, [])
                if "*" in allowed_cols or column_name in allowed_cols:
                    permitted_schema_lines.append(line)
        
        return "\n".join(permitted_schema_lines), allowed_tables

    def _validate_generated_sql(self, sql: str, allowed_tables: Set[str]) -> bool:
        """Validates the LLM-generated SQL for safety and permissions."""
        if not self.base_validator.is_safe_query(sql):
            return False

        try:
            parsed = sqlparse.parse(sql)[0]
            for token in parsed.tokens:
                # Check if the token is an identifier (like a table name)
                if isinstance(token, sqlparse.sql.Identifier):
                    # sqlparse can return identifiers with quotes, e.g., `"my_table"`
                    table_name = token.get_real_name()
                    if table_name not in allowed_tables:
                        print(f"Validation failed: SQL attempts to access non-allowed table '{table_name}'.")
                        return False
        except Exception as e:
            print(f"Error parsing generated SQL: {e}")
            return False
        
        return True

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

        # 2. Get permissions for the division
        permissions = await crud.get_permissions_for_division(db, division_id=division_id) if division_id else []
        if not permissions:
            return SQLQueryResult(success=False, error="This division has no data access permissions.")

        # 3. Get the full schema of the external database
        full_schema_str = await introspection_service.get_schema_for_company(company)
        if full_schema_str.startswith("Error"):
            return SQLQueryResult(success=False, error=full_schema_str)

        # 4. Filter the schema based on permissions
        permitted_schema, allowed_tables = self._filter_schema_by_permissions(full_schema_str, permissions)
        if not permitted_schema or not allowed_tables:
            return SQLQueryResult(success=False, error="Schema is empty or no tables are accessible.")

        # 5. Generate raw SQL query using the LLM
        generated_sql = await gemini_service.generate_raw_sql_query(user_query, permitted_schema)
        if not generated_sql:
            return SQLQueryResult(success=False, error="LLM could not generate a valid SQL query.")

        # 6. Validate the generated SQL
        if not self._validate_generated_sql(generated_sql, allowed_tables):
            return SQLQueryResult(success=False, error="Generated SQL is not safe or violates permissions.", query=generated_sql)

        # 7. Execute the query against the external database
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
