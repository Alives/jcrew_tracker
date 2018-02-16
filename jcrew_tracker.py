#!/usr/bin/env python
"""Check J. Crew items for changes."""

import argparse
import datetime
import json
import logging
import os
import socket
import smtplib
import sys
import time

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests


INVENTORY_URL = 'https://www.jcrew.com/data/v1/us/products/inventory/91918'
ITEM_URL = ('https://www.jcrew.com/mens_category/polostees/shortsleevepolos/'
            'PRDOVR~91918/91918.jsp')
PRODUCT_DATA_URL = ('https://www.jcrew.com/data/v1/US/3446/products/91918/c/'
                    'mens_category/polostees/shortsleevepolos')
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
    if colors[color]['active'] and color in state and state[color]['active']:
      logging.info('Color %s (%s) is already known to be active', color,
                   data['name'])
    elif colors[color]['active']:
      if color in state and not state[color]['active']:
        logging.info('Color %s (%s) is now active', color, data['name'])
      elif color not in state:
        logging.info('Color %s (%s) is new', color, data['name'])
      changes['New Items'].append(color)
  for color, data in sorted(state.iteritems()):
    if color not in colors or not colors[color]['active']:
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
      '--graphite', '-g', action='store_true', help='Also write to graphite.')
  parser.add_argument(
      '--ignore', '-i', nargs='*', help='Ignore space separated color codes.',
      default=[])
  parser.add_argument(
      '--logfile', default='/var/log/cron/jcrew_tracker.log',
      help='Where to write the logfile.')
  parser.add_argument(
      '--size', default='large', help='Size of clothing to look for.')
  parser.add_argument('--verbose', '-v', action='store_true')
  return parser.parse_args()


def get_url(url, user_agent, referer=None):
  """Get contents from a given URL."""
  logging.info('Loading %s', url)
  if not referer:
    referer = url
  headers = {'Referer': referer, 'User-Agent': user_agent}
  try:
    response = requests.get(url, headers=headers)
    return response.text
  except requests.exceptions.ConnectionError:
    logging.debug('Connection Error.')
  return ''


def get_product_data(size):
  """Get JSON info and extract relevant data."""
  data = {}
  inventory_data = ''
  user_agent = get_user_agent('/opt/user_agents.json')
  for _ in xrange(5):
    content = get_url(INVENTORY_URL, user_agent, referer=ITEM_URL)
    try:
      inventory_data = json.loads(content)
    except ValueError:
      time.sleep(5)
      continue
    break
  if not inventory_data:
    logging.debug('Couldn\'t get inventory data after 4 tries.')
    sys.exit(1)
  content = get_url(PRODUCT_DATA_URL, user_agent, referer=ITEM_URL)
  product_data = json.loads(content)
  for color, sku in product_data['sizesMap'][size.upper()].iteritems():
    try:
      p_d = product_data['skus'][sku]
    except KeyError:
      logging.debug('sku %s (color %s) not in product_data', sku, color)
      continue
    try:
      i_d = inventory_data['inventory'][sku]
    except KeyError:
      logging.debug('sku %s (color %s) not in inventory_data', sku, color)
      i_d = {}
    data[color] = {'name': p_d['colorName']}
    listprice = float(p_d['listPrice']['amount'])
    price = float(p_d['price']['amount'])
    if listprice > price:
      data[color]['price'] = price
    else:
      data[color]['price'] = listprice
    if 'quantity' in i_d.keys():
      data[color]['quantity'] = i_d['quantity']
      data[color]['active'] = True
    else:
      data[color]['active'] = False
  return data


def remove_ignored_colors(changes, ignore):
  """Remove ignored colors so they aren't alerted on."""
  for color_code in ignore:
    logging.info('Ignoring alerts for color code %s.', color_code)
    for k in changes.keys():
      if color_code in changes[k]:
        changes[k].remove(color_code)
        logging.info('Removed ignored color code %s from alerts.', color_code)
  return changes


def write_graphite(data, prefix='jcrew_quantity', server='127.0.0.1',
                   port=2003):
  """Write quantity data to graphite for monitoring."""
  entries = []
  now = int(datetime.datetime.now().strftime('%s'))
  sock = socket.socket()
  sock.settimeout(5)
  sock.connect((server, port))
  for color, info in data.iteritems():
    if not info['active']:
      continue
    color_name = '%s_%s' % (color, info['name'].replace(' ', '_').title())
    msg = '%s.%s %d %d.' % (prefix, color_name, info['quantity'], now)
    entries.append(msg)
    logging.info('Sending "%s" to %s:%d', msg, server, port)
  sock.sendall('\n'.join(entries) + '\n')
  sock.close()


def setup_logging(logfile, verbose):
  """Setup the logging system."""
  if verbose:
    log_level = logging.DEBUG
  else:
    log_level = logging.ERROR

  log_formatter = logging.Formatter(
      '%(levelname).1s%(asctime)s %(lineno)s]  %(message)s', datefmt='%H:%M:%S')
  root_logger = logging.getLogger()
  root_logger.setLevel(logging.INFO)
  file_handler = logging.FileHandler(logfile)
  file_handler.setFormatter(log_formatter)
  root_logger.addHandler(file_handler)

  console_handler = logging.StreamHandler(sys.stdout)
  console_handler.setLevel(log_level)
  console_handler.setFormatter(log_formatter)
  root_logger.addHandler(console_handler)


def main():
  """Main."""
  args = parse_args()
  setup_logging(args.logfile, args.verbose)
  state = State('jcrew.state')
  now = int(datetime.datetime.now().strftime('%s'))
  state_age = os.path.getmtime(state.state_file)
  if (now - state_age) > (60 * 60 * 24):
    logging.error('jcrew.state was modified over 24 hrs ago. '
                  'Something is wrong.')

  data = get_product_data(args.size)
  if not data:
    logging.error('Nothing in size %s available.', args.size)
  if args.graphite:
    write_graphite(data)
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
