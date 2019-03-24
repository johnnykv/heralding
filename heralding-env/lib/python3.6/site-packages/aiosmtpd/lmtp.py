from aiosmtpd.smtp import SMTP, syntax
from public import public


@public
class LMTP(SMTP):
    @syntax('LHLO hostname')
    async def smtp_LHLO(self, arg):
        """The LMTP greeting, used instead of HELO/EHLO."""
        await super().smtp_HELO(arg)
        self.show_smtp_greeting = False

    async def smtp_HELO(self, arg):
        """HELO is not a valid LMTP command."""
        await self.push('500 Error: command "HELO" not recognized')

    async def smtp_EHLO(self, arg):
        """EHLO is not a valid LMTP command."""
        await self.push('500 Error: command "EHLO" not recognized')
