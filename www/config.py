# -*- coding: utf-8 -*-
from heapq import merge

import config_default

configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass