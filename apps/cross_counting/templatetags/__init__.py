# apps/cross_counting/templatetags/json_filters.py

import json
import uuid
from datetime import datetime, date
from django import template
from django.core.serializers.json import DjangoJSONEncoder

register = template.Library()


class UUIDEncoder(DjangoJSONEncoder):
    """
    Custom JSON encoder that handles UUID objects and other Django model fields
    """

    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


@register.filter
def json_safe(value):
    """
    Template filter to safely serialize Python objects to JSON for JavaScript consumption
    Handles UUID objects, datetime objects, and other Django model fields

    Usage in templates:
    {{ analysis_data.region_hourly_aggregates|json_safe }}
    """
    try:
        return json.dumps(value, cls=UUIDEncoder, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        # Fallback: try to serialize with basic encoder
        try:
            # Convert problematic objects recursively
            def serialize_recursive(obj):
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                elif isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {key: serialize_recursive(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_recursive(item) for item in obj]
                else:
                    return obj

            serialized_value = serialize_recursive(value)
            return json.dumps(serialized_value, ensure_ascii=False)
        except Exception:
            # Last resort: return empty object
            return '{}'


@register.filter
def uuid_str(value):
    """
    Template filter to convert UUID to string

    Usage in templates:
    {{ camera.id|uuid_str }}
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    return value