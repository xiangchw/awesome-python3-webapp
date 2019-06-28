# -*- coding: utf-8 -*-

import config_default

class Dict(dict):
    """
    创建一个可以通过点语法访问key的字典.
    """
    def __init__(self , names=(), values=(), **kw):
        super(Dict, self).__init__(kw)
        for k, v in zip(names, values):
                self[k] = v

    #   通过.访问dict的key.
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s' " % key)

    def __setattr__(self, key, value):
        self[key] = value

def merge(defaults , override):
    """
    合并两个dict
    """
    r = {}
    for k,v in defaults.items():
        #   如果k既在defaults中,又在override中
        if k in override:
            #   如果该值是字典,则递归合并.
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            #   如果该值是单个值,则取override中的值.
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

def toDict(d):
    """
    将普通字典转为可以由点语法访问的Dict字典.
    """
    D = Dict()
    for k,v in d.items():
        #   三元表达式,处理value也为字典的情况.
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D

try:
    import config_override
    configs = merge(config_default.configs, config_override.configs)
except ImportError:
    pass

configs = toDict(configs)