from Levenshtein import distance as lev_distance

from src.domain.interfaces import IStringSorterRepository


class LevenshteinRepository(IStringSorterRepository):
    async def sort_by_similarity(self, target: str, string_list: list[str]) -> list[str]:
        distances = {}
        for string in string_list:
            dist = lev_distance(target.lower(), string.lower())
            distances[string] = dist
        string_list.sort(key=lambda x: distances[x])
        return string_list
