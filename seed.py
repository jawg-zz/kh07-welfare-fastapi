"""Seed the database with initial data.
Run at Docker build time to ensure deployed images have data.
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session, engine, Base
from app.models import Member, ContributionCause, Contribution
from sqlalchemy import select, func
from datetime import date
import random

SEED_DATA = {
    "causes": [
        {"name": "Late Father of Abel Mokua"},
        {"name": "Late Mother of Oscar Odwar"},
        {"name": "Late Mother of Aineah Nyabuga"},
    ],
    "members": [
        "Onesmus Misesi", "Samwel Maende", "Vincent Achila", "Victor Bosire",
        "Abel Abuga", "James Maencha", "Peter Mbeche", "Isaiah Anyona",
        "Peter Ateka", "Paul Ombongi", "Philip Manyega", "Arnold Nyandiko",
        "John Mogire", "Obwogo Monayo", "Abner Nyaberi", "Shalton Ocharo",
        "Ndocha Mugoya", "Victor Mayaka", "Job Momanyi", "Allan Mogere",
        "Edward Maisiba", "Samson Areri", "Dennis Abaya", "Gibson Monari",
        "Evans Adino", "Edwin Otiyo", "Eric Maneno", "Dennis Moinde",
        "Jonathan Bosire", "Erick Okola", "Albert Ayiecha", "Dennis Ogeto",
        "Dennis Nick Moseti", "Felix Ogwangi", "Edwin Misati", "Francis Mochache",
        "Moffat Kibagendi", "Enock Okibo", "Henry Oibi", "Hollines Onyiego",
        "Aineah Nyabuga", "Franklin Mwamba", "Fred Osoro", "Kevin Masira",
        "Kevin Kenyoru", "Hamson Nyabera", "Japhet Ongeri", "Jeff Orenge",
        "Crispus Momanyi", "John Otenyo", "Felix Maranga", "Dennis Okemwa",
        "Gibson Omanga", "Boniface Nyangau", "Wilfred Misente", "Ariel Ayieko",
        "Andrew Ondimu", "Nelson Nyakundi", "Noah Mecha", "Dave Onsombi",
        "Justine Nyarige", "Marvin Omenda", "Edwin Machuki", "Edwin Nyamosi",
        "Davis Ogari", "Geoffrey Maisiba", "Vincent Mogire", "Joshua Kamsingi",
        "Thomas Omenta", "Hosea Moturi", "James Matundura", "Zachary Makini",
        "Douglass Kengere", "Finley Asuma", "Amos Akes", "Cyrus Mauti",
        "Samwel Mokaya", "Douglas Ogamba", "Clifford Keya", "Wilson Moruri",
        "Justus Monari", "Richard Kibagendi", "Kelvin Somoni", "Justine Ochwangi",
        "Edgar Ongeri", "Sammy Ratemo", "Wycliffe Mageto", "Edwin Mogusu",
        "Bee Asuma", "Titus Nyakundi", "Gideon Osano", "Bob Obebo",
        "Joshua Gwaro", "Wambura Marwa", "Joel Tora", "Peter Oketch",
        "Alex Mosiere", "Clive Maikuri", "Seth Osoro", "Alex Mosioma",
        "Heri Nyanchoga", "Mzanzibari", "Jonathan Gwaro", "Enoch Oyioka",
        "Nathan Omurwa", "Lamech Misati", "Elvis Otieno", "Innocent Motanya",
        "Gregory Momanyi", "Dominic Magabi", "Abel Mokaya", "Enock Brown",
        "Emmanuel Moseti", "Japheth Nyangau", "Geoffrey Anari", "Edwin Ayora",
        "Peter Ateka", "Dennis Arasa", "Micah Nyamongo", "Albert Ombongi",
        "Newton Onsongo", "Oscar Adwar", "Abner Michieka", "David Mooncha",
        "Wilfred Magoma", "Desmond Orucho", "Mochama Nyasoko", "Jared Nyaberi",
        "Justus Onywere", "Brian Onsomu", "Areri Ongeri", "Vincent Otara",
        "Brian Soita", "Charles Ogechi", "Erick Manduku", "Ongwae Ondari",
        "Collins Mekubo", "Kepha Samson", "Peter Onkendi", "Kevin Momanyi",
        "Stanley Nyangena", "Polycap Nyaribo", "Ezra Mogire", "Robin Nyakundi",
        "Edwin Onguti", "Joash Mbegera", "Jonathan Momanyi",
    ],
    # (member_index, cause_index, amount)
    "contributions": [
        (0,0,500),(0,1,1000),(0,2,1000),(1,0,500),(1,1,1500),(1,2,0),
        (2,0,500),(2,1,500),(2,2,0),(3,0,1000),(3,1,1000),(3,2,1000),
        (4,0,0),(4,1,1000),(4,2,500),(5,0,500),(5,1,500),(5,2,500),
        (6,0,500),(6,1,500),(6,2,500),(7,0,1200),(7,1,3000),(7,2,1200),
        (8,0,500),(8,1,1000),(8,2,500),(9,0,500),(9,1,500),(9,2,500),
        (10,0,0),(10,1,1000),(10,2,500),(11,0,500),(11,1,500),(11,2,500),
        (12,0,500),(12,1,1000),(12,2,500),(13,0,0),(13,1,500),(13,2,0),
        (14,0,500),(14,1,500),(14,2,500),(15,0,500),(15,1,1000),(15,2,500),
        (16,0,500),(16,1,500),(16,2,500),(17,0,1000),(17,1,500),(17,2,500),
        (18,0,500),(18,1,500),(18,2,500),(19,0,2000),(19,1,1000),(19,2,1000),
        (20,0,500),(20,1,500),(20,2,1000),(21,0,1000),(21,1,1000),(21,2,1500),
        (22,0,500),(22,1,500),(22,2,500),(23,0,500),(23,1,500),(23,2,500),
        (24,0,500),(24,1,500),(24,2,500),(25,0,500),(25,1,500),(25,2,500),
        (26,0,0),(26,1,500),(26,2,500),(27,0,500),(27,1,500),(27,2,0),
        (28,0,500),(28,1,500),(28,2,0),(29,0,500),(29,1,500),(29,2,0),
        (30,0,500),(30,1,500),(30,2,500),(31,0,1000),(31,1,1000),(31,2,500),
        (32,0,500),(32,1,500),(32,2,500),(33,0,0),(33,1,500),(33,2,500),
        (34,0,500),(34,1,500),(34,2,500),(35,0,500),(35,1,500),(35,2,0),
        (36,0,500),(36,1,500),(36,2,500),(37,0,500),(37,1,500),(37,2,500),
        (38,0,500),(38,1,500),(38,2,500),(39,0,1000),(39,1,500),(39,2,500),
        (40,0,500),(40,1,500),(40,2,500),(41,0,500),(41,1,500),(41,2,0),
        (42,0,500),(42,1,500),(42,2,0),(43,0,500),(43,1,500),(43,2,500),
        (44,0,0),(44,1,500),(44,2,0),(45,0,500),(45,1,500),(45,2,500),
        (46,0,0),(46,1,500),(46,2,500),(47,0,1000),(47,1,1000),(47,2,1000),
        (48,0,500),(48,1,1000),(48,2,500),(49,0,0),(49,1,500),(49,2,500),
        (50,0,500),(50,1,500),(50,2,500),(51,0,500),(51,1,500),(51,2,500),
        (52,0,500),(52,1,500),(52,2,500),(53,0,500),(53,1,500),(53,2,500),
        (54,0,500),(54,1,600),(54,2,600),(55,0,500),(55,1,1000),(55,2,1000),
        (56,0,500),(56,1,500),(56,2,500),(57,0,500),(57,1,500),(57,2,1000),
        (58,0,1000),(58,1,500),(58,2,500),(59,0,500),(59,1,500),(59,2,500),
        (60,0,500),(60,1,500),(60,2,500),(61,0,500),(61,1,500),(61,2,500),
        (62,0,500),(62,1,500),(62,2,500),(63,0,500),(63,1,500),(63,2,500),
        (64,0,2000),(64,1,1000),(64,2,1000),(65,0,500),(65,1,500),(65,2,500),
        (66,0,500),(66,1,500),(66,2,500),(67,0,1000),(67,1,1000),(67,2,1500),
        (68,0,1000),(68,1,1000),(68,2,1000),(69,0,0),(69,1,500),(69,2,0),
        (70,0,2000),(70,1,1200),(70,2,1200),(71,0,500),(71,1,500),(71,2,500),
        (72,0,500),(72,1,500),(72,2,500),(73,0,1000),(73,1,1000),(73,2,1000),
        (74,0,500),(74,1,500),(74,2,0),(75,0,500),(75,1,500),(75,2,500),
        (76,0,500),(76,1,500),(76,2,0),(77,0,500),(77,1,500),(77,2,0),
        (78,0,500),(78,1,500),(78,2,0),(79,0,500),(79,1,500),(79,2,500),
        (80,0,0),(80,1,500),(80,2,0),(81,0,0),(81,1,500),(81,2,0),
        (82,0,500),(82,1,1000),(82,2,0),(83,0,500),(83,1,500),(83,2,500),
        (84,0,500),(84,1,500),(84,2,0),(85,0,0),(85,1,500),(85,2,500),
        (86,0,2000),(86,1,1500),(86,2,1500),(87,0,0),(87,1,500),(87,2,0),
        (88,0,500),(88,1,500),(88,2,500),(89,0,500),(89,1,500),(89,2,500),
        (90,0,0),(90,1,500),(90,2,0),(91,0,500),(91,1,500),(91,2,500),
        (92,0,1000),(92,1,1000),(92,2,1000),(93,0,0),(93,1,500),(93,2,0),
        (94,0,1000),(94,1,1000),(94,2,0),(95,0,0),(95,1,700),(95,2,0),
        (96,0,0),(96,1,500),(96,2,500),(97,0,0),(97,1,500),(97,2,500),
        (98,0,0),(98,1,500),(98,2,500),(99,0,500),(99,1,500),(99,2,500),
        (100,0,500),(100,1,500),(100,2,0),(101,0,0),(101,1,1000),(101,2,1000),
        (102,0,500),(102,1,500),(102,2,0),(103,0,0),(103,1,500),(103,2,500),
        (104,0,500),(104,1,500),(104,2,500),(105,0,0),(105,1,500),(105,2,500),
        (106,0,0),(106,1,200),(106,2,500),(107,0,500),(107,1,1000),(107,2,1000),
        (108,0,0),(108,1,500),(108,2,500),(109,0,1000),(109,1,1000),(109,2,1000),
        (110,0,500),(110,1,300),(110,2,300),(111,0,500),(111,1,500),(111,2,500),
        (112,0,0),(112,1,500),(112,2,500),(113,0,0),(113,1,0),(113,2,500),
        (114,0,0),(114,1,0),(114,2,500),(115,0,500),(115,1,0),(115,2,500),
        (116,0,500),(116,1,500),(116,2,500),(117,0,500),(117,1,1000),(117,2,1000),
        (118,0,0),(118,1,0),(118,2,500),(119,0,0),(119,1,0),(119,2,500),
        (120,0,0),(120,1,500),(120,2,500),(121,0,0),(121,1,0),(121,2,500),
        (122,0,0),(122,1,0),(122,2,1000),(123,0,500),(123,1,0),(123,2,500),
        (124,0,0),(124,1,0),(124,2,500),(125,0,500),(125,1,0),(125,2,500),
        (126,0,0),(126,1,0),(126,2,500),(127,0,1000),(127,1,0),(127,2,500),
        (128,0,1000),(128,1,0),(128,2,0),(129,0,500),(129,1,0),(129,2,0),
        (130,0,500),(130,1,0),(130,2,0),(131,0,500),(131,1,0),(131,2,0),
        (132,0,1000),(132,1,0),(132,2,0),(133,0,1000),(133,1,0),(133,2,0),
        (134,0,500),(134,1,0),(134,2,0),(135,0,500),(135,1,0),(135,2,0),
        (136,0,500),(136,1,0),(136,2,0),(137,0,500),(137,1,0),(137,2,0),
        (138,0,500),(138,1,0),(138,2,0),(139,0,500),(139,1,0),(139,2,0),
        (140,0,500),(140,1,0),(140,2,0),(141,0,1000),(141,1,0),(141,2,0),
        (142,0,500),(142,1,0),(142,2,0),(143,0,500),(143,1,0),(143,2,0),
        (144,0,500),(144,1,0),(144,2,0),(145,0,500),(145,1,0),(145,2,0),
        (146,0,500),(146,1,0),(146,2,0),
    ],
}

# Stagger dates across recent months for realistic trends
from datetime import date as date_cls
_base_date = date_cls(2026, 7, 24)


def _stagger_date(index: int) -> date_cls:
    """Spread contributions across Jan-Jul 2026."""
    from datetime import timedelta
    day_offset = index % 210  # ~7 months of unique days
    return _base_date - timedelta(days=210 - day_offset)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        existing = (await session.execute(select(func.count(Member.id)))).scalar()
        if existing and existing > 0:
            print(f"Database already has {existing} members, skipping seed")
            return

        cause_ids = []
        for c in SEED_DATA["causes"]:
            cause = ContributionCause(name=c["name"])
            session.add(cause)
            await session.flush()
            cause_ids.append(cause.id)

        member_ids = []
        for i, name in enumerate(SEED_DATA["members"], 1):
            member = Member(member_number=i, name=name)
            session.add(member)
            await session.flush()
            member_ids.append(member.id)

        methods = ["cash", "mpesa", "bank"]
        count = 0
        for idx, (midx, cidx, amount) in enumerate(SEED_DATA["contributions"]):
            if amount > 0:
                method = methods[idx % 3]
                ref = ""
                if method == "mpesa":
                    ref = f"MP{random.randint(100000, 999999)}"
                elif method == "bank":
                    ref = f"TRF{random.randint(10000, 99999)}"
                contrib = Contribution(
                    member_id=member_ids[midx],
                    cause_id=cause_ids[cidx],
                    amount=amount,
                    payment_method=method,
                    transaction_ref=ref,
                    date_paid=_stagger_date(count),
                )
                session.add(contrib)
                count += 1

        await session.commit()
        print(f"Seeded: {len(member_ids)} members, {len(cause_ids)} causes, {count} contributions")

    async with async_session() as session:
        total = (await session.execute(select(func.coalesce(func.sum(Contribution.amount), 0)))).scalar()
        print(f"Total: KES {float(total):,.0f}")


if __name__ == "__main__":
    asyncio.run(seed())
