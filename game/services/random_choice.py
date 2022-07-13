from typing import List
from game.models import Color
import random
from django.conf import settings
from django.core.cache import caches


class RandomChoiceService:
    PREFIX = 'R'
    REDIS_KEYS = {
        'current_choice': f'{PREFIX}'':{game_id}',
    }
    CLIENT = caches['default'].client.get_client()

    @staticmethod
    def _random_choice() -> List[int]:
        color_ids = list(Color.objects.values_list('id', flat=True))
        return random.sample(color_ids, k=settings.COLOR_CHOICES_NUMBER)

    @classmethod
    def next_random(cls, game_id):
        key = cls.REDIS_KEYS['current_choice'].format(game_id=game_id)
        choices: List[int] = cls._random_choice()

        cls.CLIENT.delete(key)
        cls.CLIENT.rpush(key, *choices)

    @classmethod
    def get_current_random(cls, game_id) -> List[int]:
        key = cls.REDIS_KEYS['current_choice'].format(game_id=game_id)
        return list(map(lambda x: int(x.decode()), cls.CLIENT.lrange(key, 0, settings.COLOR_CHOICES_NUMBER)))

    @classmethod
    def get_current_color_names(cls, game_id) -> List[str]:
        current_color_ids = cls.get_current_random(game_id=game_id)
        return [Color.objects.get(pk=color_id).name for color_id in current_color_ids]
