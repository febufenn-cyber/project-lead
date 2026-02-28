"""Campaign sending and management."""

import asyncio
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionFactory
from app.models import Campaign, CampaignRecipient, CampaignStatus, CampaignStep, EmailAccount, EmailEvent, EmailEventType, Lead
from app.services.email_sender import send_email_sync


async def send_campaign_step(campaign_id: UUID, recipient_id: UUID) -> bool:
    """Send the current step email to a recipient."""
    async with AsyncSessionFactory() as session:
        campaign = await session.get(Campaign, campaign_id, options=[selectinload(Campaign.steps), selectinload(Campaign.recipients)])
        recipient = await session.get(CampaignRecipient, recipient_id)
        if not campaign or not recipient or campaign.status != CampaignStatus.active:
            return False

        steps = sorted(campaign.steps, key=lambda s: s.order)
        if recipient.current_step >= len(steps):
            return False

        step = steps[recipient.current_step]
        from_addr = campaign.from_email
        from_name = campaign.from_name
        smtp_host, smtp_port, smtp_user, smtp_password, use_tls = None, 587, None, None, True

        if campaign.email_account_id:
            acct = await session.get(EmailAccount, campaign.email_account_id)
            if acct and acct.is_active:
                from_addr = acct.email
                from_name = acct.display_name or from_name
                smtp_host = acct.smtp_host
                smtp_port = acct.smtp_port or 587
                smtp_user = acct.smtp_user
                smtp_password = acct.smtp_password_encrypted
                use_tls = acct.use_tls

        if not from_addr or not smtp_host:
            return False

        body_html = step.body_html or ""
        body_text = step.body_text or ""

        loop = asyncio.get_event_loop()
        sent = await loop.run_in_executor(
            None,
            lambda: send_email_sync(
                to_email=recipient.email,
                subject=step.subject,
                body_html=body_html,
                body_text=body_text,
                from_email=from_addr,
                from_name=from_name,
                reply_to=campaign.reply_to,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                use_tls=use_tls,
            ),
        )

        if sent:
            recipient.current_step += 1
            recipient.status = "sent"
            recipient.last_sent_at = datetime.utcnow()
            evt = EmailEvent(
                campaign_id=campaign_id,
                recipient_id=recipient_id,
                event_type=EmailEventType.sent.value,
                step_order=step.order,
            )
            session.add(evt)
            await session.commit()
        return sent
