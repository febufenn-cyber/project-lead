class LeadCleaner:
    def clean(self, row: dict) -> dict:
        cleaned = {}
        for key, value in row.items():
            if isinstance(value, str):
                cleaned[key] = value.strip()
            else:
                cleaned[key] = value
        return cleaned
