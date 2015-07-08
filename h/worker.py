import json, traceback, requests, types
from collections import defaultdict
from h_util import HypothesisStream

h_stream = HypothesisStream()

h_stream.make_indexes()