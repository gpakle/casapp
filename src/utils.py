from datetime import date, datetime
import calendar

def get_month_end(dt: date) -> date:
    """Returns the last day of the month for a given date."""
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return date(dt.year, dt.month, last_day)

def parse_date(date_str: str) -> date:
    """Parses YYYY-MM-DD string to date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()
    
def month_diff(d1: date, d2: date) -> int:
    """Returns number of months between two dates."""
    return (d1.year - d2.year) * 12 + d1.month - d2.month
