'''
Original Author: Serge Kruk
Original Version: https://github.com/sgkruk/Apress-AI/blob/master/cutting_stock.py

Updated by: Emad Ehsan
Updated by: Jakub Jabůrek
'''
from ortools.linear_solver import pywraplp
from math import ceil
import json
from read_lengths import get_data
import typer


'''
return a printable value
'''
def SolVal(x):
  if type(x) is not list:
    return 0 if x is None \
      else x if isinstance(x,(int,float)) \
           else x.SolutionValue() if x.Integer() is False \
                else int(x.SolutionValue())
  elif type(x) is list:
    return [SolVal(e) for e in x]


def ObjVal(x):
  return x.Objective().Value()


def solve_model(demands, parent_width=100, verbose=False, level=0):
  '''
      demands = [
          [1, 3], # [quantity, width]
          [3, 5],
          ...
      ]

      parent_width = integer
  '''
  num_orders = len(demands)

  if level == 0:
    solver = pywraplp.Solver.CreateSolver('SAT')
    solver.SetNumThreads(1)
  else:
    solver = pywraplp.Solver('CBC', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)

  k,b  = bounds(demands, parent_width, verbose)

  # array of boolean declared as int, if y[i] is 1, 
  # then y[i] Big roll is used, else it was not used
  y = [ solver.IntVar(0, 1, f'y_{i}') for i in range(k[1]) ] 

  # x[i][j] = 3 means that small-roll width specified by i-th order
  # must be cut from j-th order, 3 tmies 
  x = [[solver.IntVar(0, b[i], f'x_{i}_{j}') for j in range(k[1])] \
      for i in range(num_orders)]
  
  unused_widths = [ solver.NumVar(0, parent_width, f'w_{j}') \
      for j in range(k[1]) ] 
  
  # will contain the number of big rolls used
  nb = solver.IntVar(k[0], k[1], 'nb')

  # consntraint: demand fullfilment
  for i in range(num_orders):  
    # small rolls from i-th order must be as many in quantity
    # as specified by the i-th order
    solver.Add(sum(x[i][j] for j in range(k[1])) == demands[i][0]) 

  # constraint: max size limit
  for j in range(k[1]):
    # total width of small rolls cut from j-th big roll, 
    # must not exceed big rolls width
    solver.Add( \
        sum(demands[i][1]*x[i][j] for i in range(num_orders)) \
        <= parent_width*y[j] \
      ) 

    # width of j-th big roll - total width of all orders cut from j-th roll
    # must be equal to unused_widths[j]
    # So, we are saying that assign unused_widths[j] the remaining width of j'th big roll
    solver.Add(parent_width*y[j] - sum(demands[i][1]*x[i][j] for i in range(num_orders)) == unused_widths[j])

    '''
    Book Author's note from page 201:
    [the following constraint]  breaks the symmetry of multiple solutions that are equivalent 
    for our purposes: any permutation of the rolls. These permutations, and there are K! of 
    them, cause most solvers to spend an exorbitant time solving. With this constraint, we 
    tell the solver to prefer those permutations with more cuts in roll j than in roll j + 1. 
    The reader is encouraged to solve a medium-sized problem with and without this 
    symmetry-breaking constraint. I have seen problems take 48 hours to solve without the 
    constraint and 48 minutes with. Of course, for problems that are solved in seconds, the 
    constraint will not help; it may even hinder. But who cares if a cutting stock instance 
    solves in two or in three seconds? We care much more about the difference between two 
    minutes and three hours, which is what this constraint is meant to address
    '''
    if j < k[1]-1: # k1 = total big rolls
      # total small rolls of i-th order cut from j-th big roll must be >=
      # totall small rolls of i-th order cut from j+1-th big roll
      solver.Add(sum(x[i][j] for i in range(num_orders)) >= sum(x[i][j+1] for i in range(num_orders)))

  # find & assign to nb, the number of big rolls used
  solver.Add(nb == solver.Sum(y[j] for j in range(k[1])))

  ''' 
    minimize total big rolls used
    let's say we have y = [1, 0, 1]
    here, total big rolls used are 2. 0-th and 2nd. 1st one is not used. So we want our model to use the 
    earlier rolls first. i.e. y = [1, 1, 0]. 
    The trick to do this is to define the cost of using each next roll to be higher. So the model would be
    forced to used the initial rolls, when available, instead of the next rolls.

    So instead of Minimize ( Sum of y ) or Minimize( Sum([1,1,0]) )
    we Minimize( Sum([1*1, 1*2, 1*3]) )
  ''' 

  '''
  Book Author's note from page 201:

  There are alternative objective functions. For example, we could have minimized the sum of the waste. This makes
  sense, especially if the demand constraint is formulated as an inequality. Then minimizing the sum of waste will
  spend more CPU cycles trying to find more efficient patterns that over-satisfy demand. This is especially good if
  the demand widths recur regularly and storing cut rolls in inventory to satisfy future demand is possible. Note that
  the running time will grow quickly with such an objective function
  '''

  if level == 2:
    Cost = solver.Sum((
      ((j + 2) * y[j]) +
      ((j + 1) * (1 - (unused_widths[j] / parent_width)))
    ) for j in range(k[1]))
  elif level == 1:
    Cost = solver.Sum((
      (y[j] * (j + 1) * parent_width) +
      (parent_width - unused_widths[j] + (parent_width - y[j] * parent_width))
    ) for j in range(k[1]))
  else:
    Cost = solver.Sum(((j + 1) * y[j]) for j in range(k[1]))

  solver.Minimize(Cost)

  status = solver.Solve()
  numRollsUsed = SolVal(nb)

  return status, \
    numRollsUsed, \
    rolls(numRollsUsed, SolVal(x), SolVal(unused_widths), demands), \
    SolVal(unused_widths)


