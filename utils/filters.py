from datetime import datetime
from config import Config

def thai_datetime_filter(timestamp):
    """แปลง timestamp เป็นวันเวลาไทย"""
    if not timestamp:
        return '-'

    try:
        if hasattr(timestamp, 'tzinfo'):
            thai_time = timestamp.astimezone(Config.TIMEZONE)
            return thai_time.strftime('%d/%m/%Y %H:%M น.')
        else:
            return str(timestamp)
    except:
        return str(timestamp)

def thai_date_filter(date_str):
    """แปลงวันที่เป็นรูปแบบไทย"""
    if not date_str:
        return '-'

    try:
        if isinstance(date_str, str) and '-' in date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%d/%m/%Y')
        return date_str
    except:
        return date_str

def thai_time_filter(timestamp):
    """แปลง timestamp เป็นเวลาไทย (เฉพาะเวลา)"""
    if not timestamp:
        return '-'

    try:
        if hasattr(timestamp, 'tzinfo'):
            thai_time = timestamp.astimezone(Config.TIMEZONE)
            return thai_time.strftime('%H:%M น.')
        else:
            return str(timestamp)
    except:
        return str(timestamp)

def register_filters(app):
    """Register all custom Jinja2 filters"""
    app.template_filter('thai_datetime')(thai_datetime_filter)
    app.template_filter('thai_date')(thai_date_filter)
    app.template_filter('thai_time')(thai_time_filter)