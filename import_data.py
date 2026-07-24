"""Import KH07 data from existing Django SQLite database into FastAPI SQLAlchemy."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from app.database import engine, async_session, Base
from app.models import Member, ContributionCause, Contribution
from sqlalchemy import text


async def import_from_django(django_db_path: str):
    """Import data from the Django project's SQLite database."""
    django_db_path = Path(django_db_path)
    if not django_db_path.exists():
        print(f"Error: Django database not found at {django_db_path}")
        return

    print(f"Importing from: {django_db_path}")

    # Create all tables in the new database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Connect to Django's database
    import aiosqlite
    d_conn = await aiosqlite.connect(str(django_db_path))
    d_conn.row_factory = aiosqlite.Row

    # Import members
    print("\nImporting members...")
    django_members = await d_conn.execute_fetchall(
        "SELECT member_number, name, phone_number, is_active FROM welfare_member ORDER BY member_number"
    )
    member_map = {}  # Django member_number → new id
    
    async with async_session() as session:
        for row in django_members:
            m = Member(
                member_number=row[0],
                name=row[1].strip() if row[1] else "Unknown",
                phone_number=row[2] or "",
                is_active=bool(row[3]),
            )
            session.add(m)
            await session.flush()
            member_map[row[0]] = m.id
        await session.commit()
    print(f"  Imported {len(django_members)} members")

    # Import causes
    print("\nImporting causes...")
    django_causes = await d_conn.execute_fetchall(
        "SELECT id, name, target_amount, date_occurred FROM welfare_contributioncause ORDER BY id"
    )
    cause_map = {}  # Django cause id → new id
    
    async with async_session() as session:
        for row in django_causes:
            c_name = row[1].strip() if row[1] else "Unknown"
            c = ContributionCause(
                name=c_name,
                target_amount=float(row[2]) if row[2] else None,
                date_occurred=row[3],
            )
            session.add(c)
            await session.flush()
            cause_map[row[0]] = c.id
        await session.commit()
    print(f"  Imported {len(django_causes)} causes")

    # Import contributions in bulk
    print("\nImporting contributions...")
    django_contribs = await d_conn.execute_fetchall(
        "SELECT member_id, cause_id, amount, date_paid, notes FROM welfare_contribution ORDER BY date_paid"
    )
    
    from datetime import date as date_cls
    contribs_to_insert = []
    errors = 0
    
    for row in django_contribs:
        django_member_id = row[0]
        django_cause_id = row[1]
        
        if django_member_id not in member_map:
            errors += 1
            continue
        if django_cause_id not in cause_map:
            errors += 1
            continue
        
        # Get original member_number
        mrow = await d_conn.execute_fetchall(
            f"SELECT member_number FROM welfare_member WHERE id = {django_member_id}"
        )
        if not mrow:
            errors += 1
            continue
        original_number = mrow[0][0]
        
        # Parse date
        dp_val = row[3]
        if isinstance(dp_val, str):
            dp = date_cls.fromisoformat(dp_val)
        elif dp_val is None:
            dp = date_cls.today()
        else:
            dp = dp_val
        
        contribs_to_insert.append({
            "member_id": member_map[original_number],
            "cause_id": cause_map[django_cause_id],
            "amount": float(row[2]) if row[2] else 0,
            "date_paid": dp,
            "notes": row[4] or "",
        })
    
    # Bulk insert
    async with async_session() as session:
        session.add_all([Contribution(**c) for c in contribs_to_insert])
        await session.commit()
    
    print(f"  Imported {len(contribs_to_insert)} contributions ({errors} errors)")
    
    await d_conn.close()
    
    # Summary
    async with async_session() as session:
        from sqlalchemy import func
        total = (await session.execute(
            select(func.coalesce(func.sum(Contribution.amount), 0))
        )).scalar()
        print(f"\n=== Import Summary ===")
        print(f"  Members: {len(django_members)}")
        print(f"  Causes: {len(django_causes)}")
        print(f"  Contributions: {len(contribs_to_insert)}")
        print(f"  Total: KES {float(total):,.0f}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python import_data.py <path-to-django-db.sqlite3>")
        sys.exit(1)
    
    from sqlalchemy import select
    asyncio.run(import_from_django(sys.argv[1]))
