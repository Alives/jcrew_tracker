#!/usr/bin/env python
"""Check J. Crew items for changes."""

import argparse
import json
import logging
import os
import re
import smtplib
import sys

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests


INVENTORY_URL = 'https://www.jcrew.com/data/v1/us/products/inventory/91918'
ITEM_URL = ('https://www.jcrew.com/mens_category/polostees/shortsleevepolos/'
            'PRDOVR~91918/91918.jsp')
USER_AGENT = ('Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36')


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


def item_div(color, data, state):
  """Build a specific item's div with an image, price data, and name.

  Args:
      color: (string) The specific color for this div.
      data: (dict) All the colors data including name and price.
      state: (dict) The previous run's colors data for calculating price
        changes.

  Returns:
      A string of the html for the specific item's div.
  """
  now = ''
  price_html = []
  css = {
      'a':     'style="text-decoration:none;color:#000;"',
      'div':  'style="float:left;padding:1em;text-align:center;width:75px;"',
      'price': 'style="margin:0.2em 0 0.2em 0;font-size:0.9em;color:#13c;"',
      'color': 'style="margin:0.2em 0 0.2em 0;font-size:0.9em;color:#888;"',
      'name':  'style="margin:0.2em 0 0 0;font-size:1em;color:#000;"'}
  html = [
      '%s<div %s>' % ((' ' * 6), css['div']),
      '%s<a href="%s" %s>' % ((' ' * 8), ITEM_URL, css['a']),
      ('%s<img src="https://i.s-jcrew.com/is/image/jcrew/91918_%s?'
       '$pdp_tn75$" height="75" width="75" />' % ((' ' * 10), color))]

  if color in state:
    diff = data[color]['price'] - state[color]['price']
  else:
    diff = 0
  if diff != 0:
    now = 'now: '
    delta = '+'
    if diff < 0:
      delta = '-'
      diff = abs(diff)
    price_html.append('%s<p %s>was $%.2f</p>' %
                      ((' ' * 10), css['price'],
                       float(state[color]['price'])))
    price_html.append('%s<p %s>(%s$%.2f)</p>' %
                      ((' ' * 10), css['price'], delta, diff))
  html.append('%s<p %s>%s$%.2f</p>' %
              ((' ' * 10), css['price'], now, float(data[color]['price'])))
  html.extend(price_html)
  html.append('%s<p %s>%s</p>' % ((' ' * 10), css['color'], color))
  if 'quantity' in data[color]:
    html.append('%s<p %s>Quantity: %s</p>' % ((' ' * 10), css['color'],
                                             data[color]['quantity']))
  html.extend([
      '%s<p %s>%s</p>' % ((' ' * 10), css['name'],
                          data[color]['name'].title()),
      '%s</a>' % (' ' * 8),
      '%s</div>' % (' ' * 6)])

  return '\n'.join(html)


def generate_html(changes, data, state):
  """Write the entire HTML document.

  Args:
      changes: (dict) All the items that changed since the last run.
      data: (dict) All the colors data including name and price.
      state: (dict) The previous run's colors data for calculating price
        changes.

  Returns:
      A string of all the html for the new webpage.
  """
  logging.info('Generating HTML')
  css = {'a':    'style="text-decoration:none;color:#000;"',
         'div':  'style="overflow:auto;"',
         'h1':   'style="font-size:1.5em;margin:0;"',
         'html': 'style="font-family:arial;font-size:12px;"'}
  html = ['<html %s>' % css['html'],
          '%s<body>' % (' ' * 2)]
  for change_type, change_list in sorted(changes.iteritems()):
    if not change_list:
      continue
    html.extend(['%s<h1 %s>%s:</h1>' % ((' ' * 4), css['h1'], change_type),
                 '%s<div %s>' % ((' ' * 4), css['div'])])
    col = 0
    for color in change_list:
      if col > 0 and col % 4 == 0:
        html.extend(['%s</div>' % (' ' * 4),
                     '%s<div %s>' % ((' ' * 4), css['div'])])
      html.append(item_div(color, data, state))
      col += 1
    html.append('%s</div>' % (' ' * 4))
  html.extend(['%s</body>' % (' ' * 2), '</html>', ''])
  html_text = '\n'.join(html)
  return html_text
