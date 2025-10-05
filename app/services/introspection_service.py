from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import inspect
from app.database.schema import Company
from app.services.connection_manager import external_connection_manager
from typing import Dict, List, Any

class IntrospectionService:
    async def get_schema_for_company(self, company: Company) -> str:
        """
        Connects to a company's external database and introspects its schema.
        Returns a formatted string representation of the schema for the LLM.
        """
        engine = external_connection_manager.get_engine(company)
        if not engine:
            return "No external database configured for this company."

        formatted_schema = f"Schema for external database '{company.name}':\n"
        
        try:
            async with engine.connect() as conn:
                def sync_inspector(sync_conn):
                    return inspect(sync_conn)
                
                inspector = await conn.run_sync(sync_inspector)
                tables = await conn.run_sync(inspector.get_table_names)

                for table_name in tables:
                    formatted_schema += f"- Table: {table_name}\n"
                    columns = await conn.run_sync(inspector.get_columns, table_name)
                    for column in columns:
                        formatted_schema += f"  - Column: {column['name']} (Type: {column['type']})\n"
        except Exception as e:
            return f"Error introspecting schema: {e}"
        
        return formatted_schema

# Singleton instance
introspection_service = IntrospectionService()
