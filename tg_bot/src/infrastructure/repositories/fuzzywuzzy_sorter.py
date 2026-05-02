from fuzzywuzzy import fuzz
import re

from src.domain.interfaces import IStringSorterRepository


class FuzzywuzzyRepository(IStringSorterRepository):
    def clean_string(self, text):
        return re.sub(r'\s+', ' ', text.strip()).lower()

    async def sort_by_similarity(self, target: str, string_list: list[str]) -> list[str]:
        cleaned_search = self.clean_string(target)
        scored_strings = []
        for string in string_list:
            cleaned_string = self.clean_string(string)
            score = fuzz.token_sort_ratio(cleaned_search, cleaned_string)
            scored_strings.append((string, score))
        scored_strings.sort(key=lambda x: x[1], reverse=True)
        return [string for string, score in scored_strings]

