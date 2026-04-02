#!/usr/bin/env python3
"""
ASCII Art Formatter for Creator Insights
Beautiful terminal output with box drawing, bars, and emojis.
"""

def create_box(title, width=60):
    """Create a fancy box with title"""
    top = f"╔{'═' * (width - 2)}╗"
    title_line = f"║ {title.center(width - 4)} ║"
    separator = f"╠{'═' * (width - 2)}╣"
    bottom = f"╚{'═' * (width - 2)}╝"
    return top, title_line, separator, bottom


def create_header(text, width=60):
    """Create a header with double lines"""
    border = "═" * width
    centered = text.center(width)
    return f"\n{border}\n{centered}\n{border}"


def create_section_header(text, width=60):
    """Create a section header with emoji"""
    line = "─" * width
    return f"\n{text}\n{line}"


def create_progress_bar(value, max_value, width=20, filled_char="█", empty_char="░"):
    """Create a visual progress bar

    Args:
        value: Current value
        max_value: Maximum value
        width: Width of the bar in characters
        filled_char: Character for filled portion
        empty_char: Character for empty portion

    Returns:
        String representation of progress bar
    """
    if max_value == 0:
        percentage = 0
    else:
        percentage = min(100, (value / max_value) * 100)

    filled_length = int(width * percentage / 100)
    bar = filled_char * filled_length + empty_char * (width - filled_length)
    return f"{bar} {percentage:.1f}%"


def create_metric_bar(label, value, max_value, width=40, show_value=True):
    """Create a labeled metric bar"""
    bar_width = width - len(label) - 12  # Space for label and value
    bar = create_progress_bar(value, max_value, bar_width)

    if show_value:
        value_str = format_number(value)
        return f"  {label:<20} {bar}  {value_str:>10}"
    else:
        return f"  {label:<20} {bar}"


def format_number(num):
    """Format number with K/M suffix"""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return f"{num:.0f}"


def create_sparkline(data, width=20):
    """Create a sparkline (mini line chart) from data

    Args:
        data: List of numeric values
        width: Width of sparkline in characters

    Returns:
        String representation of sparkline
    """
    if not data or len(data) == 0:
        return "─" * width

    # Sparkline characters from low to high
    chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

    min_val = min(data)
    max_val = max(data)

    if max_val == min_val:
        return chars[4] * min(len(data), width)

    # Normalize and convert to sparkline
    normalized = [(x - min_val) / (max_val - min_val) for x in data]
    sparkline = ''.join([chars[min(int(x * len(chars)), len(chars) - 1)] for x in normalized])

    # Truncate or pad to width
    if len(sparkline) > width:
        return sparkline[:width]
    else:
        return sparkline


def create_stat_card(label, value, change=None, width=30):
    """Create a stat card with optional change indicator

    Args:
        label: Metric label
        value: Current value
        change: Optional change value (positive/negative)
        width: Width of card

    Returns:
        Multi-line stat card
    """
    top = f"┌{'─' * (width - 2)}┐"
    label_line = f"│ {label:<{width - 4}} │"
    value_line = f"│ {str(value):<{width - 4}} │"

    if change is not None:
        if change > 0:
            change_str = f"↑ +{change:.1f}%"
            emoji = "📈"
        elif change < 0:
            change_str = f"↓ {change:.1f}%"
            emoji = "📉"
        else:
            change_str = "→ 0.0%"
            emoji = "➡️"

        change_line = f"│ {emoji} {change_str:<{width - 7}} │"
    else:
        change_line = f"│{' ' * (width - 2)}│"

    bottom = f"└{'─' * (width - 2)}┘"

    return f"{top}\n{label_line}\n{value_line}\n{change_line}\n{bottom}"


def create_table_row(columns, widths, separator="│"):
    """Create a table row with aligned columns

    Args:
        columns: List of column values
        widths: List of column widths
        separator: Column separator character

    Returns:
        Formatted table row
    """
    formatted_cols = []
    for col, width in zip(columns, widths):
        col_str = str(col)
        if len(col_str) > width:
            col_str = col_str[:width - 3] + "..."
        formatted_cols.append(col_str.ljust(width))

    return f"{separator} {' │ '.join(formatted_cols)} {separator}"


def create_table_separator(widths, style="middle"):
    """Create table separator line

    Args:
        widths: List of column widths
        style: 'top', 'middle', or 'bottom'

    Returns:
        Separator line
    """
    if style == "top":
        left, mid, right, line = "┌", "┬", "┐", "─"
    elif style == "bottom":
        left, mid, right, line = "└", "┴", "┘", "─"
    else:  # middle
        left, mid, right, line = "├", "┼", "┤", "─"

    segments = [line * (w + 2) for w in widths]
    return f"{left}{mid.join(segments)}{right}"


