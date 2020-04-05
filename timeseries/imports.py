import fastai2
import fastcore
import torch
from fastai2.imports import *
from fastai2.data.all import *
from fastai2.vision.data import get_grid
import pprint
import psutil
import scipy as sp

PATH = Path(os.getcwd())
device = 'cuda' if torch.cuda.is_available() else 'cpu'
