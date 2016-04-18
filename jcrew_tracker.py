#!/usr/bin/env python

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from getpass import getuser
from pushbullet import Pushbullet
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from socket import gethostname

import argparse
import json
import logging
import os
import smtplib
import sys
import urllib2


class JCrewTracker(object):
  EMAIL_SUBJECT = 'J.Crew Polo Changes'
  EMAIL_USER = '%s@%s' % (getuser(), gethostname())
  STATE_FILE = 'jcrew.state'
  THUMB_SIZE = 75
  URL = 'https://www.jcrew.com/mens_category/polostees/shortsleevepolos/' \
        'PRDOVR~91918/91918.jsp'
  USER_AGENT = ('Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36')
  USER_AGENTS_FILE = '/opt/user_agents.txt'

  def __init__(self, email_from=EMAIL_USER, email_subject=EMAIL_SUBJECT,
      email_to=EMAIL_USER, http_path=None, pushbullet_api_key=None,
      pushbullet_api_keyfile=None, size=None, smtp='localhost',
      state_file=STATE_FILE, thumb_size=THUMB_SIZE, url=URL,
      user_agent=USER_AGENT, user_agent_file=USER_AGENTS_FILE, www_path=None):
    self.http_path = http_path
    self.item_code = url.split('/')[-1].split('.')[0]
    self.thumb_size = thumb_size
    self.image_url = ('https://i.s-jcrew.com/is/image/jcrew/%s_%s?$pdp_tn%s$' %
        (self.item_code, '%s', self.thumb_size))
    self.msg = MIMEMultipart()
    self.msg['From'] = email_from
    self.msg['To'] = email_to
    self.msg['Subject'] = email_subject
    self.path = os.path.dirname(os.path.realpath(__file__))
    self.pushbullet_api_key = pushbullet_api_key
    self.pushbullet_api_keyfile = pushbullet_api_keyfile
    self.size = size
    self.state_file = os.path.join(self.path, state_file)
    self.url = url
    self.user_agent = user_agent
    self.user_agent_file = user_agent_file
    self.www_path = www_path

  def DownloadFile(self, url):
    logging.info('Downloading %s', url)
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', self.user_agent)]
    data = opener.open(url).read()
    logging.info('Downloaded %d bytes', len(data))
    return data

  def GetAttributeData(self, driver, tag, name):
    logging.debug('Getting attributes for tag: %s name: %s', tag, name)
    return driver.execute_script("""
      var elements = document.getElementsByTagName("%s");
      var attribs = [];
      for (var i = 0; i < elements.length; i++) {
        item = elements[i].attributes.getNamedItem("%s");
        if (item) { attribs.push(item.nodeValue); }
      }
      return attribs;
      """ % (tag, name))

  def GetChanges(self, colors, state):
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

  def GetColors(self, driver, wait):
    colors = {}
    logging.info('Getting active colors')
    search = wait.until(EC.presence_of_element_located((By.ID, 'data-size')))
    driver.find_element_by_name('LARGE').click()
    search = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, 'selected')))
    data = self.GetAttributeData(driver, 'div', 'data-color')
    for color in sorted(data):
      driver.find_element_by_name(color).click()
      colors[color] = {
        'name': self.GetNodeText(driver, 'color-name').title(),
        'price': float(self.GetNodeText(driver, 'full-price').split('$')[-1]),
        'active': True}
      logging.info('Active color %s: %s', color, str(colors[color]))
    return colors

  def GetNodeText(self, driver, class_name):
    logging.debug('Getting node text for class %s', class_name)
    return driver.execute_script(('return document.getElementsByClassName'
        '("%s")[0].childNodes[0].nodeValue') % class_name)

  def GetPushbulletAPIKey(self):
    if not self.pushbullet_api_key:
      if not self.pushbullet_api_keyfile:
        logging.info('No Pushbullet API Key or Keyfile, not using Pushbullet')
        return
      logging.debug('Getting pushbullet api key')
      try:
        with open(self.pushbullet_api_keyfile) as f:
          self.pushbullet_api_key = f.read().replace('\n', '')
      except:
        self.pushbullet_api_key = None

  def GetSizes(self, driver):
    logging.info('Getting current sizes')
    sizes = self.GetAttributeData(driver, 'div', 'data-size')
    if self.size not in [x.lower() for x in sizes]:
      logging.error('%s not available: %s', self.size, str(sizes))
      exit(1)

  def GetState(self):
    logging.info('Loading state from %s', self.state_file)
    try:
      with open(self.state_file) as f:
        return json.load(f)
    except:
      return {}

  def GetURL(self, driver, wait):
    logging.info('Loading %s', self.url)
    driver.get(self.url)
    search = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, 'color-box')))

  def GetUserAgent(self):
    if not os.path.exists(self.user_agent_file):
      self.user_agent = self.USER_AGENT
    logging.info('Loading user agent from %s', self.user_agent_file)
    try:
      with open(self.user_agent_file) as f:
        for line in f:
          self.user_agent = line.split(' ', 1)[1].rstrip()
    except:
      logging.error('Error getting user agent, using default')
      self.user_agent = self.USER_AGENT
    logging.info('Using User-Agent: %s', self.user_agent)

  def SendAlert(self, html):
    self.SendEmail(html)
    self.GetPushbulletAPIKey()
    try:
      pb = Pushbullet(self.pushbullet_api_key)
      if self.pushbullet_api_key:
        logging.info('Sending Pushbullet alert')
        push = pb.push_link(self.msg['Subject'], self.url)
    except:
      pass

  def SendEmail(self, html):
    logging.info('Sending email alert')
    envelope_to = [self.msg['To']]
    self.msg.attach( MIMEText(html, 'html') )
    try:
      smtp = smtplib.SMTP('localhost')
      smtp.sendmail(self.msg['From'], envelope_to, self.msg.as_string() )
      smtp.close()
    except:
      pass

  def ShirtDiv(self, color, colors, state):
    now = ''
    if color in state:
      diff = colors[color]['price'] - state[color]['price']
    else:
      diff = 0
    h2 = []
    css = {
      'a':     'style="text-decoration:none;color:#000;"',
      'div':  ('style="float:left;padding:1em;text-align:center;width:%spx;"'
         % self.thumb_size),
      'price': 'style="margin:0.2em 0 0.2em 0;font-size:0.9em;color:#13c;"',
      'color': 'style="margin:0.2em 0 0.2em 0;font-size:0.9em;color:#888;"',
      'name':  'style="margin:0.2em 0 0 0;font-size:1em;color:#000;"'}
    h = [
      '%s<div %s>' % ((' ' * 6), css['div']),
      '%s<a href="%s" %s>' % ((' ' * 8), self.url, css['a']),
      ('%s<img src="%s/%s.jpg" height="%s" width="%s" />' %
        ((' ' * 10), self.http_path, color, self.thumb_size, self.thumb_size))]
    if diff != 0:
      now = 'now: '
      delta = '+'
      if diff < 0:
        delta = '-'
        diff = abs(diff)
      h2.append('%s<p %s>was $%.2f</p>' %
        ((' ' * 10), css['price'], float(state[color]['price'])))
      h2.append('%s<p %s>(%s$%.2f)</p>' %
        ((' ' * 10), css['price'], delta, diff))
    h.append('%s<p %s>%s$%.2f</p>' %
        ((' ' * 10), css['price'], now, float(colors[color]['price'])))
    h.extend(h2)
    h.extend(['%s<p %s>%s</p>' % ((' ' * 10), css['color'], color),
      '%s<p %s>%s</p>' %
        ((' ' * 10), css['name'], colors[color]['name'].title()),
      '%s</a>' % (' ' * 8),
      '%s</div>' % (' ' * 6)])
    return h

  def UpdateDivs(self, driver):
    logging.info('Updating divs')
    driver.execute_script('''
      var attribs;
      var allDivs = document.getElementsByTagName("div");
      var ids = ["data-size", "data-color"];
      var item;
      for (var i = 0; i < allDivs.length; i++) {
        attribs = allDivs[i].attributes;
        for (var j = 0; j <= 1; j++) {
          item = attribs.getNamedItem(ids[j]);
          if (item) {
            allDivs[i].setAttribute("id", ids[j]);
            allDivs[i].setAttribute("name", item.nodeValue);
          }
        }
      }''')

  def WriteHTML(self, changes, colors, state):
    html = ''
    css = {'a':    'style="text-decoration:none;color:#000;"',
           'div':  'style="overflow:auto;"',
           'h1':   'style="font-size:1.5em;margin:0;"',
           'html': 'style="font-family:arial;font-size:12px;"'}
    logging.info('Generating HTML')
    h = ['<html %s>' % css['html'],
         '%s<body>' % (' ' * 2)]
    for change_type, change_list in sorted(changes.iteritems()):
      if not change_list:
        continue
      h.extend(['%s<h1 %s>%s:</h1>' % ((' ' * 4), css['h1'], change_type),
                '%s<div %s>' % ((' ' * 4), css['div'])])
      col = 0
      for color in change_list:
        if col > 0 and col % 4 == 0:
          h.extend(['%s</div>' % (' ' * 4),
                    '%s<div %s>' % ((' ' * 4), css['div'])])
        h.extend(self.ShirtDiv(color, colors, state))
        path = os.path.join(self.www_path, '%s.jpg' % color)
        if not os.path.exists(path):
          img = self.DownloadFile(self.image_url % color)
          with open(path, 'w') as f:
            f.write(img)
        col += 1
      h.append('%s</div>' % (' ' * 4))
    h.extend(['%s</body>' % (' ' * 2), '</html>', ''])
    html = '\n'.join(h)
    path = os.path.join(self.www_path, 'jcrew.html')
    with open(path, 'w') as f:
      f.write(html)
    logging.info('Wrote HTML file')
    return html

  def WriteState(self, colors):
    logging.info('Saving state')
    with open(self.state_file, 'w') as f:
      f.write(json.dumps(colors, indent=2, sort_keys=True) + '\n')

  def Run(self):
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = self.GetUserAgent()
    driver = webdriver.PhantomJS(
        desired_capabilities=dcap, service_args=['--ssl-protocol=any'],
        service_log_path=os.path.devnull)
    wait = WebDriverWait(driver, 10)
    driver.set_window_size(1120, 550)
    try:
      self.GetURL(driver, wait)
      self.GetSizes(driver)
      self.UpdateDivs(driver)
      colors = self.GetColors(driver, wait)
    finally:
      driver.quit()

    state = self.GetState()
    changes = self.GetChanges(colors, state)
    if sum([len(v) for k,v in changes.iteritems()]) > 0:
      html = self.WriteHTML(changes, colors, state)
      self.SendAlert(html)
    else:
      logging.info('No changes to alert on.')
    self.WriteState(colors)


