"""
Contribution reminder script — checks for members with no recent contributions
to active causes and sends Telegram notifications.
Designed to run as a scheduled cron job via Hermes cronjob tool.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import urllib.request, urllib.parse
from datetime import date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models import Member, ContributionCause, Contribution
from app.database import DB_PATH, DATABASE_URL

# Telegram config
TELEGRAM_TOKEN = "7605394619:AAE7YyqBjUSqqf1UQsg0DrzJQ5v4nLImq6Y"
TELEGRAM_CHAT_ID = "6760963523"


def send_telegram(message: str):
    """Send a Telegram message."""
    try:
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data=data, timeout=10
        )
        print("Telegram sent OK")
    except Exception as e:
        print(f"Telegram send failed: {e}")


async def check_reminders():
    """Check for members who haven't contributed to active causes recently."""
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Get active causes
        causes = (await session.execute(
            select(ContributionCause).where(ContributionCause.is_active == True)
        )).scalars().all()

        if not causes:
            print("No active causes to check")
            return

        # Get all active members with their contribution status
        members = (await session.execute(
            select(Member).where(Member.is_active == True).order_by(Member.member_number)
        )).scalars().all()

        # For each cause, find members who haven't contributed in the last 30 days
        thirty_days_ago = date.today() - timedelta(days=30)
        reminders = []

        for cause in causes:
            # Get member IDs who HAVE contributed to this cause recently
            recent_contributors = (await session.execute(
                select(Contribution.member_id)
                .where(
                    Contribution.cause_id == cause.id,
                    Contribution.date_paid >= thirty_days_ago,
                )
                .distinct()
            )).scalars().all()
            recent_set = set(recent_contributors)

            # Members who haven't contributed to this cause at all
            all_contributors = (await session.execute(
                select(Contribution.member_id)
                .where(Contribution.cause_id == cause.id)
                .distinct()
            )).scalars().all()
            all_set = set(all_contributors)

            for member in members:
                if member.id not in all_set:
                    reminders.append((member, cause, "never"))
                elif member.id not in recent_set:
                    reminders.append((member, cause, "overdue"))

        if not reminders:
            print("No members need reminders")
            return

        # Send summary via Telegram
        msg_parts = ["<b>📋 Contribution Reminder</b>\n"]

        # Group by cause
        from collections import defaultdict
        by_cause = defaultdict(lambda: {"never": [], "overdue": []})
        for member, cause, status in reminders:
            by_cause[cause.name][status].append(member.name)

        total_reminded = 0
        for cause_name, groups in sorted(by_cause.items()):
            lines = []
            for status, members_list in [("overdue", "⚠️ Overdue (30+ days)"), ("never", "🆕 Never contributed")]:
                if groups[status]:
                    lines.append(f"  {members_list}:")
                    for name in groups[status]:
                        lines.append(f"    • {name}")
                        total_reminded += 1
            if lines:
                msg_parts.append(f"\n<b>→ {cause_name}</b>")
                msg_parts.extend(lines)

        msg_parts.append(f"\n\nTotal members to remind: {total_reminded}")
        msg_parts.append(f"\n💡 <a href='https://kh07-welfare.spidmax.win/alumni'>View Alumni List</a>")

        full_msg = "\n".join(msg_parts)

        # Don't send empty reminders
        if total_reminded == 0:
            print("No reminders needed")
            return

        # Truncate if too long (Telegram max ~4096 chars)
        if len(full_msg) > 4000:
            # Send per-cause breakdown instead
            msg_parts = [f"<b>📋 Contribution Reminder</b>\n\nTotal: {total_reminded} members need attention"]
            for cause_name, groups in sorted(by_cause.items()):
                total_for_cause = sum(len(g) for g in groups.values())
                if total_for_cause > 0:
                    msg_parts.append(f"\n<b>{cause_name}</b>: {total_for_cause} member(s)")
            msg_parts.append(f"\n💡 <a href='https://kh07-welfare.spidmax.win/alumni'>View Alumni List</a>")
            full_msg = "\n".join(msg_parts)

        send_telegram(full_msg)
        print(f"Sent reminder: {total_reminded} members across {len(by_cause)} causes")


if __name__ == "__main__":
    asyncio.run(check_reminders())
