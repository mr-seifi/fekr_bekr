from django.db import models


class Player(models.Model):
    name = models.CharField(max_length=64)


class Color(models.Model):
    name = models.CharField(max_length=32)


class Choice(models.Model):
    colors = models.ManyToManyField(to=Color)

    def __str__(self):
        return f'{("-".join([color.name for color in self.colors.all()]))}'


class Card(models.Model):
    player = models.ForeignKey(to=Player, on_delete=models.CASCADE, related_name='cards')
    choices = models.ManyToManyField(to=Choice)


class Game(models.Model):
    players = models.ManyToManyField(to=Player)
