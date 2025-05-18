import re


def escape_telegram_markdown(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    return re.sub(r"([{}])".format(re.escape(escape_chars)), r"\\\1", text)


def markdown_to_telegram(text: str) -> str:
    # Remove headers like #, ##, etc.
    text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Split text into chunks: links and non-links
    parts = []
    last_end = 0
    for match in re.finditer(r"\[(.*?)\]\((.*?)\)", text):
        start, end = match.span()

        # Add and escape text before the link
        if last_end < start:
            before = text[last_end:start]
            parts.append(escape_telegram_markdown(before))

        # Handle the link
        label = escape_telegram_markdown(match.group(1))
        url = match.group(2)
        parts.append(f"[{label}]({url})")

        last_end = end

    # Add and escape any remaining text after last link
    if last_end < len(text):
        parts.append(escape_telegram_markdown(text[last_end:]))

    text = "".join(parts)

    # Convert **bold**
    text = re.sub(
        r"\*(\*[^*]+\*)\*",
        lambda m: f"*{escape_telegram_markdown(m.group(1)[1:-1])}*",
        text,
    )
    # Convert *italic*
    text = re.sub(
        r"(?<!\*)\*(?!\*)([^*]+)(?<!\*)\*(?!\*)",
        lambda m: f"_{escape_telegram_markdown(m.group(1))}_",
        text,
    )

    return text
