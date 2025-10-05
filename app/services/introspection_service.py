from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import inspect
from app.database.schema import Company
from app.services.connection_manager import external_connection_manager
from typing import Dict, List, Any

class IntrospectionService:
    async def get_schema_for_company(self, company: Company) -> Dict[str, Any]:
        """
        Connects to a company's external database and introspects its schema.
        Returns a structured dictionary representation of the schema.
        """
        engine = external_connection_manager.get_engine(company)
        if not engine:
            return {"error": "No external database configured for this company."}

        schema_data = []
        
        try:
            async with engine.connect() as conn:
                def sync_inspector(sync_conn):
                    return inspect(sync_conn)
                
                inspector = await conn.run_sync(sync_inspector)
                
                # Correctly pass arguments within run_sync using a lambda
                tables = await conn.run_sync(lambda sync_conn: inspector.get_table_names(schema="public"))

                for table_name in tables:
                    # Correctly pass arguments within run_sync using a lambda
                    columns = await conn.run_sync(lambda sync_conn: inspector.get_columns(table_name, schema="public"))
                    column_names = [col['name'] for col in columns]
                    schema_data.append({"table_name": table_name, "columns": column_names})
        except Exception as e:
            return {"error": f"Error introspecting schema: {e}"}
        
        return {"schema": schema_data}

# Singleton instance
introspection_service = IntrospectionService()
