class SocialEnricher:
    async def enrich(self, website: str | None) -> dict:
        return {
            "linkedin_url": None,
            "twitter_url": None,
            "facebook_url": None,
            "instagram_url": None,
        }
