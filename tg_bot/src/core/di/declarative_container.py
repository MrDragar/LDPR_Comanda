from abc import ABC

from . import providers


class DeclarativeContainer(ABC):
    providers: dict[str, providers.Provider]

    def __init__(self):
        providers_dict = {}
        for name, provider in self.__dict__.items():
            if not isinstance(provider, providers.Provider):
                continue
            providers_dict[name] = provider()
        self.providers = providers_dict

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls, *args, **kwargs)
        for key, value in vars(cls).items():
            obj.__dict__[key] = value
        return obj
