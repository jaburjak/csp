import pathlib
from typing import List
import re
from math import ceil

""" Reads a file of numbers and returns a tuple of the first number and a list of (count, number) pairs."""
def get_data(infile: str) -> tuple[float, List[float]]:
    _p = pathlib.Path(infile)
    input_text = _p.read_text()

    numbers = [ceil(float(n)) for n in re.findall(r'[0-9.]+', _p.read_text())]

    roll_width = numbers[0]
    numbers = numbers[1:]

    quan = []
    nr = []

    for n in numbers:
        if n not in nr and n != 0:
            quan.append(numbers.count(n))
            nr.append(n)

    return (roll_width, list(zip(quan,nr)))
