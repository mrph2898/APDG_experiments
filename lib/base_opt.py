from typing import List, Optional
from autograd import grad, jacobian, elementwise_grad
import numpy as np
import matplotlib.pyplot as plt
import sys, os
from tqdm import tqdm
import math
import scipy 
from scipy import linalg
from numpy import linalg as LA
from pyblas.level1 import dnrm2
import sys

sys.path.append("../")

import numpy as np
from datetime import datetime
from typing import Optional
from .problems import BaseSaddle
import lib.utils as ut


class BaseSaddleOpt(object):
    """
    Base class for saddle-point algorithms.
    Parameters
    ----------
    oracle: BaseSmoothSaddleOracle
        Oracle corresponding to the objective function.
    z_0: ArrayPair
        Initial guess
    tolerance: Optional[float]
        Accuracy required for stopping criteria.
    stopping_criteria: Optional[str]
        Str specifying stopping criteria. Supported values:
        "grad_rel": terminate if ||f'(x_k)||^2 / ||f'(x_0)||^2 <= eps
        "grad_abs": terminate if ||f'(x_k)||^2 <= eps
    logger: Optional[Logger]
        Stores the history of the method during its iterations.
    """
    def __init__(
        self,
        problem: BaseSaddle,
        x0: np.ndarray, 
        y0: np.ndarray,
        eps: float,
        stopping_criteria: Optional[str],
        params: dict
    ):
        self.problem = problem
        self.x = x0.copy()
        self.y = y0.copy()

        if hasattr(self.problem, 'proj_x'):
            self.proj_x = self.problem.proj_x
        else:
            self.proj_x = lambda x: x

        if hasattr(self.problem, 'proj_y'):
            self.proj_y = self.problem.proj_y
        else:
            self.proj_y = lambda y: y

        self.x = self.proj_x(self.x)
        self.y = self.proj_y(self.y)

        # self._name = None
        self.params = params
        
        self.eps = eps
        if stopping_criteria == 'grad_rel':
            self.stopping_criteria = self.stopping_criteria_grad_relative
        elif stopping_criteria == 'grad_abs':
            self.stopping_criteria = self.stopping_criteria_grad_absolute
        elif stopping_criteria == 'loss':
            self.stopping_criteria = self.stopping_criteria_loss
        elif stopping_criteria == None:
            self.stopping_criteria = self.stopping_criteria_none
        else:
            raise ValueError('Unknown stopping criteria type: "{}"' \
                             .format(stopping_criteria))

    def __call__(self, 
            max_iter: int, 
            max_time: float = None,
            verbose=1
           ):
        """
        Run the method for no more that max_iter iterations and max_time seconds.
        Parameters
        ----------
        max_iter: int
            Maximum number of iterations.
        max_time: float
            Maximum time (in seconds).
        """
        self.grad_norm_0 = np.sqrt(self.x.dot(self.x)**2 + self.y.dot(self.y)**2)
   
        if max_time is None:
            max_time = +np.inf
        if not hasattr(self, 'time'):
            self.time = 0.
        
        self.loss = [self.problem.loss(self.x, self.y)]
        self.all_metrics = {"gap": [],
                            "grad_norm": [],
                            "func": []
                           }
        metrics, _ = ut.metrics(self.problem, self.x, self.y)
        for metric, val in metrics.items():
            self.all_metrics[metric].append(val)
        self.x_hist, self.y_hist = [self.x], [self.y]

        bar = range(max_iter)
        if verbose > 0:
            bar = tqdm(bar, desc=self.__class__.__name__)
            
        self._absolute_time = datetime.now()
        
        for iter_count in bar:
            self.iter_count = iter_count
            if self.time > max_time:
                break
            self._update_time()
            
            self.step()
            self.x = self.proj_x(self.x)
            self.y = self.proj_y(self.y)
            lo = self.problem.loss(self.x, self.y)
            metrics, _ = ut.metrics(self.problem, self.x, self.y)
            for metric, val in metrics.items():
                self.all_metrics[metric].append(val)
            self.loss.append(lo)  
            self.x_hist.append(self.x)
            self.y_hist.append(self.y)            
            
            if self.stopping_criteria():
                break
        return self.loss, self.x_hist, self.y_hist
                

    def _update_time(self):
        now = datetime.now()
        self.time += (now - self._absolute_time).total_seconds()
        self._absolute_time = now

    def step(self):
        raise NotImplementedError('step() not implemented!')

    def stopping_criteria_grad_relative(self):
        return self.grad.dot(self.grad) <= self.eps * self.grad_norm_0 ** 2

    def stopping_criteria_grad_absolute(self):
        return self.grad.dot(self.grad) <= self.eps
    
    def stopping_criteria_loss(self):
        return self.problem.loss(self.x, self.y) <= self.eps

    def stopping_criteria_none(self):
        return False
