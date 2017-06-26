import os, sys, logging
import subprocess
import itertools
from collections import defaultdict

import numpy
from PIL import Image

from .connection import Socket


class Mamele(object):
    SwitchesOrder = ['left', 'right', 'up', 'down', 'button1', 'button2', 'button3',
    'button4', 'button5', 'button6', 'coin', 'player1']

    HorizontalDirectionRange = range(2)
    VerticalDirectionRange = range(2,4)
    ButtonsRange = range(4,10)
    MiscellaneousRange = range(10,12)

    ResetFrames = 20 # The reset time is handled on the MAME side, so just skip a little bit here
    CoinToStartFrames = 60 
    StartToLiveFrames = 20 
    PressFrames = 4


    def __init__(self, game_name, watch=False):

        self.game_name = game_name
        self.watch = watch

        # we'll initialise these once we know what we are dealing with
        self.score = None
        self.latest_image_as_string = None
        self.previous_score = self.score = 0
        self.images_size_in_bytes = 0
        self.action_spaces = None
        self.width = None
        self.height = None
        self.game_over = True
        self.resetting = False
        self.buttons_used = None

        self.action_to_description = {}
        self.nothing_pressed = '0' * len(self.SwitchesOrder) # template for the switches to send, all unpressed

        self.mamele_connection = Socket()
        socket_path = self.mamele_connection.start_server()
        self.mame = self._start_mame(game_name, socket_path)

        self.last_received = False

        # wait for mame to connect
        self.mamele_connection.wait_for_connection()

        # we expect the mame module to send the size and the minimal button set
        self.receive_message()
        self.receive_message()


    class CommunicationError(Exception):
        """
        Generic error that happened somewhere in our communications
        """

    def send_message(self, message):
        if not self.last_received:
            # the passthrough only receives once after sendin an update, so avoid the deadlock and 
            # receive the message first
            self.receive_message()

        self.mamele_connection.send(message)
        self.last_received = False


    def receive_message(self):
        try:
            # we have a fixed command size of the first four characters
            # should do for now

            command = self.mamele_connection.receive_bytes(4).lower()
            if command == 'size':
                # we have the size of the space. Initialise buffer and observation space
                size_description = self.mamele_connection.receive_until_character('\n')
                self._initialise_screen(size_description.strip())
            elif command == 'used':
                # get the switches that are used
                switches_used_description = self.mamele_connection.receive_until_character('\n')
                self._initialise_action_space(switches_used_description.strip())
            elif command == 'quit':
                logging.info("Got a quit from the environment")
                self.expected_quit()
            elif command == 'updt':
                # combo update of score and image
                score_description = self.mamele_connection.receive_until_character('\n')
                game_over_description = self.mamele_connection.receive_until_character('\n')
                self.latest_image_as_string = self.mamele_connection.receive_bytes(self.images_size_in_bytes)
                if not self.resetting:
                    # ignore score and game over status while we are resetting
                    self._set_score(score_description.strip())
                    self._set_game_over(game_over_description.strip())
                self.last_received = True


        except self.CommunicationError as error:
            logging.error("Something went wrong talking to mamele: %s" % error)
            self.unexpected_quit()


    def get_screen_dimensions(self):
        return self.width, self.height

    def get_minimal_action_set(self):
        return self.action_spaces

    def is_game_over(self):
        return self.game_over

    def get_screen_rgb(self):
        # we get the data as BGRA. Convert it to RGB in numpy
        image = Image.frombuffer("RGBA",(self.width, self.height), self.latest_image_as_string,'raw', "RGBA", 0, 1)
        arrayed = numpy.asarray(image)
        return arrayed[:, :, [2, 1, 0]]

    def restart_game(self):
        # Restart the game
        # If we are in game over, just insert a coin and press start player 1
        # otherwise reset the machine, insert a coin, press player 1

        self.resetting = True
        if not self.last_received:
            # make sure it's waiting for us
            self.receive_message()
        if not self.game_over:
            self.send_message('rest')
            self.skip(self.ResetFrames)
        self.insert_coin()
        self.skip(self.PressFrames)
        self.press_nothing()
        self.skip(self.CoinToStartFrames)        
        self.start_player1()
        self.skip(self.PressFrames)
        self.press_nothing()
        self.skip(self.StartToLiveFrames)
        self.game_over = False
        self.score = self.previous_score = 0
        self.resetting = False


    def act(self, action):
        """
        The `action` parameter describes what we do in each action space
        """
        self.send_message("inpt %s\n" % self.action_to_description[tuple(action)])
        self.receive_message()
        return self.score - self.previous_score

    def expected_quit(self):
        # mame-side expected quit
        self.mamele_connection.destroy()

    def unexpected_quit(self):
        # mame-side hang up unexpectedly

        self.mamele_connection.destroy()
        # now bail
        raise IOError("Could not connect to our module in mamele land")


    def quit(self):
        self.send_message('quit')

    def insert_coin(self):
        self.send_message("inpt %s\n" % self.action_to_description['coin'])

    def start_player1(self):
        self.send_message("inpt %s\n" % self.action_to_description['player1'])

    def press_nothing(self):
        self.send_message("inpt %s\n" % self.nothing_pressed)

    def skip(self, frames):
        self.send_message('skip %d\n' % frames)        


    def _initialise_screen(self, description):
        # we get sent something like 400x300 (widthxheight)

        parts = description.split('x')
        if len(parts) != 2:
            raise self.CommunicationError("Didn't get a size in width x height format")

        try:
            self.width = int(parts[0])
            self.height = int(parts[1])
            logging.info("Screen size: %sx%s" % (self.width, self.height))
        except ValueError as error:
            raise self.CommunicationError("Either width or height weren't integers")

        self.images_size_in_bytes = self.height * self.width * 4 # comes as BGRA


    def _initialise_action_space(self, switches_used_description):

        # We get a 0 or a 1 for each of the switches sent back. eg '111111000011'
        # Treat each of the directions separately, and each separate from the buttons

        if len(switches_used_description) != len(self.SwitchesOrder):
            raise IOError("Got a description of the switches used of an unexpected length. Expected %s, got %s (%s)" % (len(self.SwitchesOrder), switches_used_description, len(switches_used_description)))

        spaces = defaultdict(lambda: list(['noop']))

        self.buttons_used = []
        for index, (used, switch_name) in enumerate(zip(switches_used_description, self.SwitchesOrder)):
            if used == '1':
                if index in self.HorizontalDirectionRange:
                    spaces['horizontal'].append(switch_name)
                elif index in self.VerticalDirectionRange:
                    spaces['vertical'].append(switch_name)
                elif index in self.ButtonsRange:
                    spaces[switch_name].append(switch_name)
                # The other two miscellaneous ones are coin insertion and start of player 1
                # We'll handle those 

        action_spaces = []
        for space_name in ['horizontal', 'vertical'] + [self.SwitchesOrder[index] for index in self.ButtonsRange]:
            if space_name in spaces:
                action_spaces.append((space_name, spaces[space_name]))

        # we'll expect an action for each of the spaces from the client-side
        self.action_spaces = action_spaces

        self.generate_switch_mapping()


    def generate_switch_mapping(self):
        """
        Pre-generate all switch configurations mapping to what we send back
        """
        SwitchIndex = {}
        for index, switch in enumerate(self.SwitchesOrder):
            SwitchIndex[switch] = index


        number_of_switches = len(self.SwitchesOrder)

        coin_button = SwitchIndex['coin']
        player1_button = SwitchIndex['player1']
        self.action_to_description['coin'] = ''.join('0' if index != coin_button else '1' for index in range(number_of_switches))
        self.action_to_description['player1'] = ''.join('0' if index != player1_button else '1' for index in range(number_of_switches))


        # iterate over all our action spaces and generate a description for each one
        all_spaces = [action_space[1] for action_space in self.action_spaces]
        for action in itertools.product(*all_spaces):
            switches = set()

            for component in action:
                if component != 'noop':
                    switches.add(SwitchIndex[component])

            # create the description
            self.action_to_description[action] = ''.join('1' if index in switches else '0' for index in range(number_of_switches))


    def _set_score(self, description):
        self.previous_score = self.score
        self.score = int(description)

    def _set_game_over(self, description):
        # we only set game over to True here
        if description == '1':
            self.game_over = True


    def _start_mame(self, game, socket_path):

        this_directory = os.path.realpath(os.path.dirname(__file__))
        passthrough_module = os.path.join(this_directory, 'passthrough')

        # mame is one down, the python bindings are three down
        mame_binary = os.path.join(this_directory, 'mamele_real', 'mame64')
        description_directory = os.path.join(this_directory, 'mamele_real', 'learning_environment')
        roms_directory = os.path.join(os.path.expanduser("~"), '.le', 'roms')
        if not os.path.isdir(roms_directory):
            raise ValueError("'%s' is not a directory. Put your roms there" % roms_directory)            
        python_bindings = os.path.join(this_directory, 'mamele_real', 'learning_environment', 'example_agents', 'pythonbinding.so')

        command = [mame_binary, game, '-nowriteconfig', '-noreadconfig', '-window'] 
        if not self.watch:
            command.extend('-nothrottle -noswitchres -video none -nole_show -sound none'.split())
        command.extend('-noautosave -frameskip 0 -skip_gameinfo -noautoframeskip -use_le -le_library'.split())
        command.extend([python_bindings, '-rompath', roms_directory, '-le_datapath', description_directory, '-le_options'])

        # le_options is one parameter, the python bindings of mamele split it into the module name,
        # and the rest. That rest is passed to the module which can do with it as it pleases
        command.append("%s %s" % (passthrough_module, socket_path))
        process = subprocess.Popen(command, stderr=subprocess.STDOUT, close_fds=True)

        return process
