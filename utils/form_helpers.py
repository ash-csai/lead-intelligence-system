def normalize_form_input(field_name, value):
    if field_name in {"school_id", "coaching_id", "follow_up_date"} and value == "":
        return None
    if field_name == "interest_level" and value is not None:
        return value.lower()
    return value
