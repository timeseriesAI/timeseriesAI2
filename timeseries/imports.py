import fastai2
import fastcore
import torch
from fastai2.imports import *
import pprint
import psutil
import scipy as sp

PATH = Path(os.getcwd())
device = 'cuda' if torch.cuda.is_available() else 'cpu'
