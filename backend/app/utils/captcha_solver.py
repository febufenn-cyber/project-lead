class CaptchaSolver:
    async def solve_recaptcha(self, site_key: str, page_url: str) -> str:
        raise NotImplementedError("Captcha solving is not enabled in this baseline.")
