from src.domain.entities.headliner import Headliner, HeadlinerFollower
from src.domain.entities.user import Sources, UserRole
from src.domain.interfaces import IHeadlinerRepository, IUnitOfWork
from src.services.interfaces import IHeadlinerService, IUserService


def normalize_fio(surname: str, name: str | None, patronymic: str | None) -> str:
    parts = [surname, name, patronymic]
    return " ".join(part.strip().lower() for part in parts if part and part.strip())


class HeadlinerService(IHeadlinerService):
    def __init__(
            self,
            uow: IUnitOfWork,
            headliner_repo: IHeadlinerRepository,
            user_service: IUserService,
            vk_bot_link: str,
            tg_bot_link: str,
            max_bot_link: str
    ):
        self.__uow = uow
        self.__headliner_repo = headliner_repo
        self.__user_service = user_service
        self.__vk_bot_link = vk_bot_link
        self.__tg_bot_link = tg_bot_link
        self.__max_bot_link = max_bot_link

    async def create_headliner(
            self,
            user_id: int,
            fio: str,
            position: str,
            topic: str,
            group_link: str,
            photo: str | None,
            user_source: Sources = Sources.MAX
    ) -> Headliner:
        async with self.__uow.atomic():
            existing = await self.__headliner_repo.get_by_user(user_id, user_source)
            if existing:
                headliner = await self.__headliner_repo.update(
                    existing.id,
                    fio=fio,
                    position=position,
                    topic=topic,
                    group_link=group_link,
                    photo=photo
                )
            else:
                headliner = await self.__headliner_repo.create(Headliner(
                    user_id=user_id,
                    user_source=user_source,
                    fio=fio,
                    position=position,
                    topic=topic,
                    group_link=group_link,
                    photo=photo
                ))

        await self.__user_service.update_user_role(user_id, user_source, UserRole.HEADLINER)
        await self.__sync_headliners_by_profile(headliner)
        return headliner

    async def __sync_headliners_by_profile(self, source_headliner: Headliner) -> None:
        source_user = await self.__user_service.get_user(
            source_headliner.user_id,
            source_headliner.user_source
        )
        source_fio = normalize_fio(source_user.surname, source_user.name, source_user.patronymic)
        users = await self.__user_service.search_users_by_phone(source_user.phone_number)

        for user in users:
            if normalize_fio(user.surname, user.name, user.patronymic) != source_fio:
                continue

            async with self.__uow.atomic():
                existing = await self.__headliner_repo.get_by_user(user.id, user.source)
                if existing:
                    await self.__headliner_repo.update(
                        existing.id,
                        fio=source_headliner.fio,
                        position=source_headliner.position,
                        topic=source_headliner.topic,
                        group_link=source_headliner.group_link,
                        photo=source_headliner.photo
                    )
                else:
                    await self.__headliner_repo.create(Headliner(
                        user_id=user.id,
                        user_source=user.source,
                        fio=source_headliner.fio,
                        position=source_headliner.position,
                        topic=source_headliner.topic,
                        group_link=source_headliner.group_link,
                        photo=source_headliner.photo
                    ))

            await self.__user_service.update_user_role(user.id, user.source, UserRole.HEADLINER)

    async def publish_article(self, headliner: Headliner) -> tuple[int | None, str | None]:
        return None, "Публикация в витрину для MAX-бота не используется."

    async def get_by_user(self, user_id: int, user_source: Sources) -> Headliner | None:
        async with self.__uow.atomic():
            return await self.__headliner_repo.get_by_user(user_id, user_source)

    async def get_by_id(self, headliner_id: int) -> Headliner | None:
        async with self.__uow.atomic():
            return await self.__headliner_repo.get_by_id(headliner_id)

    async def get_all(self) -> list[Headliner]:
        async with self.__uow.atomic():
            return await self.__headliner_repo.get_all()

    async def update_headliner(self, headliner_id: int, **kwargs) -> Headliner:
        async with self.__uow.atomic():
            return await self.__headliner_repo.update(headliner_id, **kwargs)

    async def delete_headliner(self, headliner_id: int) -> Headliner | None:
        async with self.__uow.atomic():
            headliner = await self.__headliner_repo.delete(headliner_id)
        if headliner is not None:
            await self.__user_service.update_user_role(
                headliner.user_id,
                headliner.user_source,
                UserRole.USER
            )
        return headliner

    async def get_rating(self) -> list[tuple[Headliner, int]]:
        headliners = await self.get_all()
        result = []
        for headliner in headliners:
            result.append((headliner, await self.count_followers(headliner.id)))
        return sorted(result, key=lambda item: item[1], reverse=True)

    async def update_welcome_message_by_user(
            self,
            user_id: int,
            user_source: Sources,
            welcome_message: str
    ) -> Headliner | None:
        async with self.__uow.atomic():
            headliner = await self.__headliner_repo.get_by_user(user_id, user_source)
            if headliner is None:
                return None
            return await self.__headliner_repo.update(
                headliner.id,
                welcome_message=welcome_message
            )

    async def attach_follower(
            self,
            headliner_id: int,
            follower_id: int,
            follower_source: Sources
    ) -> HeadlinerFollower | None:
        async with self.__uow.atomic():
            headliner = await self.__headliner_repo.get_by_id(headliner_id)
            if headliner is None:
                return None
            if await self.__headliner_repo.is_follower_exists(follower_id, follower_source):
                return None
            return await self.__headliner_repo.add_follower(
                headliner_id,
                follower_id,
                follower_source
            )

    async def get_followers(self, headliner_id: int) -> list[HeadlinerFollower]:
        async with self.__uow.atomic():
            return await self.__headliner_repo.get_followers(headliner_id)

    async def count_followers(self, headliner_id: int) -> int:
        async with self.__uow.atomic():
            return await self.__headliner_repo.count_followers(headliner_id)

    def make_referral_links(self, headliner_id: int) -> dict[str, str]:
        payload = f"hl_{headliner_id}_max"
        return {
            "VK": f"{self.__vk_bot_link}?ref={payload}",
            "MAX": f"{self.__max_bot_link}?start={payload}",
            "Telegram": f"{self.__tg_bot_link}?start={payload}",
        }
