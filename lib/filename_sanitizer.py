def sanitize_filename(unsanitized_filename: str, replacement_symbol = "_"):
    sanitized_filename = unsanitized_filename.replace("<", replacement_symbol) \
                                             .replace(">", replacement_symbol) \
                                             .replace(":", replacement_symbol) \
                                             .replace("\"", replacement_symbol) \
                                             .replace("/", replacement_symbol) \
                                             .replace("\\", replacement_symbol) \
                                             .replace("|", replacement_symbol) \
                                             .replace("?", replacement_symbol) \
                                             .replace("*", replacement_symbol)
    if sanitized_filename in (".", "..", "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"):
        raise Exception("Sanitized filename ({}) is not allowed by major OS systems.".format(sanitized_filename))
    return sanitized_filename
