
##
Website: http://zombiesimu.run
Deployed on: AWS EC2
Date: 3/21/2017
Author: Calvin Nguyen
GitHub: https://github.com/calvnguyen/ZombieApocalypse

## Technologies
1. Django, Python (for Back-End)
2. Bootstrap/jquery/ HTML/CSS/JavaScript (Front-End)
3. SQLite3 DB for database

## Server 
 Ubuntu 16.04
 nginx version: nginx/1.10.0 (Ubuntu)

### Implementation details

* Database Tables
    1. We have used Django models to create database
    2. We have created two models one is for game(Game) another for simulation(SimulationResult).

* Game creation
    When users submit form:
       1. If form is valid then create a game and corresponding SimulationResult which initially goes to 0th iteration.
       2. When there are user input errors, request for form resubmission where error message(s) will be displayed

* Simulation details
    1. There is a Planet class which holds list of creatures( Human, PanickedHuman, Zombie and FightingHuman classes )
    2. Game is initialized with zombie/human/fighting population calculated from user inputs
    3. Fighting humans are selected randomly at 5% of zombies
    4. These creates are placed at different locations on the planet. Planet is considered a 2-D plane
    5. Humans are infected when within a radius of zombie locations. They can randomly be infected or panic.
    6. Humans can panic and run witin the same radius, which then become Panicked Humans. This is randomized.
    7. Zombies can be killed by Fighting Human
    8. Fighting Human (aka super hero) can turn Panicked Human into normal again and also kill zombies
    9. In each iteration, move all these creatures with a time of 1 quanta
   10. All constants values like speed, creature size are defined in consts.py
   11. At the end of each simulation simulation state is dump into the file
   12. When page is refreshed Planet is created from file


* Move detail
    1. Zombie can move in any 8 directions
    2. Other creatures move in one direction with their speed
    3. In the movement, their co-ordinates change from (x0,y0) to (x1,y1)

* Form Handling:
   * GameForm logic is based on standard Django ModelForm (which verifies for positive integer value)
   * Added a cleanup function which verifies whether user have entered % between 0 and 100 or not


* Graph plotting
    Graph is displayed using Google graph library using Google Charts, which takes list of values and draw them.

* Creature Plotting:
    All creatures are drawn in HTML5 canvas using fillRect and fillColor methods

* UI Details
    1. index.html: Used for home page where form is displayed
    2. about.html: Used for about page
    3. simulation.html: Simulation result is displayed and page will be reloaded/refreshed with next iteration  at the end of the drawing
    4. simulation_end.html: Display final simulation result with chart and creatures state in the table format.

