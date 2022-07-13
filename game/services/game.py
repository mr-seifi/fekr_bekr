from django.core.cache import caches
from django.conf import settings
from game.models import Player, Card, Choice, Game, Color
from .random_choice import RandomChoiceService


class GameService:
    PREFIX = 'G'
    REDIS_KEYS = {
        'player_turn': f'{PREFIX}'':{game_id}',
        'player_score': f'{PREFIX}'':{game_id}:{player_id}'
    }
    CLIENT = caches['default'].client.get_client()
    PLAYERS_NUMBER = 0

    def __init__(self, game_instance):
        self.game_instance: Game = game_instance
        self.PLAYERS_NUMBER = self.game_instance.players.count()

    def next_turn(self):
        current_turn = self.get_turn()
        first_player_id = self.game_instance.players.first().id

        players = self.game_instance.players.all()
        current_player = [it for it, player in enumerate(players) if player.id == current_turn][0]

        if current_player >= settings.PLAYERS_NUMBER:
            current_turn = first_player_id
        else:
            current_turn = players[current_player + 1].id

        self.CLIENT.set(name=self.REDIS_KEYS['player_turn'].format(game_id=self.game_instance.id),
                        value=current_turn)

    def get_turn(self) -> int:
        first_player_id = self.game_instance.players.first().id
        return int(self.CLIENT.get(name=self.REDIS_KEYS['player_turn'].format(game_id=self.game_instance.id))
                   or first_player_id)

    def cache_player_score(self, player_id, score):
        key = self.REDIS_KEYS['player_score'].format(game_id=self.game_instance.id,
                                                     player_id=player_id)

        last_score = self.get_player_score(player_id=player_id)
        self.CLIENT.set(name=key,
                        value=score + last_score)

    def get_player_score(self, player_id) -> int:
        key = self.REDIS_KEYS['player_score'].format(game_id=self.game_instance.id,
                                                     player_id=player_id)

        return int(self.CLIENT.get(key) or b'0')

    @staticmethod
    def create_choice_object(colors: list) -> Choice:
        ch = Choice.objects.create()
        [ch.colors.add(color) for color in colors]

        return ch

    @staticmethod
    def get_last_card(player_instance: Player) -> Card:
        return player_instance.cards.last()

    @classmethod
    def set_last_choice(cls, player_instance: Player, colors: list):
        card = cls.get_last_card(player_instance)
        choice = cls.create_choice_object(colors=colors)
        card.choices.add(choice)

    @staticmethod
    def get_last_choice(player_instance: Player) -> Choice:
        last_card: Card = player_instance.cards.last()
        return last_card.choices.last()

    @staticmethod
    def give_cards_to_players(players):
        for player in players:
            card = Card.objects.create(player=player)
            player.cards.add(card)

    @staticmethod
    def _validate_choices(choices, color_mapping) -> bool:
        try:
            [color_mapping[choice] for choice in choices]
        except KeyError:
            return False
        return True

    @staticmethod
    def _calculate_score(player_choices, actual_choices) -> int:
        return sum([1 for p_c, a_c in zip(player_choices, actual_choices) if p_c == a_c])

    def game_handler(self):
        players = self.game_instance.players.all()
        player_id_to_player_name = dict(players.values_list())
        colors = dict(Color.objects.values_list())

        random_service = RandomChoiceService()
        random_service.next_random(game_id=self.game_instance.id)

        self.give_cards_to_players(players)

        turn = self.get_turn()

        cnt = 0
        while cnt != settings.CHOICES_CARD_NUMBER:
            while turn <= self.PLAYERS_NUMBER:
                print(f'{player_id_to_player_name[turn]} turn\'s')
                print(colors)
                print(f'Choose {settings.COLOR_CHOICES_NUMBER} of the above colors like this: 1 2 3 ...')

                player_colors = list(map(lambda x: int(x), input().split(' ')))

                validated = self._validate_choices(player_colors, colors)
                if not validated:
                    continue

                player = Player.objects.get(pk=turn)
                self.set_last_choice(player_instance=player, colors=player_colors)
                self.next_turn()
                turn = self.get_turn()

            last_choices = {player.id: self.get_last_choice(player) for player in players}
            for player_id, choice in last_choices.items():
                player_name = Player.objects.get(pk=player_id).name
                print(f'{player_name} choices: {str(choice)}')

            actual_choices_id = random_service.get_current_random(game_id=self.game_instance.id)
            actual_choices = random_service.get_current_color_names(game_id=self.game_instance.id)
            print(f'The actual ones: {"-".join(actual_choices)}')

            max_score, player_name = -1, ''
            for player in players:
                player_score = self._calculate_score(last_choices[player.id], actual_choices_id)
                self.cache_player_score(player_id=player.id, score=player_score)

                total_player_score = self.get_player_score(player_id=player.id)
                print(f'{player.name} score: {total_player_score}')

                if player_score > max_score:
                    max_score = player_score
                    player_name = player.name

            if max_score == settings.COLOR_CHOICES_NUMBER:
                print(f'{player_name} Wins! :))')
                break

            self.next_turn()
            cnt += 1

        print('Nobody win!')
