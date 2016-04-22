#!/usr/bin/env python
"""Load and save objects between runs."""

import json
import logging
import os


class State(object):
  """Read a json file and save current state as json files."""
  def __init__(self, state_file):
    self.path = os.path.dirname(os.path.realpath(__file__))
    self.state_file = os.path.join(self.path, state_file)

  def get_state(self):
    """Read an object from a json encoded file."""
    logging.info('Loading state from %s', self.state_file)
    try:
      with open(self.state_file) as f_state:
        return json.load(f_state)
    except IOError, msg:
      logging.error('Could not read %s: %s', self.state_file, msg)
      return {}

  def write_state(self, state):
    """Write an object to a json file."""
    logging.info('Saving state')
    try:
      with open(self.state_file, 'w') as f_state:
        f_state.write(json.dumps(state, indent=2, sort_keys=True) + '\n')
    except IOError, msg:
      logging.error('Could not write %s: %s', self.state_file, msg)
