from src.domain.entities.headliner import Headliner, HeadlinerFollower
from src.domain.entities.user import Sources, UserRole
from src.domain.interfaces import IHeadlinerRepository, IUnitOfWork, IVKPublicationRepository
from src.services.interfaces import IHeadlinerService, IUserService


class HeadlinerService(IHeadlinerService):
    def __init__(
            self,
            uow: IUnitOfWork,
            headliner_repo: IHeadlinerRepository,
            publication_repo: IVKPublicationRepository,
            user_service: IUserService,
            vk_bot_link: str,
            tg_bot_link: str,
            max_bot_link: str
    ):
        self.__uow = uow
        self.__headliner_repo = headliner_repo
        self.__publication_repo = publication_repo
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
            photo: str | None
    ) -> Headliner:
        async with self.__uow.atomic():
            existing = await self.__headliner_repo.get_by_user(user_id, Sources.VK)
            if existing:
                return await self.__headliner_repo.update(
                    existing.id,
                    fio=fio,
                    position=position,
                    topic=topic,
                    group_link=group_link,
                    photo=photo
                )

            headliner = await self.__headliner_repo.create(Headliner(
                user_id=user_id,
                user_source=Sources.VK,
                fio=fio,
                position=position,
                topic=topic,
                group_link=group_link,
                photo=photo
            ))
        await self.__user_service.update_user_role(user_id, Sources.VK, UserRole.HEADLINER)
        return headliner

    async def publish_article(self, headliner: Headliner) -> tuple[int | None, str | None]:
        description = (
            f"Должность: {headliner.position}\n"
            f"Тема: {headliner.topic}\n"
            f"Группа: {headliner.group_link}\n\n"
            "Присоединяйтесь к команде хедлайнера через реферальную ссылку в боте."
        )
        try:
            post_id = await self.__publication_repo.publish_headliner(
                name=headliner.fio,
                description=description,
                photo=headliner.photo
            )
            return post_id, None
        except Exception as e:
            return None, str(e)

    async def get_by_user(self, user_id: int, user_source: Sources) -> Headliner | None:
        async with self.__uow.atomic():
            return await self.__headliner_repo.get_by_user(user_id, user_source)

    async def get_by_id(self, headliner_id: int) -> Headliner | None:
        async with self.__uow.atomic():
            return await self.__headliner_repo.get_by_id(headliner_id)

    async def get_all(self) -> list[Headliner]:
        async with self.__uow.atomic():
            return await self.__headliner_repo.get_all()

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
        payload = f"hl_{headliner_id}_vk"
        return {
            "VK": f"{self.__vk_bot_link}?ref={payload}",
            "MAX": f"{self.__max_bot_link}?start={payload}",
            "Telegram": f"{self.__tg_bot_link}?start={payload}",
        }
