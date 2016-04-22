#!/usr/bin/env python

import jcrew_tracker
import unittest

class Test(unittest.TestCase):
  @classmethod
  def setUp(self):
    self.jt = jcrew_tracker

  def test_get_changes_NewItems(self):
    colors = {'a': {'active': True, 'price': 5, 'name': 'a'},
              'b': {'active': True, 'price': 5, 'name': 'b'},
              'c': {'active': True, 'price': 5, 'name': 'c'}}
    state = {'a': {'active': True, 'price': 5, 'name': 'a'},
             'b': {'active': False, 'price': 5, 'name': 'b'}}
    changes = self.jt.get_changes(colors, state)
    self.assertDictEqual(
      {'New Items': ['b', 'c'], 'Price Changes': [], 'Removed Items': []},
      changes)

  def test_get_changes_RemovedItems(self):
    colors = {'a': {'active': True, 'price': 5, 'name': 'a'}}
    state = {'a': {'active': True, 'price': 5, 'name': 'a'},
             'b': {'active': True, 'price': 5, 'name': 'b'},
             'c': {'active': False, 'price': 5, 'name': 'c'}}
    changes = self.jt.get_changes(colors, state)
    self.assertDictEqual(
      {'New Items': [], 'Price Changes': [], 'Removed Items': ['b']},
      changes)

  def test_get_changes_PriceChangedItems(self):
    colors = {'a': {'active': True, 'price': 5, 'name': 'a'},
              'b': {'active': True, 'price': 0, 'name': 'b'}}
    state = {'a': {'active': True, 'price': 0, 'name': 'a'},
             'b': {'active': True, 'price': 5, 'name': 'b'}}
    changes = self.jt.get_changes(colors, state)
    self.assertDictEqual(
      {'New Items': [], 'Price Changes': ['a', 'b'], 'Removed Items': []},
      changes)

  def test_get_changes_AllChanges(self):
    colors = {'a': {'active': True, 'price': 5, 'name': 'a'},
              'b': {'active': True, 'price': 0, 'name': 'b'},
              'c': {'active': True, 'price': 0, 'name': 'c'},
              'd': {'active': True, 'price': 0, 'name': 'd'}}
    state = {'a': {'active': True, 'price': 0, 'name': 'a'},
             'b': {'active': True, 'price': 5, 'name': 'b'},
             'c': {'active': False, 'price': 0, 'name': 'c'},
             'e': {'active': True, 'price': 5, 'name': 'e'}}
    changes = self.jt.get_changes(colors, state)
    self.assertDictEqual(
      {'New Items': ['c', 'd'], 'Price Changes': ['a', 'b'],
       'Removed Items': ['e']}, changes)


if __name__ == '__main__':
   unittest.main()
