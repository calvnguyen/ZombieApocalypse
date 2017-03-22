# this is where all the game logic and database objects are stored
from __future__ import unicode_literals
import copy
import random
import re
import bcrypt
from datetime import datetime
from django.db import models

from consts import WIDTH, HEIGHT, \
    HUMAN_SPEED_X, HUMAN_SPEED_Y, ZOMBIE_SPEED_X, \
    ZOMBIE_SPEED_Y, OBJECT_SIZE


class Game(models.Model):
    game_id = models.AutoField(primary_key=True)
    date = models.DateTimeField(auto_now=True)
    population_count = models.PositiveIntegerField(default=100)
    infected_population = models.FloatField(default=40, verbose_name="Infected Population(%)")
    simulation_iteration = models.PositiveIntegerField(default=5)

    def save(self, *args, **kwargs):
        """Save Game and create 0th simulation state"""
        super(Game, self).save(*args, **kwargs)
        zombie_population = int((self.population_count * self.infected_population) / 100)
        human_population = self.population_count - zombie_population
        simulation = self.simulationresult_set.filter(simulation_id=0)
        # if simulation already exist then just update that
        if len(simulation) > 0:
            simulation = simulation[0]
            simulation.human_population = human_population
            simulation.zombie_population = zombie_population
            simulation.save()
        else:
            SimulationResult.objects.create(game=self, human_population=human_population,
                                            zombie_population=zombie_population)

    def __str__(self):
        return str([self.pk, self.population_count, self.infected_population])


class SimulationResult(models.Model):
    game = models.ForeignKey(Game)
    simulation_id = models.IntegerField(default=0)
    human_population = models.PositiveIntegerField()
    new_zombies = models.IntegerField(default=0)
    zombie_population = models.PositiveIntegerField(default=0)
    panicked_human = models.PositiveIntegerField(default=0)
    fighting_human = models.PositiveIntegerField(default=0)
    zombie_killed = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str([self.simulation_id, self.human_population, self.zombie_population, self.new_zombies])


class Human(object):
    im = 0  # Human
    width = WIDTH
    height = HEIGHT

    def __init__(self, x, y, speedX=HUMAN_SPEED_X, speedY=HUMAN_SPEED_Y):
        self.x = x
        self.y = y
        self.speedX = speedX
        self.speedY = speedY

    def move(self, time):

        """
        Move four direction randomly
               1

         3            4

                2
        """
        direction = random.randint(1, 4)
        if direction == 1:
            self.moveDxDy(self.speedX * time, self.speedY * time)
        elif direction == 2:
            self.moveDxDy(self.speedX * time, -self.speedY * time)
        elif direction == 3:
            self.moveDxDy(-self.speedX * time, self.speedY * time)
        else:
            self.moveDxDy(-self.speedX * time, -self.speedY * time)

    def moveDxDy(self, dx, dy):
        """Take delta step"""
        self.x += dx
        self.y += dy
        # Human has moved out of the boundary so place at random co-ordinates
        if self.x + OBJECT_SIZE > self.width or self.y + OBJECT_SIZE > self.height:
            self.place_random()

    def set_speed(self, speedX, speedY):
        self.speedX = speedX
        self.speedY = speedY

    def __str__(self):
        return "%s:%s:%s:%s:%s" % (self.im, self.x, self.y, self.speedX, self.speedY)

    def place_random(self):
        """Place my self at random location"""
        self.x = random.randint(1, self.width - OBJECT_SIZE)
        self.y = random.randint(1, self.height - OBJECT_SIZE)

    def __eq__(self, other):
        # check whether two objects are same of not
        return self.im == other.x and \
               self.x == other.x and \
               self.y == other.y and \
               self.speedY == other.speedY and \
               self.speedX == other.speedX


class PanickedHuman(Human):
    im = 1  # "PanickedHuman"

    def __init__(self, x, y, speedX=2 * HUMAN_SPEED_X, speedY=2 * HUMAN_SPEED_Y):
        super(PanickedHuman, self).__init__(x, y, speedX, speedY)


class Zombie(Human):
    im = 2  # "Zombie"

    def __init__(self, x, y, speedX=ZOMBIE_SPEED_X, speedY=ZOMBIE_SPEED_Y):
        super(Zombie, self).__init__(x, y, speedX, speedY)
        self.speedX = speedX
        self.speedY = speedY

    def move(self, time):
        direction = random.randint(1, 8)
        """
                   1
                5       6
             3     0       4
                8      7
                    2
        """
        if direction == 1:
            self.moveDxDy(0, time * self.speedY)
        elif direction == 2:
            self.moveDxDy(0, -time * self.speedY)
        elif direction == 3:
            self.moveDxDy(-time * self.speedX, 0)
        elif direction == 4:
            self.moveDxDy(time * self.speedX, 0)
        elif direction == 5:
            self.moveDxDy(-time * self.speedX, time * self.speedY)
        elif direction == 6:
            self.moveDxDy(time * self.speedX, time * self.speedY)
        elif direction == 7:
            self.moveDxDy(time * self.speedX, -time * self.speedY)
        elif direction == 8:
            self.moveDxDy(-time * self.speedX, -time * self.speedY)


