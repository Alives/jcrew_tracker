#!/usr/bin/env python
"""Check J. Crew items for changes."""

from browser import Browser
from html_builder import HTMLBuilder
from state import State

import alert
import argparse
import json
import logging
import os
import sys


EMAIL_SUBJECT = 'J. Crew Polo Changes'
HTML_FILENAME = 'jcrew.html'
STATE_FILENAME = 'jcrew.state'
THUMB_SIZE = 75
TRIES = 4
URL = ('https://www.jcrew.com/mens_category/polostees/shortsleevepolos/'
       'PRDOVR~91918/91918.jsp')
USER_AGENT = ('Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36')


def get_changes(colors, state):
  """Compare the current and previous runs to see if anything changed.

  Args:
      colors: (dict) The current colors data.
      state: (dict) The previous run's colors data.

  Returns:
      A dict containing the color codes that 1) are new, 2) are no longer
      available, and 3) have price changes.
  """
  changes = {'New Items': [], 'Removed Items': [], 'Price Changes': []}
  for color, data in sorted(colors.iteritems()):
    if color in state and state[color]['active']:
      logging.info('Color %s (%s) is already known to be active', color,
                   data['name'])
    else:
      if color in state and not state[color]['active']:
        logging.info('Color %s (%s) is now active', color, data['name'])
      elif color not in state:
        logging.info('Color %s (%s) is new', color, data['name'])
      changes['New Items'].append(color)
  for color, data in sorted(state.iteritems()):
    if color not in colors:
      if not data['active']:
        logging.debug('Color %s (%s) already inactive', color, data['name'])
        continue
      logging.info('Color %s (%s) is now inactive (removed)', color,
                   data['name'])
      changes['Removed Items'].append(color)
      data['active'] = False
      colors[color] = data
      continue
    if data['price'] != colors[color]['price']:
      logging.info('Color %s (%s) changed price to $%.2f', color,
                   data['name'], data['price'])
      changes['Price Changes'].append(color)
  return changes


def get_user_agent(user_agent_file):
  """Get the most recent user agent from a file on disk if it exists.

  Args:
      user_agent_file: (string) Filepath of file containing user agent strings.

  Returns:
      A string contiaining the current user-agent.
  """
  user_agent = ''
  if os.path.exists(user_agent_file):
    logging.info('Loading user agent from %s', user_agent_file)
    try:
      with open(user_agent_file) as f_user_agent:
        ua = json.load(f_user_agent)
      user_agent = ua['latest']['agent']
    except IOError, e_msg:
      logging.error('Error getting user agent: %s, using default', e_msg)
      user_agent = USER_AGENT
    logging.info('Using User-Agent: %s', user_agent)
    return user_agent


def parse_args():
  """Handle all the argument parsing.

  Returns:
      An argparse object.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-f', '--email_from', required=True,
      help='Email address to send email as.')
  parser.add_argument(
      '-s', '--subject', default=EMAIL_SUBJECT, help='The email subject.')
  parser.add_argument(
      '-t', '--email_to', required=True, help='Email address to send email to.')
  parser.add_argument(
      '--debug', '-d', action='store_true', help='Enable debugging logging.')
  parser.add_argument(
      '--html_filename', default=HTML_FILENAME,
      help='Filename of the html document to write for debugging.')
  parser.add_argument(
      '--http_path', required=True,
      help='http:// path where images can be retrieved.')
  parser.add_argument(
      '--logfile', default='/var/log/jcrew_tracker.log',
      help='Where to write the logfile.')
  parser.add_argument(
      '--pushbullet_api_key', default=None, help='Pushbullet API key to use.')
  parser.add_argument(
      '--pushbullet_api_keyfile', default=None,
      help='File storing Pushbullet API key.')
  parser.add_argument(
      '--size', default='large', help='Size of clothing to look for.')
  parser.add_argument(
      '--smtp', default='localhost',
      help='SMTP server to use for sending emails.')
  parser.add_argument(
      '--state_file', default=STATE_FILENAME,
      help='File to store state in between runs.')
  parser.add_argument(
      '--thumb_size', default=THUMB_SIZE, help='Size of thumbnails to display.')
  parser.add_argument('--url', default=URL, help='URL to check against.')
  parser.add_argument(
      '--user_agent', default=USER_AGENT, help='User-Agent string to use.')
  parser.add_argument(
      '--user_agent_file', default='/opt/user_agents.json',
      help='File to read user-agent from with "$timestamp $string" format.')
  parser.add_argument('--verbose', '-v', action='store_true')
  parser.add_argument(
      '--www_path', default='', help='Local path to store http images.')
  return parser.parse_args()


def main():
  """The main function."""

  args = parse_args()

  if args.debug:
    log_level = logging.DEBUG
  else:
    log_level = logging.INFO

  log_formatter = logging.Formatter(
      '%(levelname).1s%(asctime)s %(lineno)s]  %(message)s', datefmt='%H:%M:%S')
  root_logger = logging.getLogger()
  root_logger.setLevel(log_level)
  file_handler = logging.FileHandler(args.logfile)
  file_handler.setFormatter(log_formatter)
  root_logger.addHandler(file_handler)

  if args.verbose:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

  if args.user_agent == USER_AGENT:
    user_agent = get_user_agent(args.user_agent_file)

  headers = {'Referer': args.url, 'User-Agent': user_agent}
  browser = Browser(user_agent)
  builder = HTMLBuilder(headers, args.http_path, args.thumb_size, args.url,
                        args.www_path)
  state = State(args.state_file)

  try:
    browser.get_url(args.url, TRIES)
    browser.check_size(args.size)
    browser.update_divs()
    colors = browser.get_colors(args.size)
  finally:
    browser.quit()

  existing_state = state.get_state()
  changes = get_changes(colors, existing_state)
  if sum([len(v) for v in changes.values()]) > 0:
    html = builder.write_html(changes, colors, existing_state,
                              args.html_filename)
    if args.pushbullet_api_key or args.pushbullet_api_keyfile:
      alert.send_alert(args.pushbullet_api_key, args.pushbullet_api_keyfile,
                       args.subject, args.url)
    if args.email_from and args.email_to:
      alert.send_email(args.email_from, args.email_to, html, args.smtp,
                       args.subject)
  else:
    logging.info('No changes to alert on.')
  state.write_state(colors)


if __name__ == '__main__':
  main()
