from django import template  # type: ignore
import arabic_reshaper  # type: ignore
from bidi.algorithm import get_display  # type: ignore

register = template.Library()

@register.filter
def reshape_arabic(text):
    if not text:
        return ""
    try:
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)
    except Exception:
        return str(text)
