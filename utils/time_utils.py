from datetime import datetime
import time
from datetime import datetime, timezone, timedelta

def current_time(format="%Y-%m-%d %H:%M:%S.%f", cutoff=3):
    ret = datetime.now().strftime(format)
    if cutoff:
        return ret[:-cutoff]
    return ret

def current_timeoffset():
    timezone_offset = time.strftime('%z')
    # Format +0800 to +08:00
    if len(timezone_offset) == 5:
        return timezone_offset[:3] + ':' + timezone_offset[3:]
    return timezone_offset

def current_iso8601_time():
    return current_time(format="%Y-%m-%dT%H:%M:%S", cutoff=0) + current_timeoffset()


def days_between_someday_and_today(someday):
    """
    计算某一天到今天的天数
    :param someday: str, 格式为 "2025-05-14T23:27:25.000+08:00"
    :return: int
    """
    # 处理带有时区的字符串
    if '+' in someday:
        # Handle timezone formats like "+08:00" or "+0800"
        parts = someday.rsplit('+', 1)
        dt_str = parts[0]
        offset_str = parts[1]
        
        # Handle different timezone formats
        if ':' in offset_str:
            offset_hours = int(offset_str.split(':')[0])
            offset_minutes = int(offset_str.split(':')[1])
        else:
            offset_hours = int(offset_str[:2])
            offset_minutes = int(offset_str[2:]) if len(offset_str) > 2 else 0
        
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")
        dt = dt.replace(tzinfo=timezone(timedelta(hours=offset_hours, minutes=offset_minutes)))
    elif '-' in someday[19:]:  # Only check for timezone '-', not date separators
        parts = someday.rsplit('-', 1)
        dt_str = parts[0]
        offset_str = parts[1]
        
        # Handle different timezone formats
        if ':' in offset_str:
            offset_hours = int(offset_str.split(':')[0])
            offset_minutes = int(offset_str.split(':')[1])
        else:
            offset_hours = int(offset_str[:2])
            offset_minutes = int(offset_str[2:]) if len(offset_str) > 2 else 0
        
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")
        dt = dt.replace(tzinfo=timezone(timedelta(hours=-offset_hours, minutes=-offset_minutes)))
    else:
        dt = datetime.strptime(someday, "%Y-%m-%dT%H:%M:%S.%f")
        dt = dt.replace(tzinfo=None)

    today = datetime.now(dt.tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
    someday_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return (today - someday_date).days


if __name__ == "__main__":
    # 获取当前时间和时区信息
    now = datetime.now()
    timezone_name = time.tzname[time.daylight]
    timezone_offset = current_timeoffset()

    print(f"当前时间: {now}")
    print(f"时区名称: {timezone_name}")
    print(f"时区偏移: {timezone_offset}")

    print(f"当前时间（ISO 8601格式）: {current_iso8601_time()}")

    print(f"今天到某一天的天数: {days_between_someday_and_today('2025-05-14T23:27:25.000+08:00')}")