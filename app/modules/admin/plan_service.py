from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.plan_model import Plan
from app.schemas.plan_schema import PlanCreate, PlanUpdate

class PlanService:
    async def get_plan_by_id(self, db: AsyncSession, plan_id: int) -> Plan:
        result = await db.execute(select(Plan).filter(Plan.id == plan_id))
        plan = result.scalars().first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        return plan

    async def create_plan(self, db: AsyncSession, plan_data: PlanCreate) -> Plan:
        # Check if a plan with the same name already exists
        result = await db.execute(select(Plan).filter(Plan.name == plan_data.name))
        existing_plan = result.scalars().first()
        if existing_plan:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Plan with name '{plan_data.name}' already exists."
            )
            
        db_plan = Plan(**plan_data.model_dump())
        db.add(db_plan)
        await db.commit()
        await db.refresh(db_plan)
        return db_plan

    async def update_plan(self, db: AsyncSession, plan_id: int, plan_data: PlanUpdate) -> Plan:
        db_plan = await self.get_plan_by_id(db, plan_id)
        update_data = plan_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_plan, key, value)
        
        await db.commit()
        await db.refresh(db_plan)
        return db_plan

    async def deactivate_plan(self, db: AsyncSession, plan_id: int) -> Plan:
        db_plan = await self.get_plan_by_id(db, plan_id)
        db_plan.is_active = False # Soft delete
        await db.commit()
        await db.refresh(db_plan)
        return db_plan

plan_service = PlanService()
