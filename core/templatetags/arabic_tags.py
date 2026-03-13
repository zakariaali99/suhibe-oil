from django import template
import arabic_reshaper
from bidi.algorithm import get_display

register = template.Library()

@register.filter(name='arabic')
def arabic(value):
    if value is None:
        return ""
    text = str(value)
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

@register.simple_tag(name='ar')
def ar(text):
    if text is None:
        return ""
    text = str(text)
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)
