"""JSON/text helpers used by every skill."""

import json
import os


def read_json(path, what, required=True):
    if not path or not os.path.exists(path):
        if required:
            raise IOError("no %s at %s" % (what, path))
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def rupees(x):
    x = float(x)
    if abs(x - round(x)) < 0.005:
        return "Rs " + "{:,.0f}".format(round(x))
    return "Rs " + "{:,.2f}".format(x)
