#!/usr/bin/env python
"""Send pushbullet and email alerts."""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import logging
import pushbullet
import smtplib


def get_api_key(api_key, keyfile):
  """Get a pushbullet api key from a text file.

  Args:
      api_key: (string) pushbullet api key.
      api_keyfile: (string) filename of file containing api key.

  Returns: String of the api key from the file or the key originally passed.
  """
  if not api_key:
    if not keyfile:
      logging.info('No Pushbullet API Key or Keyfile, not using Pushbullet')
      return
    logging.debug('Getting pushbullet api key')
    try:
      with open(keyfile) as f_pbf:
        api_key = f_pbf.read().replace('\n', '')
    except IOError, e_msg:
      api_key = None
      logging.error('Unable to read pushbullet api keyfile %s: %s', keyfile,
                    e_msg)
    logging.debug('Pushbullet api key is %s', api_key)
  return api_key


def send_alert(api_key, keyfile, subject, url):
  """Send a pushbullet alert."""
  api_key = get_api_key(api_key, keyfile)
  try:
    pushb = pushbullet.Pushbullet(api_key)
    if api_key:
      logging.info('Sending Pushbullet alert')
      pushb.push_link(subject, url)
  except pushbullet.PushError, e_msg:
    logging.info('Error sending Pushbullet alert: %s', e_msg)


def send_email(email_from, email_to, html, smtp, subject):
  """Send an email."""
  logging.info('Sending email alert')
  msg = MIMEMultipart()
  msg['From'] = email_from
  msg['To'] = email_to
  msg['Subject'] = subject
  envelope_to = [msg['To']]
  msg.attach(MIMEText(html, 'html'))
  try:
    smtp = smtplib.SMTP(smtp)
    smtp.sendmail(msg['From'], envelope_to, msg.as_string())
  finally:
    smtp.close()
