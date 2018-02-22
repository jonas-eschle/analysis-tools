from unittest import TestCase
from collections import OrderedDict
import copy

import numpy as np

from analysis.utils.config import recursive_dict_copy

target1 = OrderedDict([('a', OrderedDict([('aa', {'aaa': 111, 'aab': OrderedDict([('aaba', 1121)])})])),
                       ('b', {'ba': np.random.normal(10)})])


def test_recursive_dict_copy():
    test_odict1 = recursive_dict_copy(x=copy.deepcopy(target1))

    assert test_odict1 == target1
    assert test_odict1 is not target1
    assert test_odict1['a'] == target1['a']
    assert test_odict1['a'] is not target1['a']
    assert test_odict1['b']['ba'] is target1['b']['ba']
