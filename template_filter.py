from django import template
import arabic_reshaper
from bidi.algorithm import get_display

register = template.Library()

@register.filter
def reshape_arabic(text):
    if text:
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)
    return text