class FightingHuman(Human):
    im = 3  # "FightingHuman"


class Planet(object):
    def __init__(self, height=HEIGHT, width=WIDTH, filePath=None):
        self.height = height
        self.width = width
        self.filePath = filePath
        self.objects = dict()
        self.zombie_killed = 0
        if self.filePath is not None:
            self.load_state_from_file(self.filePath)

    def object_types(self, x, y):
        """Returns list of object types at a co-ordinate (x,y)"""
        types = set()
        if (x, y) in self.objects:
            for obj in self.objects[(x, y)]:
                types.add(type(obj))
        return types

    def count_population(self):
        zombie = 0
        human = 0
        panicked_human = 0
        fighting_human = 0

        for _, values in self.objects.items():
            for value in values:
                if value.im == Zombie.im:
                    zombie += 1
                elif value.im == Human.im:
                    human += 1
                elif value.im == PanickedHuman.im:
                    panicked_human += 1
                elif value.im == FightingHuman.im:
                    fighting_human += 1

        return zombie, human, panicked_human, fighting_human

    def simulate_one_round(self, iteration, game):
        # Move all creatures one step further
        self.data = []
        keys = self.objects.keys()
        for key in keys:
            self.move(*key)
            # self.data.append(self.get_json())
        self.data.append(self.get_json())
        # Save state to file which will be used for creation
        self.dump_state_to_file(self.filePath)
        self.create_db_entry(iteration, game)
        return '{"data":[%s]}' % ",".join(self.data)

    def create_db_entry(self, iteration, game):
        """Add a new entry in database for this simulation round"""
        zombie, human, panic, fighting = self.count_population()
        sm = SimulationResult.objects.get(game=game, simulation_id=iteration - 1)
        new_zombies_ = zombie - sm.zombie_population
        zombie_killed = 0
        new_zombies = 0
        # get the new zombies count
        if new_zombies_ > 0:
            new_zombies = new_zombies_

        SimulationResult.objects.create(game=game,
                                        simulation_id=iteration,
                                        human_population=human,
                                        new_zombies=new_zombies,
                                        zombie_population=zombie,
                                        panicked_human=panic,
                                        fighting_human=fighting,
                                        zombie_killed=self.zombie_killed)

    def move(self, x, y):
        peoples = self.objects.get((x, y), set())
        new_people = []
        new_removed = []

        for people in peoples:
            people.move(1)
            if people.im == Human.im:
                types = set()
                # Check whether in OBJECT_SIZE*HUMAN_SPEED_X x OBJECT_SIZE * HUMAN_SPEED_Y
                # area is there any zombie If we find any Zombie then human will become
                # panicked human or zombie randomly
                for i in range(0, OBJECT_SIZE * HUMAN_SPEED_X):
                    for j in range(0, OBJECT_SIZE * HUMAN_SPEED_Y):
                        types = types.union(self.object_types(people.x + i, people.y))
                        types = types.union(self.object_types(people.x + i, people.y + j))
                        types = types.union(self.object_types(people.x + i, people.y - j))
                        types = types.union(self.object_types(people.x - i, people.y))
                        types = types.union(self.object_types(people.x - i, people.y + j))
                        types = types.union(self.object_types(people.x - i, people.y - j))
                        types = types.union(self.object_types(people.x, people.y + j))
                        types = types.union(self.object_types(people.x, people.y - j))
                if Zombie in types:
                    # Make zombie or panicked human randomly
                    r = random.choice([1, 2])
                    if r == 1:
                        people = PanickedHuman(people.x, people.y)
                    else:
                        people = Zombie(people.x, people.y)
                    new_people.append(people)
                else:
                    new_people.append(people)

            elif people.im == Zombie.im:
                types = set()
                for i in range(0, OBJECT_SIZE*ZOMBIE_SPEED_X):
                    for j in range(0, OBJECT_SIZE*ZOMBIE_SPEED_Y):
                        types = types.union(self.object_types(people.x + i, people.y + j))

                # There's a fighting human and zombie has entered, so zombie will be die!!!!
                if FightingHuman in types:
                    # no addition of Zombie :(
                    self.zombie_killed += 1
                else:
                    # converting to zombie
                    people = Zombie(people.x, people.y)
                    for obj in self.objects.get((people.x, people.y), []):
                        new_people.append(Zombie(obj.x, obj.y))
                        new_removed.append(obj)
                    new_people.append(people)

            elif people.im == FightingHuman.im:
                new_people.append(people)
                for i in range(0, OBJECT_SIZE*HUMAN_SPEED_X):
                    for j in range(0, OBJECT_SIZE*HUMAN_SPEED_Y):
                        for o in self.objects.get((people.x + i, people.y + j), set()):
                            if o.im == Zombie.im:
                                # ZOMBIE DYING.....count it
                                self.zombie_killed += 1
                                new_removed.append(o)
                            elif o.im == PanickedHuman.im:
                                # Become a normal human again (no panic)
                                new_removed.append(o)
                                new_people.append(Human(o.x, o.y))

            elif people.im == PanickedHuman.im:
                new_people.append(people)
            else:
                assert False, "Unknown object type"

        self.objects.pop((x, y))
        empty = []
        for people in new_removed:
            if (people.x, people.y) in self.objects and \
                            people in self.objects[(people.x, people.y)]:
                self.objects[(people.x, people.y)].remove(people)
                if len(self.objects[(people.x, people.y)]) == 0:
                    empty.append((x, y))

        for people in new_people:
            self.objects.setdefault((people.x, people.y), set()).add(people)
        for i in empty:
            if i in self.objects:
                self.objects.pop(i)

    def get_unique_location(self, locations):
        # Generate unique address for creature
        x, y = random.randint(1, self.width), random.randint(1, self.height)
        while (x, y) in locations:
            x, y = random.randint(1, self.width), random.randint(1, self.height)
        locations.append((x, y))
        return x, y

    def create_initial_state(self, humans, zombies, filePath):
        """Create initial simulation state"""
        generate_x_y = []
        for _ in xrange(humans):
            x, y = self.get_unique_location(generate_x_y)
            self.objects.setdefault((x, y), set()).add(Human(x, y))

        for _ in xrange(zombies):
            x, y = self.get_unique_location(generate_x_y)
            self.objects.setdefault((x, y), set()).add(Zombie(x, y))

        # 20% of zombies are fighting humans
        fighting_humans = zombies * 20 / 100
        if fighting_humans < 10:
            fighting_humans = 10

        for _ in xrange(fighting_humans):
            x, y = self.get_unique_location(generate_x_y)
            self.objects.setdefault((x, y), set()).add(FightingHuman(x, y))
        self.filePath = filePath
        self.dump_state_to_file(filePath)

    def dump_state_to_file(self, filePath):
        """Store simulation state in a file, file is saved based on the co-ordinates
               e.g if at address (x,y) there are 2 creatures Human, PanickedHuman
                then will be saved a new line as x:y 0:x:y:2:2 0:x:y:3:3 """

        with open(filePath, "w") as f:
            for key, values in self.objects.items():
                f.write("%s:%s " % (key[0], key[1]))
                for value in values:
                    f.write(str(value))
                    f.write(" ")
                f.write("\n")

    def load_state_from_file(self, filePath):
        """Parse the data from file and map to Creatures
               This is the reverse process of dump_state_to_file
               """
        object_map = {
            0: Human,
            1: PanickedHuman,
            2: Zombie,
            3: FightingHuman,
        }
        with open(filePath, "r") as f:
            for line in f.readlines():
                objs = line.strip().split()
                objs[0] = objs[0].split(":")
                key = (int(objs[0][0]), int(objs[0][1]))
                self.objects[key] = set()
                for obj in objs[1:]:
                    attrs = obj.split(":")
                    attrs = map(int, attrs)
                    assert len(attrs) == 5, "Wrong data to deserialize"
                    if attrs[0] in object_map:
                        people = object_map[attrs[0]](*attrs[1:])
                    else:
                        assert False, "Unknown Object Type"
                    self.objects[key].add(people)

    def get_json(self):
        """Serialize creatures state in json to be used by  browser to draw on canvas"""

        data = ["{"]
        gfirst = False
        for key, value in self.objects.items():
            if not gfirst:
                data.append('"%s,%s":[' % (key[0], key[1]))
                gfirst = True
            else:
                data.append(',"%s,%s":[' % (key[0], key[1]))
            first = False
            for val in value:
                if not first:
                    data.append('%s' % val.im)
                    first = False
                else:
                    data.append(',%s' % val.im)
            data.append("]")
        data.append("}")
        return "".join(data)


EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
# name cannot contain numbers
NAME_REGEX = re.compile(r'^[^0-9]+$')
# requires a password to have at least 1 uppercase letter and 1 numeric value.
PASS_REGEX = re.compile(r'^(?=.*[A-Z])(?=.*\d).+$')


class UserManager(models.Manager):
    def login(self, email, password):
        errors = {}

        errors['email-error'] = []
        errors['password-error'] = []

        if len(email) < 1:
            errors['email-error'].append("Email cannot be empty!")

        elif not EMAIL_REGEX.match(email):
            errors['email-error'].append("Invalid email address format!")

        if len(password) < 1:
            errors['password-error'].append("Password cannot be empty!")

        elif len(password) < 8:
            errors['password-error'].append("Password\'s length has to be more than 8 characters!")

        if len(errors['email-error']) != 0 or len(errors['password-error']) != 0:
            return (False, errors)

        else:
            try:
                user = User.userMgr.get(email=email)

                if not bcrypt.hashpw(password, user.password.encode('utf-8')) == user.password:
                    print "login check - password DO NOT MATCH"
                    errors['password-error'].append("Either email/pw is incorrect")
                    return (False, errors)
                elif bcrypt.hashpw(password, user.password.encode('utf-8')) == user.password:
                    print "login check - passwords match"
                return (True, user)


            except User.DoesNotExist:
                errors['email-error'].append("Email cannot be found")
        return (False, errors)

    def register(self, first_name, last_name, email, password, passwordconfirm, dob):
        errors = {}
        present = datetime.now()
        errors['first-name-error'] = []
        errors['last-name-error'] = []
        errors['email-error'] = []
        errors['dob-error'] = []
        errors['password-error'] = []
        errors['password-confirm-error'] = []

        if len(first_name) < 1:
            errors['first-name-error'].append("First name cannot be empty!")

        elif len(first_name) < 2:
            errors['first-name-error'].append("First name has to be at least 2 characters!")

        elif not NAME_REGEX.match(first_name):
            errors['first-name-error'].append("First name cannot contain a number!")

        if len(last_name) < 1:
            errors['last-name-error'].append("Last name cannot be empty!")

        elif len(last_name) < 2:
            errors['last-name-error'].append("Last name has to be at least 2 characters!")

        elif not NAME_REGEX.match(last_name):
            errors['last-name-error'].append("Last name cannot contain a number!")

        if len(email) < 1:
            errors['email-error'].append("Email cannot be empty!")

        elif not EMAIL_REGEX.match(email):
            errors['email-error'].append("Invalid email address format!")

        elif not self.is_date(dob):
            errors['dob-error'].append("Birthday entered is not valid!!")
        elif datetime.strptime(dob, "%Y-%m-%d") > present:
            errors['dob-error'].append("Birthday must be from the past!")

        if len(password) < 1:
            errors['password-error'].append("Password cannot be empty!")

        elif len(password) < 8:
            errors['password-error'].append("Password's length has to be more than 8 characters!")

        elif not PASS_REGEX.match(password):
            errors['password-error'].append("Password needs to have at least 1 number and 1 Upper-Case letter!")

        if len(passwordconfirm) < 1:
            errors['password-confirm-error'].append("Password Confirmation cannot be empty!")

        elif not PASS_REGEX.match(passwordconfirm):
            errors['password-confirm-error'].append(
                "Password confirmation needs to have at least 1 number and 1 Upper-Case letter!")

        elif len(passwordconfirm) < 8:
            errors['password-confirm-error'].append("Password confirmation's length has to be more than 8 characters!")

        if password != passwordconfirm:
            errors['password-confirm-error'].append("Password and password's confirmation must match!")

        print len(errors['email-error'])
        if len(errors['email-error']) != 0 or len(errors['password-error']) != 0 or len(
                errors['password-confirm-error']) != 0 or len(errors['dob-error']) != 0 or len(
            errors['first-name-error']) != 0 or len(errors['last-name-error']) != 0:
            return (False, errors)

        else:
            user = User.userMgr.filter(email=email)
            if (user):
                errors['email-error'].append("Email already exists. Please proceed to login or choose another one")
                return (False, errors)
            else:
                hashed = bcrypt.hashpw(password, bcrypt.gensalt().encode('utf-8'))
                user = User.userMgr.create(first_name=first_name, last_name=last_name, email=email, password=hashed,
                                           dob=dob)
                user.save()
                return (True, user)

    def is_date(self, birthday):
        try:
            if birthday != datetime.strptime(birthday, "%Y-%m-%d").strftime('%Y-%m-%d'):
                raise ValueError
            return True
        except ValueError:
            return False


class User(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    dob = models.CharField(max_length=10, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    userMgr = UserManager()
