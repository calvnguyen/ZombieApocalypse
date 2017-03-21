from django.contrib import admin
from models import Game, SimulationResult


@admin.register(Game)
class Game(admin.ModelAdmin):
    pass

@admin.register(SimulationResult)
class Simulation(admin.ModelAdmin):
    pass
