# Cutting Stock Problem

Cutting Stock Problem (CSP) deals with planning the cutting of items (rods / sheets) from given stock items (which are usually of fixed size).

This implementation of CSP tries to answer \
_How to minimize number of stock items used while cutting customer order?_ \
While doing so, it also caters \
_How to cut the stock for customer orders so that waste is minimum?_ \
The OR Tools also helps us in calculating the number of possible solutions for your problem. So in addition, we can also compute \
_In how many ways can we cut given order from fixed size stock?_

## Quick start

Install [Pipenv](https://pipenv.pypa.io/en/latest/), if not already installed.

Clone this project and install packages:

```sh
$ git clone git@github.com:jaburjak/csp.git
$ cd csp
$ pipenv install

# activate env
$ pipenv shell
```

## Usage

To solve your Cutting Stock Problem, run the `stock_cutter_1d.py` file:

```sh
(csp) $ python csp/stock_cutter_1d.py infile.txt
```

Output:

```json
{
    "statusName": "OPTIMAL",
    "numSolutions": 1,
    "numUniqueSolutions": 1,
    "numRollsUsed": 5,
    "solutions": [
    	[
    		// [unused_stock_width, [item_width...]]
            [0, [3400, 500, 500, 500, 220, 220, 220, 220, 220]],
            [80, [500, 500, 500, 500, 220, 1850, 1850]],
            [10, [220, 220, 1850, 1850, 1850]],
            [90, [3400, 220, 220, 220, 1850]],
            [880, [3400, 500, 500, 500, 220]]
        ]
    ]
}
```

### Using the input file

The first number in the input file must be the stock width followed by requested item widths. Numbers should be separated by whitespace.

## Libraries
* [Google OR-Tools](https://developers.google.com/optimization)

## Limitations
* Works with integers only. If you have some values that have decimal part, you can multiply all of your inputs with some number that will make them integers (or close estimation).

## Acknowledgements

This project is a fork of [Emad Ehsan’s CSP solver](https://github.com/emadehsan/csp), which in turn builds on the code of [Serge Kruk](https://github.com/sgkruk/Apress-AI/).
