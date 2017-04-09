"""
Passthrough controller that connects to the Gym environent
"""

import os
import sys
import socket
import random
import logging

sys.path.insert(0, '.')
from connection import Socket

def le_get_functions(args):
    """
    This function has to be called le_get_functions

    args is the rest of the command-line options passed in on -le_options to MAME after the name of the module
    
    It should return a 3-tuple of the function to call with updates on framebuffer, the function to be called to get
    agent input, and the function to be called when MAME shuts down.  Any of them can be set to None if you don't
    want to be notified of that event type.
    """
    state = PassthroughController(args)
    return (state.start, state.update, state.get_actions, state.should_we_reset, state.shutdown, None)



class PassthroughController(object):
    class CommunicationError(Exception):
        """
        Generic error that happened somewhere in our communications
        """


    def __init__(self, args):
        # some useful constants
        left_arrow_button = Button(0)       
        right_arrow_button = Button(1)
        up_arrow_button = Button(2)     
        down_arrow_button = Button(3)

        button1 = Button(4)
        button2 = Button(5)
        button3 = Button(6)
        button4 = Button(7)
        button5 = Button(8)
        button6 = Button(9)

        self.ArrowKeyNames = {
            'left' : left_arrow_button, 
            'right' : right_arrow_button, 
            'up' : up_arrow_button, 
            'down' : down_arrow_button
        }
        self.ActionKeyNames = {'button1' : button1, 'button2' : button2, 'button3' : button3, 'button4' : button4,
                               'button5' : button5, 'button6' : button6}

        self.coin_button = Button(10)
        self.player1_button = Button(11)

        self.arrow_buttons = (left_arrow_button, right_arrow_button, up_arrow_button, down_arrow_button)
        self.action_buttons = (button1, button2, button3, button4, button5, button6)
        self.game_buttons = self.arrow_buttons + self.action_buttons
        self.misc_buttons = (self.coin_button, self.player1_button)
        self.button_order = self.arrow_buttons + self.action_buttons + self.misc_buttons
        self.actions = [False for i in self.button_order]

        self.update_count = 0
        self.current_score = 0
        self.frames_to_skip = 0

        self.we_should_reset = False

        # connect to the Gym driver
        socket_path = args
        self.controller_connection = Socket()
        self.controller_connection.start_client(socket_path)


    def start(self, game_name, width, height, buttons_used):
        self.game_name = game_name
        self.width = width
        self.height = height
        self.buttons_used = buttons_used

        # send dimensions
        self.controller_connection.send("size %sx%s\n" % (self.width, self.height))
        self.controller_connection.send("used %s\n" % (''.join('1' if used else '0' for used in self.buttons_used)))

        
    def update(self, score, game_over, video_frame):
        """
        This will be called with a score if available (otherwise zero), and the video_frame
        
        The frame can be converted to a nice PIL image with something like

        frame = PIL.Image.frombuffer("RGBA",(self.width, self.height),video_frame,'raw', ("BGRA",0,1))

        Return the number of frames you want skipped before being called again.  Due to conversions, it's much faster
        to return a positive number here than to keep an internal count on when to react
        """        
        self.update_count += 1
        self.current_score = score
        self.game_over = game_over

        frames_to_skip = self.frames_to_skip - 1
        if frames_to_skip < 0:
            frames_to_skip = 0
            self.controller_connection.send('updt %d\n%d\n%s' % (score, game_over, video_frame))
            self.receive_message()
        else:
            self.frames_to_skip = 0
        return frames_to_skip #number of frames you want to skip


    
    def get_actions(self):
        """
        This will also be called on each frame update to get the actions of the agent.

        A list of the state of the 12 buttons should be returned
        """

        # update each button. Each one has a 3% chance of toggling
        self.actions = []
        for button, used in zip(self.button_order, self.buttons_used):
            if used:
                self.actions.append(button.state)
            else:
                self.actions.append(False)
        return self.actions

    
    def should_we_reset(self):
        # act like a one-time switch
        if self.we_should_reset:
            self.we_should_reset = False
            return True
        return False

    def shutdown(self):
        """
        This will be called when MAME shuts down
        """

        # tell Gym that we are shutting down

        self.controller_connection.send("quit")
        self.controller_connection.destroy()
    
    
    def receive_message(self):
        try:
            # we have a fixed command size of the first four characters
            # should do for now

            command = self.controller_connection.receive_bytes(4).lower()
            if command == 'inpt':
                # we have the size of the space. Initialise buffer and observation space
                input_description = self.controller_connection.receive_until_character('\n').strip()
                self._set_input(input_description)
            elif command == 'rest':
                # reset
                self.we_should_reset = True
            elif command == 'skip':
                skip_description = self.controller_connection.receive_until_character('\n').strip()
                self.frames_to_skip = int(skip_description.strip())
            elif command == 'quit':
                logging.info("We've been told to quit")
                self.controller_connection.destroy()
                sys.exit(0)                
        except self.CommunicationError as error:
            logging.error("Something went wrong talking to mamele: %s" % error)
            self.shutdown()


    def _set_input(self, description):
        """
        Set the state of our buttons to that described in the input
        """

        # input is just a 1 or a 0 for each of the buttons in the button order

        if not len(description) == 12:
            raise self.CommunicationError("input should pass through the state of the 12 buttons. We saw '%s' of length '%s'" % (description, len(description)))

        for index, state in enumerate(description):
            if state == '1':
                self.button_order[index].press()
            else:
                self.button_order[index].release()



class Button(object):
    """
    Button class
    """
    def __init__(self, number_in_c):
        self.state = False
        self.last_state = False
        self.number_in_c = number_in_c

    def press(self):
        self.state = True

    def release(self):
        self.state = False

    def toggle(self):
        self.state = not self.state

    def changed(self):
        return self.state != self.last_state

    def tick(self):
        self.last_state = self.state
