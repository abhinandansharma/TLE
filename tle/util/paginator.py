import asyncio
import functools

_REACT_FIRST = '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}'
_REACT_PREV = '\N{BLACK LEFT-POINTING TRIANGLE}'
_REACT_NEXT = '\N{BLACK RIGHT-POINTING TRIANGLE}'
_REACT_LAST = '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}'


class PaginatorError(Exception):
    pass


class NoPagesError(PaginatorError):
    pass


class InsufficientPermissionsError(PaginatorError):
    pass


class Paginated:
    def __init__(self, bot, pages, wait_time):
        self.bot = bot
        self.pages = pages
        self.wait_time = wait_time
        self.cur_page = None
        self.message = None
        self.reaction_map = {
            _REACT_FIRST: functools.partial(self.show_page, 1),
            _REACT_PREV: self.prev_page,
            _REACT_NEXT: self.next_page,
            _REACT_LAST: functools.partial(self.show_page, len(pages))
        }

    async def show_page(self, page_num):
        if 1 <= page_num <= len(self.pages):
            content, embed = self.pages[page_num - 1]
            await self.message.edit(content=content, embed=embed)
            self.cur_page = page_num

    async def prev_page(self):
        await self.show_page(self.cur_page - 1)

    async def next_page(self):
        await self.show_page(self.cur_page + 1)

    async def paginate(self, ctx):
        content, embed = self.pages[0]
        self.message = await ctx.send(content, embed=embed)

        if len(self.pages) == 1:
            # No need to paginate.
            return

        self.cur_page = 1
        for react in self.reaction_map.keys():
            await self.message.add_reaction(react)

        def check(reaction, user):
            return self.bot.user != user and reaction.emoji in self.reaction_map

        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=self.wait_time, check=check)
                await reaction.remove(user)
                await self.reaction_map[reaction.emoji]()
            except asyncio.TimeoutError:
                await self.message.clear_reactions()
                break


def paginate(bot, ctx, pages, *, wait_time, set_pagenum_footers=False):
    if not pages:
        raise NoPagesError()
    permissions = ctx.channel.permissions_for(ctx.guild.me)
    if not permissions.manage_messages:
        raise InsufficientPermissionsError()
    if len(pages) > 1 and set_pagenum_footers:
        for i, (content, embed) in enumerate(pages):
            embed.set_footer(text=f'Page {i + 1} / {len(pages)}')
    paginated = Paginated(bot, pages, wait_time)
    asyncio.create_task(paginated.paginate(ctx))