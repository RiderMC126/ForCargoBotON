import re 


# Валидация телефона (+7XXXXXXXXXX) и даты (ДД.ММ.ГГГГ)
def validate_phone(phone):
    pattern = r'^\+7\d{10}$'
    return bool(re.match(pattern, phone))

def validate_date(date):
    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    return bool(re.match(pattern, date))