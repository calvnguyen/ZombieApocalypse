import os

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404

from consts import WIDTH, HEIGHT, OBJECT_SIZE
from forms import GameForm
from models import Planet, Game


def index(request):
    """Home page view"""
    form = GameForm(request.POST or None)
    context = {}
    context['title'] = "Zombie Apocalypse Simulation"
    # form is valid then save the result
    if request.method == 'POST' and form.is_valid():
        game = form.save()
        return redirect(reverse("game_view", kwargs={'game_id': game.pk, 'sim_id': 0}))

    context['form'] = form
    return render(request, 'zombie/index.html', context=context)


def game_simulator(request, game_id, sim_id):
    """Create different simulation results"""
    game = get_object_or_404(Game, game_id=game_id)
    context = {}
    # Where Planet state to be dumped or from loaded
    filePath = "game-%s.txt" % game_id
    sim_id = int(sim_id)
    if sim_id == 0 or os.path.isfile(filePath):
        if sim_id == 0 or sim_id + 1 <= game.simulation_iteration:
            # It's beginning of simulation so create 1st plane
            if sim_id == 0:
                p = Planet()
                sim = game.simulationresult_set.first()
                p.create_initial_state(sim.human_population, sim.zombie_population, filePath)
            else:
                # We already have dumped state to the file so load them
                p = Planet(filePath=filePath)

            context['data'] = p.simulate_one_round(sim_id + 1, game)
            # Constants used in the browser for drawig
            context['width'] = WIDTH
            context['height'] = HEIGHT
            context['size'] = OBJECT_SIZE
            context['title'] = "Game %s | Simulation %s" % (game_id, sim_id + 1)
            context['url'] = reverse("game_view", kwargs={'game_id': game.game_id, 'sim_id': sim_id})
            context['next_url'] = reverse("game_view", kwargs={'game_id': game.game_id, 'sim_id': sim_id + 1})
            return render(request, "zombie/simulation.html", context)
        return redirect(reverse("simulation_end", kwargs={'game_id': game.game_id}))
    return redirect("home")


def simulation_end(request, game_id):
    game = get_object_or_404(Game, game_id=game_id)
    context = {}
    filePath = "game-%s.txt" % game_id
    if os.path.isfile(filePath):
        # Generate graph  data
        chart_data = [['Iteration', 'Human Population', 'Zombie Population', 'New Zombie Population',
                       'Panicked Human Population', 'Zombie Killed']]
        table_data = []
        for sm in game.simulationresult_set.all():
            chart_data.append([str(sm.simulation_id), sm.human_population,
                               sm.zombie_population, sm.new_zombies, sm.panicked_human,
                               sm.zombie_killed])

        prev = game.simulationresult_set.first()
        for sm in game.simulationresult_set.all()[1:]:
            table_data.append([prev.simulation_id + 1, prev.human_population, prev.zombie_population,
                               sm.human_population, sm.zombie_population, sm.new_zombies, sm.zombie_killed])
            prev = sm

        context['chart_data'] = chart_data
        context['table_data'] = table_data
        context['styles'] = ['active', 'success', 'info', 'warning', 'danger']
        context['title'] = "Game %s Ends" % game.game_id
        p = Planet(filePath=filePath)
        context['data'] = p.get_json()
        context['width'] = WIDTH
        context['height'] = HEIGHT
        context['size'] = OBJECT_SIZE
        try:
            os.remove(filePath)
        except:
            pass
        return render(request, "zombie/simulation_end.html", context)
    return redirect("home")

# route to about page
def about(request):
    """about page"""
    context = {}
    context['title'] = "Zombie Apocalypse"
    return render(request, "zombie/about.html", context)
