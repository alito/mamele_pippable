#!/usr/bin/env python
#coding: utf8

"""
Gentle keymasher
"""
from __future__ import print_function, absolute_import, division, unicode_literals

import sys, os
import random

import mamele

DefaultNumberOfGames = 3
ChangeActionPeriod = 10

def main(args):

    from argparse import ArgumentParser
    
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", dest="verbosity", default=0, action="count",
                      help="Verbosity.  Invoke many times for higher verbosity")
    parser.add_argument("-n", "--number", dest="number_of_games", default=DefaultNumberOfGames, type=int,
                      help="Number of games to play. 0 for neverending. Default: %(default)s")    
    parser.add_argument("game", nargs=1,
                      help="Game to play")

    parameters = parser.parse_args(args)

    game = mamele.Mamele(parameters.game[0], watch=True)

    action_sets = game.get_minimal_action_set()

    count = 0
    change_probability = 1. / ChangeActionPeriod
    action = [random.choice(action_set[1]) for action_set in action_sets]

    
    frame_count = 0
    while True:
        if game.is_game_over():
            count += 1
            if parameters.number_of_games and count > parameters.number_of_games:
                break
            game.restart_game()

        frame_count += 1

        if random.random() < change_probability:
            action = [random.choice(action_set[1]) for action_set in action_sets]
        game.act(action)

    game.quit()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
