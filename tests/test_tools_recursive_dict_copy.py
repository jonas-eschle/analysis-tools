from unittest import TestCase
from collections import OrderedDict
import copy

import numpy as np
import ROOT

from analysis.utils.config import recursive_dict_copy

target1 = OrderedDict([('a', OrderedDict([('aa', {'aaa': 111, 'aab': OrderedDict(
        [('aaba', 1121), ('aabb', ROOT.RooRealVar('name1', 'title1', 3))])})])),
                       ('b', {'ba': np.random.normal(10)})])


def test_recursive_dict_copy():
    target1_copy = copy.deepcopy(target1)
    test_odict1 = recursive_dict_copy(x=target1)

    assert target1_copy == target1
    assert test_odict1 == target1
    assert test_odict1 is not target1
    assert test_odict1['a'] == target1['a']
    assert test_odict1['a'] is not target1['a']
    assert test_odict1['b']['ba'] is target1['b']['ba']
    assert test_odict1['a']['aa']['aab']['aabb'] is target1['a']['aa']['aab']['aabb']
    assert isinstance(test_odict1['a']['aa']['aab'], OrderedDict)
