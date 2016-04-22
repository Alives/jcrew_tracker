#!/usr/bin/env python
"""Build HTML files given specific inputs."""

import logging
import os
import urllib2


class HTMLBuilder(object):
  """Build an HTML document."""
  def __init__(self, headers, http_path, thumb_size, url, www_path):
    item_code = url.split('/')[-1].split('.')[0]
    self.headers = headers
    self.http_path = http_path
    self.thumb_size = thumb_size
    self.image_url = ('https://i.s-jcrew.com/is/image/jcrew/%s_%s?$pdp_tn%s$' %
                      (item_code, '%s', thumb_size))
    self.url = url
    self.www_path = www_path

  def download_file(path, url):
    """Download a file using HTTP(S).

    Args:
        path: (string) The filepath to save the data to.
        url: (string) The URL to download.

    Returns:
        None.
    """
    if os.path.exists(path):
      return
    logging.info('Downloading %s', url)
    opener = urllib2.build_opener()
    opener.addheaders = []
    for header, value in self.headers.iteritems():
      if value:
        opener.addheaders.append((header, value))
    data = opener.open(url).read()
    with open(path, 'w') as f_img:
      f_img.write(data)
    logging.info('Downloaded %d bytes', len(data))

  def item_div(self, color, colors, state):
    """Build a specific item's div with an image, price data, and name.

    Args:
        color: (string) The specific color for this div.
        colors: (dict) All the colors data including name and price.
        state: (dict) The previous run's colors data for calculating price
          changes.

    Returns:
        A string of the html for the specific item's div.
    """
    now = ''
    price_html = []
    css = {
        'a':     'style="text-decoration:none;color:#000;"',
        'div':  ('style="float:left;padding:1em;text-align:center;width:%spx;"'
                 % self.thumb_size),
        'price': 'style="margin:0.2em 0 0.2em 0;font-size:0.9em;color:#13c;"',
        'color': 'style="margin:0.2em 0 0.2em 0;font-size:0.9em;color:#888;"',
        'name':  'style="margin:0.2em 0 0 0;font-size:1em;color:#000;"'}
    html = [
        '%s<div %s>' % ((' ' * 6), css['div']),
        '%s<a href="%s" %s>' % ((' ' * 8), self.url, css['a']),
        ('%s<img src="%s/%s.jpg" height="%s" width="%s" />' %
         ((' ' * 10), self.http_path, color, self.thumb_size,
          self.thumb_size))]

    # Download the image.
    path = os.path.join(self.www_path, '%s.jpg' % color)
    download_file(path, self.image_url % color)

    if color in state:
      diff = colors[color]['price'] - state[color]['price']
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
                ((' ' * 10), css['price'], now, float(colors[color]['price'])))
    html.extend(price_html)
    html.extend([
        '%s<p %s>%s</p>' % ((' ' * 10), css['color'], color),
        '%s<p %s>%s</p>' %
        ((' ' * 10), css['name'], colors[color]['name'].title()),
        '%s</a>' % (' ' * 8),
        '%s</div>' % (' ' * 6)])

    return '\n'.join(html)

  def write_html(self, changes, colors, state, html_filename='jcrew.html'):
    """Write the entire HTML document.

    Args:
        changes: (dict) All the items that changed since the last run.
        colors: (dict) All the colors data including name and price.
        state: (dict) The previous run's colors data for calculating price
          changes.
        html_filename: (string) The filename to write the document to.

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
        html.append(self.item_div(color, colors, state))
        col += 1
      html.append('%s</div>' % (' ' * 4))
    html.extend(['%s</body>' % (' ' * 2), '</html>', ''])
    html_text = '\n'.join(html)
    path = os.path.join(self.www_path, html_filename)
    with open(path, 'w') as f_html:
      f_html.write(html_text)
    logging.info('Wrote HTML file')
    return html_text