def Main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-f', '--email_from', default=JCrewTracker.EMAIL_USER,
      help='Email address to send email as.')
  parser.add_argument('-s', '--email_subject',
      default=JCrewTracker.EMAIL_SUBJECT, help='The email subject.')
  parser.add_argument('-t', '--email_to', default=JCrewTracker.EMAIL_USER,
      help='Email address to send email to.')
  parser.add_argument('--debug', '-d', action='store_true',
      help='Enable debugging logging.')
  parser.add_argument('--http_path', required=True,
      help='http:// path where images can be retrieved.')
  parser.add_argument('--pushbullet_api_key', default=None,
      help='Pushbullet API key to use.')
  parser.add_argument('--pushbullet_api_keyfile', default=None,
      help='File storing Pushbullet API key.')
  parser.add_argument('--size', default='large',
      help='Size of clothing to look for.')
  parser.add_argument('--smtp', default='localhost',
      help='SMTP server to use for sending emails.')
  parser.add_argument('--state_file', default='jcrew.state',
      help='File to store state in between runs.')
  parser.add_argument('--thumb_size', default=JCrewTracker.THUMB_SIZE,
      help='Size of thumbnails to display.')
  parser.add_argument('--url', default=('https://www.jcrew.com/mens_category/'
      'polostees/shortsleevepolos/PRDOVR~91918/91918.jsp'),
      help='URL to check against.')
  parser.add_argument('--user_agent', default=JCrewTracker.USER_AGENT,
      help='User-Agent string to use.')
  parser.add_argument('--user_agent_file', default=('/opt/user_agents.txt'),
      help='File to read user-agent from ($timestamp $string format).')
  parser.add_argument('--verbose', '-v', action='store_true')
  parser.add_argument('--www_path', default='',
      help='Local path to store http images.')
  args = parser.parse_args()

  logFormatter = logging.Formatter('%(levelname).1s%(asctime)s '
      '%(lineno)s]  %(message)s', datefmt='%H:%M:%S')
  rootLogger = logging.getLogger()
  rootLogger.setLevel(logging.INFO)
  fileHandler = logging.FileHandler('/var/log/jcrew_tracker.log')
  fileHandler.setFormatter(logFormatter)
  rootLogger.addHandler(fileHandler)

  if args.verbose:
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(logging.INFO)
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)
  if args.debug:
    consoleHandler.setLevel(logging.DEBUG)
    rootLogger.setLevel(logging.DEBUG)

  jcrew = JCrewTracker(args.email_from, args.email_subject, args.email_to,
      args.http_path, args.pushbullet_api_key, args.pushbullet_api_keyfile,
      args.size, args.smtp, args.state_file, args.thumb_size, args.url,
      args.user_agent, args.user_agent_file, args.www_path)
  jcrew.Run()


if __name__ == '__main__':
  Main()
