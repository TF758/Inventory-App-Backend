def get_serializer_field_info(serializer_class):
    """
    Return metadata about serializer fields.
    Used for dynamic forms / frontend hints.
    """
    serializer = serializer_class()
    field_info = {}

    for name, field in serializer.fields.items():
        info = {
            "required": field.required,
            "allow_null": getattr(field, "allow_null", False),
            "allow_blank": getattr(field, "allow_blank", False),
        }

        if getattr(field, "max_length", None):
            info["max_length"] = field.max_length
        if getattr(field, "min_length", None):
            info["min_length"] = field.min_length
        if getattr(field, "choices", None):
            info["choices"] = list(field.choices.keys())

        field_info[name] = info

    return field_info
