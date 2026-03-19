"""
WhatsApp chat parser for Brazuka Scout.
Parses the raw .txt export into structured message objects.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# WhatsApp export format: [MM/DD/YY, HH:MM:SS AM/PM] Sender: message
MESSAGE_PATTERN = re.compile(
    r'^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2}:\d{2}\s?(?:AM|PM)?)\]\s([^:]+):\s(.*)',
    re.IGNORECASE
)

@dataclass
class Message:
    timestamp: datetime
    sender: str
    text: str
    raw: str = field(repr=False)

    @property
    def date(self):
        return self.timestamp.date()


def parse_timestamp(date_str: str, time_str: str) -> datetime:
    """Parse WhatsApp timestamp into a datetime object."""
    time_str = time_str.strip()
    dt_str = f"{date_str} {time_str}"

    # Try formats: with AM/PM and without
    for fmt in ["%m/%d/%y %I:%M:%S %p", "%m/%d/%Y %I:%M:%S %p",
                "%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S"]:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse timestamp: {dt_str!r}")


def parse_chat(filepath: str) -> list[Message]:
    """Parse a WhatsApp .txt export into a list of Message objects."""
    messages = []
    current_msg = None

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            match = MESSAGE_PATTERN.match(line)

            if match:
                # Save the previous message
                if current_msg:
                    messages.append(current_msg)

                date_str, time_str, sender, text = match.groups()
                try:
                    ts = parse_timestamp(date_str, time_str)
                    current_msg = Message(
                        timestamp=ts,
                        sender=sender.strip(),
                        text=text.strip(),
                        raw=line
                    )
                except ValueError:
                    current_msg = None
            else:
                # Continuation of previous message (multi-line)
                if current_msg:
                    current_msg.text += "\n" + line.strip()

    if current_msg:
        messages.append(current_msg)

    return messages


def filter_recent(messages: list[Message], days: int = 60) -> list[Message]:
    """Return only messages from the last N days."""
    if not messages:
        return []
    latest = max(m.timestamp for m in messages)
    from datetime import timedelta
    cutoff = latest - timedelta(days=days)
    return [m for m in messages if m.timestamp >= cutoff]


def filter_by_date_range(messages: list[Message], start: datetime, end: datetime) -> list[Message]:
    """Return messages within a date range."""
    return [m for m in messages if start <= m.timestamp <= end]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python parser.py <chat_file>")
        sys.exit(1)

    msgs = parse_chat(sys.argv[1])
    recent = filter_recent(msgs, days=30)
    print(f"Total messages: {len(msgs)}")
    print(f"Last 30 days: {len(recent)}")
    print(f"\nSample (last 5):")
    for m in recent[-5:]:
        print(f"  [{m.timestamp.strftime('%Y-%m-%d %H:%M')}] {m.sender}: {m.text[:80]}")
