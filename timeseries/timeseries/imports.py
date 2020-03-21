import fastai2
import torch
from fastai2.imports import *
import pprint
import psutil

PATH = Path(os.getcwd())
device = 'cuda' if torch.cuda.is_available() else 'cpu'