def create_ranking_list(items, title="Rankings", width=60, show_bars=True):
    """Create a visual ranking list

    Args:
        items: List of tuples (rank, label, value)
        title: List title
        width: Width of display
        show_bars: Whether to show value bars

    Returns:
        Formatted ranking list
    """
    output = []
    output.append(create_section_header(f"🏆 {title}", width))

    if not items:
        output.append("  No data available")
        return "\n".join(output)

    max_value = max([item[2] for item in items]) if items else 1

    for rank, label, value in items:
        # Rank emoji
        if rank == 1:
            rank_emoji = "🥇"
        elif rank == 2:
            rank_emoji = "🥈"
        elif rank == 3:
            rank_emoji = "🥉"
        else:
            rank_emoji = f"{rank}."

        # Format value
        value_str = format_number(value)

        if show_bars:
            bar_width = width - len(str(rank_emoji)) - len(label) - len(value_str) - 8
            bar = create_progress_bar(value, max_value, bar_width)
            line = f"  {rank_emoji} {label:<25} {bar} {value_str:>8}"
        else:
            line = f"  {rank_emoji} {label:<40} {value_str:>12}"

        output.append(line)

    return "\n".join(output)


def create_comparison_bars(data, width=60):
    """Create side-by-side comparison bars

    Args:
        data: List of tuples (label, value1, value2, label1, label2)
        width: Width of display

    Returns:
        Formatted comparison
    """
    output = []

    for label, val1, val2, label1, label2 in data:
        total = val1 + val2
        if total == 0:
            continue

        bar_width = width - len(label) - 4
        val1_width = int((val1 / total) * bar_width)
        val2_width = bar_width - val1_width

        bar1 = "█" * val1_width
        bar2 = "░" * val2_width

        output.append(f"  {label}")
        output.append(f"    {label1}: {bar1}{bar2} {val1:.1f}")
        output.append(f"    {label2}: {bar2}{bar1} {val2:.1f}")
        output.append("")

    return "\n".join(output)


def create_emoji_indicator(value, thresholds):
    """Create emoji-based indicator

    Args:
        value: Numeric value
        thresholds: List of tuples (threshold, emoji)

    Returns:
        Appropriate emoji
    """
    for threshold, emoji in sorted(thresholds, reverse=True):
        if value >= threshold:
            return emoji
    return thresholds[-1][1]  # Return lowest threshold emoji


def wrap_in_box(content, title=None, width=60):
    """Wrap content in a fancy box

    Args:
        content: Text content (can be multi-line)
        title: Optional title
        width: Box width

    Returns:
        Boxed content
    """
    lines = content.split('\n')
    output = []

    # Top border
    if title:
        title_text = f" {title} "
        padding = (width - len(title_text) - 2) // 2
        top = f"╔{'═' * padding}{title_text}{'═' * (width - padding - len(title_text) - 2)}╗"
    else:
        top = f"╔{'═' * (width - 2)}╗"

    output.append(top)

    # Content lines
    for line in lines:
        # Truncate or pad line
        if len(line) > width - 4:
            line = line[:width - 7] + "..."
        padded = line.ljust(width - 4)
        output.append(f"║ {padded} ║")

    # Bottom border
    bottom = f"╚{'═' * (width - 2)}╝"
    output.append(bottom)

    return "\n".join(output)


def create_info_panel(icon, title, content, width=60):
    """Create an info panel with icon

    Args:
        icon: Emoji icon
        title: Panel title
        content: List of content lines
        width: Panel width

    Returns:
        Formatted panel
    """
    output = []
    header = f"{icon} {title}"
    output.append(f"\n┌{'─' * (width - 2)}┐")
    output.append(f"│ {header:<{width - 4}} │")
    output.append(f"├{'─' * (width - 2)}┤")

    for line in content:
        if len(line) > width - 4:
            line = line[:width - 7] + "..."
        output.append(f"│ {line:<{width - 4}} │")

    output.append(f"└{'─' * (width - 2)}┘")

    return "\n".join(output)


# ANSI color codes (optional, works on most terminals)
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


def colorize(text, color):
    """Add ANSI color to text

    Args:
        text: Text to colorize
        color: Color from Colors class

    Returns:
        Colorized text
    """
    return f"{color}{text}{Colors.RESET}"