def bounds(demands, parent_width=100, verbose=False):
  '''
  b = [sum of widths of individual small rolls of each order]
  T = local var. stores sum of widths of adjecent small-rolls. When the width reaches 100%, T is set to 0 again.
  k = [k0, k1], k0 = minimum big-rolls requierd, k1: number of big rolls that can be consumed / cut from
  TT = local var. stores sum of widths of of all small-rolls. At the end, will be used to estimate lower bound of big-rolls
  '''
  num_orders = len(demands)
  b = []
  T = 0
  k = [0,1]
  TT = 0

  for i in range(num_orders):
    # q = quantity, w = width; of i-th order
    quantity, width = demands[i][0], demands[i][1]
    # TODO Verify: why min of quantity, parent_width/width?
    # assumes widths to be entered as percentage
    # int(round(parent_width/demands[i][1])) will always be >= 1, because widths of small rolls can't exceed parent_width (which is width of big roll)
    # b.append( min(demands[i][0], int(round(parent_width / demands[i][1]))) )
    b.append( min(quantity, int(round(parent_width / width))) )

    # if total width of this i-th order + previous order's leftover (T) is less than parent_width
    # it's fine. Cut it.
    if T + quantity*width <= parent_width:
      T, TT = T + quantity*width, TT + quantity*width
    # else, the width exceeds, so we have to cut only as much as we can cut from parent_width width of the big roll
    else:
      while quantity:
        if T + width <= parent_width:
          T, TT, quantity = T + width, TT + width, quantity-1
        else:
          k[1],T = k[1]+1, 0 # use next roll (k[1] += 1)
  k[0] = int(round(TT/parent_width+0.5))

  if verbose:
    print('k', k)
    print('b', b)

  return k, b


'''
  nb: array of number of rolls to cut, of each order
  
  w: 
  demands: [
    [quantity, width],
    [quantity, width],
    [quantity, width],
  ]
'''
def rolls(nb, x, w, demands):
  consumed_big_rolls = []
  num_orders = len(x) 
  # go over first row (1st order)
  # this row contains the list of all the big rolls available, and if this 1st (0-th) order
  # is cut from any big roll, that big roll's index would contain a number > 0
  for j in range(len(x[0])):
    # w[j]: width of j-th big roll 
    # int(x[i][j]) * [demands[i][1]] width of all i-th order's small rolls that are to be cut from j-th big roll 
    RR = [ abs(w[j])] + [ int(x[i][j])*[demands[i][1]] for i in range(num_orders) \
                    if x[i][j] > 0 ] # if i-th order has some cuts from j-th order, x[i][j] would be > 0
    consumed_big_rolls.append(RR)

  return consumed_big_rolls


