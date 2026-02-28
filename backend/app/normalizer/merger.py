class LeadMerger:
    def merge(self, left: dict, right: dict) -> dict:
        merged = dict(left)
        for key, value in right.items():
            if key not in merged or merged[key] in (None, "", [], {}):
                merged[key] = value
        return merged