def send_email(email_from, email_to, html):
  logging.info('Sending email alert')
  msg = MIMEMultipart()
  msg['From'] = email_from
  msg['To'] = email_to
  msg['Subject'] = 'J. Crew Polo Changes'
  envelope_to = [x.strip() for x in msg['To'].split(',')]
  msg.attach(MIMEText(html, 'html'))
  try:
    smtp = smtplib.SMTP('localhost')
    smtp.sendmail(msg['From'], envelope_to, msg.as_string())
  finally:
    smtp.close()


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
  user_agent = ''
  if os.path.exists(user_agent_file):
    logging.info('Loading user agent from %s', user_agent_file)
    try:
      with open(user_agent_file) as f_user_agent:
        agent = json.load(f_user_agent)
      user_agent = agent['latest']['agent']
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
      '-t', '--email_to', required=True, help='Email address to send email to.')
  parser.add_argument(
      '--debug', '-d', action='store_true', help='Enable debugging logging.')
  parser.add_argument(
      '--ignore', '-i', nargs='*', help='Ignore space separated color codes.',
      default=[])
  parser.add_argument(
      '--logfile', default='/var/log/jcrew_tracker.log',
      help='Where to write the logfile.')
  parser.add_argument(
      '--size', default='large', help='Size of clothing to look for.')
  parser.add_argument('--verbose', '-v', action='store_true')
  return parser.parse_args()


def get_url(url, user_agent, referer=None):
  logging.info('Loading %s', url)
  if not referer:
    referer = url
  headers = {'Referer': referer, 'User-Agent': user_agent}
  response = requests.get(url, headers=headers)
  return response.text


def extract_json_from_html(html):
  logging.info('Extracting JSON.')
  try:
    json_str = re.findall(r'^\s+var pdpJSON = ({.*});$', html, re.M)[0]
  except IndexError:
    logging.error('Unable to find json in html.')
    exit(1)
  return json.loads(json_str)


def build_sku_list(product_data, inventory_data, size):
  """Combine product and inventory data by sku."""
  data = {}
  inventory = inventory_data['inventory']
  for sku, details in product_data['productDetails']['skus'].iteritems():
    if details['size'] == size.upper():
      color = details['colorCode']
      data[color] = {
          'name': details['colorName'],
          'price': float(details['price']['amount'])
      }
      if 'inStock' in inventory[sku]:
        if not inventory[sku]['inStock']:
          data[color]['active'] = False
      else:
        data[color]['active'] = True
        data[color]['quantity'] = inventory[sku]['quantity']
  return data


def get_jcrew_data(size):
  user_agent = get_user_agent('/opt/user_agents.json')
  html = get_url(ITEM_URL, user_agent)
  product_data = extract_json_from_html(html)
  html = get_url(INVENTORY_URL, user_agent, referer=ITEM_URL)
  inventory_data = json.loads(html)
  return build_sku_list(product_data, inventory_data, size)


def remove_ignored_colors(changes, ignore):
  """Remove ignored colors so they aren't alerted on."""
  for color_code in ignore:
    logging.info('Ignoring alerts for color code %s.', color_code)
    for k in changes.keys():
      if color_code in changes[k]:
        changes[k].remove(color_code)
        logging.info('Removed ignored color code %s from alerts.', color_code)
  return changes


def setup_logging(debug, logfile, verbose):
  """Setup the logging system."""
  if debug:
    log_level = logging.DEBUG
  else:
    log_level = logging.INFO

  log_formatter = logging.Formatter(
      '%(levelname).1s%(asctime)s %(lineno)s]  %(message)s', datefmt='%H:%M:%S')
  root_logger = logging.getLogger()
  root_logger.setLevel(log_level)
  file_handler = logging.FileHandler(logfile)
  file_handler.setFormatter(log_formatter)
  root_logger.addHandler(file_handler)

  if verbose:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)


def main():
  """Main."""
  args = parse_args()
  setup_logging(args.debug, args.logfile, args.verbose)
  state = State('jcrew.state')

  data = get_jcrew_data(args.size)
  if not data:
    logging.error('Nothing in size %s available.', args.size)
  existing_state = state.get_state()
  changes = get_changes(data, existing_state)

  changes = remove_ignored_colors(changes, args.ignore)

  if sum([len(v) for v in changes.values()]) > 0:
    html = generate_html(changes, data, existing_state)
    send_email(args.email_from, args.email_to, html)
  else:
    logging.info('No changes to alert on.')
  state.write_state(data)
  logging.info('Finished.')


if __name__ == '__main__':
  main()