'''
checks if all small roll widths (demands) smaller than parent roll's width
'''
def checkWidths(demands, parent_width):
  for quantity, width in demands:
    if width > parent_width:
      print(f'Small roll width {width} is greater than parent rolls width {parent_width}. Exiting')
      return False
  return True


'''
    params
        child_rolls: 
            list of lists, each containing quantity & width of rod / roll to be cut
            e.g.: [ [quantity, width], [quantity, width], ...]
        parent_rolls: 
            list of lists, each containing quantity & width of rod / roll to cut from
            e.g.: [ [quantity, width], [quantity, width], ...]
'''
def StockCutter1D(child_rolls, parent_rolls, verbose=False, level=0):
  # at the moment, only parent one width of parent rolls is supported
  # quantity of parent rolls is calculated by algorithm, so user supplied quantity doesn't matter?
  # TODO: or we can check and tell the user the user when parent roll quantity is insufficient
  parent_width = parent_rolls[0][1]

  if not checkWidths(demands=child_rolls, parent_width=parent_width):
    return []

  if verbose:
    print('child_rolls:', child_rolls)
    print('parent_rolls:', parent_rolls)

  status, numRollsUsed, consumed_big_rolls, unused_roll_widths = \
            solve_model(demands=child_rolls, parent_width=parent_width, verbose=verbose, level=level)

  # convert the format of output of solve_model to be exactly same as solve_large_model
  if verbose:
    print('consumed_big_rolls before adjustment: ', consumed_big_rolls)
  new_consumed_big_rolls = []
  for big_roll in consumed_big_rolls:
    if len(big_roll) < 2:
      # sometimes the solve_model return a solution that contanis an extra [0.0] entry for big roll
      consumed_big_rolls.remove(big_roll)
      continue
    unused_width = round(big_roll[0])
    subrolls = []
    for subitem in big_roll[1:]:
      if isinstance(subitem, list):
        # if it's a list, concatenate with the other lists, to make a single list for this big_roll
        subrolls = subrolls + subitem
      else:
        # if it's an integer, add it to the list
        subrolls.append(subitem)
    new_consumed_big_rolls.append([unused_width, subrolls])
  if verbose:
    print('consumed_big_rolls after adjustment: ', new_consumed_big_rolls)
  consumed_big_rolls = new_consumed_big_rolls

  numRollsUsed = len(consumed_big_rolls)

  STATUS_NAME = ['OPTIMAL',
    'FEASIBLE',
    'INFEASIBLE',
    'UNBOUNDED',
    'ABNORMAL',
    'NOT_SOLVED'
  ]

  output = {
      "statusName": STATUS_NAME[status],
      "numSolutions": 1,
      "numUniqueSolutions": 1,
      "numRollsUsed": numRollsUsed,
      "solutions": [consumed_big_rolls] # unique solutions
  }

  if verbose:
    print('numRollsUsed', numRollsUsed)
    print('Status:', output['statusName'])
    print('Solutions found :', output['numSolutions'])
    print('Unique solutions: ', output['numUniqueSolutions'])

  return json.dumps(output)


if __name__ == '__main__':
  app = typer.Typer()

  def main(infile_name: str = typer.Argument(...), level: int = typer.Option(0), verbose: bool = typer.Option(False)):
    read_data = get_data(infile_name)
    roll_width = int(read_data[0])
    child_rolls = list(map(lambda r: (r[0], int(r[1])), read_data[1]))

    parent_rolls = [[1000, roll_width]] # 1000 doesn't matter, it is not used at the moment

    consumed_big_rolls = StockCutter1D(child_rolls, parent_rolls, verbose=verbose, level=level)
    typer.echo(f"{consumed_big_rolls}")

  typer.run(main)
