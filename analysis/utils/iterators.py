#!/usr/bin/env python
# =============================================================================
# @file   iterators.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   09.07.2013
# =============================================================================
"""Various iterators for python sequences."""
from __future__ import print_function, division, absolute_import


def pairwise(iterable):
    """Split sequence in pairs of consecutive elements.

        s -> (s0, s1), (s1, s2), (s2, s3), ...

    Arguments:
        iterable (sequence): Sequence to iterate on.

    Yields:
        tuple: Pairs of consecutive elements.

    """
    import itertools
    # pylint: disable=C0103
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)


def chunks(iterable, chunk_size):
    """Yield successive chunk_size-sized chunks from a sequence.

    Arguments:
        iterable (sequence): Sequence to iterate on.
        chunk_size (int): Size of the chunks.

    Yields:
        sequence: chunk_size-sized chunk of ``iterable``.

    """
    for index in xrange(0, len(iterable), int(chunk_size)):
        yield iterable[index:index+int(chunk_size)]

# EOF
