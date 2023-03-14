import json


class SetDecoder(json.JSONDecoder):
    def __init__(self, list_type=set, **kwargs):
        json.JSONDecoder.__init__(self, **kwargs)
        # Use the custom JSONArray
        self.parse_array = self.JSONArray
        # Use the python implemenation of the scanner
        self.scan_once = json.scanner.py_make_scanner(self)
        self.list_type = list_type

    def JSONArray(self, s_and_end, scan_once, **kwargs):
        values, end = json.decoder.JSONArray(s_and_end, scan_once, **kwargs)
        return self.list_type(values), end


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set) or isinstance(obj, frozenset):
            return list(obj)
        return json.JSONEncoder.default(self, obj)
