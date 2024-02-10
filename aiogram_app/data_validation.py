import re


def validate_cyrillic_words(input_string):
    cyrillic_words = re.findall(r'\b[а-яА-Я]+\b', input_string)
    return 1 <= len(cyrillic_words) <= 3


def validate_phone_number(input_string):
    pattern = r'^(?:\+7|7|8)[\s-]*(\d[\s-]*){10}$'
    return bool(re.match(pattern, input_string))


def serialize_phone(input_string):
    digits = re.sub(r'[^\d]', '', input_string)
    return f'+7{digits[-10:]}'

