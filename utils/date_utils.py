from datetime import datetime


def convert_yyyymmdd_to_dotted(date_str: str) -> str:
    return f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:]}"
