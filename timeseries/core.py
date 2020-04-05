# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/001_core.ipynb (unless otherwise specified).

__all__ = ['TSTensor', 'ToTSTensor', 'NumpyTensor', 'ToNumpyTensor', 'TSTensorBlock', 'TSDataLoaders', 'PytorchDataset',
           'NumpyDatasets', 'TSDatasets', 'NumpyDataLoader', 'show_tuple', 'TSDataLoader', 'add_ds', 'add_test',
           'add_unlabeled']

# Cell
from fastcore.all import *
from fastai2.torch_imports import *
from fastai2.torch_core import *
from fastai2.data.all import *
from fastai2.vision.data import get_grid

# Cell
from .imports import *
from .utils import *

# Cell
class TSTensor(TensorBase):
    '''Returns a tensor of at least 2 dims of type torch.float32 and class TSTensor'''
    def __new__(cls, o, dtype=torch.float32, **kwargs):
        res = ToType(dtype)(To2DPlusTensor(o))
        res.__class__ = cls
        res._meta = kwargs
        return res

    @property
    def vars(self): return self.shape[-2]

    @property
    def length(self): return self.shape[-1]

    def __getitem__(self, idx):
        res = super().__getitem__(idx)
        return retain_type(res, self)

    def __repr__(self):
        if self.ndim >= 3:   return f'TSTensor(samples:{self.shape[-3]}, vars:{self.shape[-2]}, len:{self.shape[-1]})'
        elif self.ndim == 2: return f'TSTensor(vars:{self.shape[-2]}, len:{self.shape[-1]})'
        elif self.ndim == 1: return f'TSTensor(len:{self.shape[-1]})'
        else: return f'TSTensor(float)'

    def show(self, ax=None, ctx=None, title=None, title_color='black', **kwargs):
        ax = ifnone(ax,ctx)
        if ax is None: fig, ax = plt.subplots(**kwargs)
        ax.plot(self.T)
        ax.axis(xmin=0, xmax=self.shape[-1] - 1)
        ax.set_title(title, weight='bold', color=title_color)
        plt.tight_layout()
        return ax

@Transform
def ToTSTensor(o:np.ndarray, dtype=torch.float32, **kwargs):
    """ Transforms input to tensor of dtype torch.float32"""
    return TSTensor(o, dtype=dtype, **kwargs)

# Cell
class NumpyTensor(TensorBase):

    def __new__(cls, o, **kwargs):
        res = ToTensor(o)
        res.__class__ = cls
        res._meta = kwargs
        return res

    def __getitem__(self, idx):
        res = super().__getitem__(idx)
        return retain_type(res, self)

    def show(self, ax=None, ctx=None, title=None, **kwargs):
        ax = ifnone(ax,ctx)
        if ax is None: fig, ax = plt.subplots(**kwargs)
        ax.plot(self.T)
        ax.axis(xmin=0, xmax=self.shape[-1] - 1)
        ax.set_title(title, weight='bold')
        plt.tight_layout()
        return ax

@Transform
def ToNumpyTensor(o:np.ndarray):
    return NumpyTensor(o)

# Cell
def TSTensorBlock():
    return TransformBlock(item_tfms=ToTSTensor)

class TSDataLoaders(DataLoaders):
    @classmethod
    @delegates(DataLoaders.from_dblock)
    def from_numpy(cls, X, y=None, splitter=None, valid_pct=0.2, seed=0, item_tfms=None, batch_tfms=None, **kwargs):
        "Create timeseries dataloaders from arrays (X and y, unless unlabeled)"
        if splitter is None: splitter = RandomSplitter(valid_pct=valid_pct, seed=seed)
        getters = [ItemGetter(0), ItemGetter(1)] if y is not None else [ItemGetter(0)]
        dblock = DataBlock(blocks=(TSTensorBlock, CategoryBlock),
                           getters=getters,
                           splitter=splitter,
                           item_tfms=item_tfms,
                           batch_tfms=batch_tfms)

        source = itemify(X) if y is None else itemify(X,y)
        return cls.from_dblock(dblock, source, **kwargs)

# Cell
# Native Pytorch dataset
class PytorchDataset():
    def __init__(self, X, y=None): self.X, self.y = torch.as_tensor(X), torch.as_tensor(y)
    def __getitem__(self, idx): return (self.X[idx], self.y[idx])
    def __len__(self): return len(self.X)

# Cell
class NumpyDatasets(Datasets):
    "A dataset that creates tuples from X (and y) and applies `item_tfms`"
    _xtype, _ytype = None, None # Expected X and y output types (torch.Tensor - default - or subclass)
    def __init__(self, X=None, y=None, items=None, sel_vars=None, sel_steps=None, tfms=None, tls=None, n_inp=None, dl_type=None,
                 preprocess=False, **kwargs):

        if tls is None: items = ifnoneelse(y,tuple((X,)),tuple((X, y)))
        self.tfms = L(ifnone(tfms,[None]*len(ifnone(tls,items))))
        self.sel_vars = slice(None) if sel_vars is None else sel_vars
        self.sel_steps = slice(None) if sel_steps is None else sel_steps
        self.tls = L(tls if tls else [TfmdLists(item, t, **kwargs) for item,t in zip(items,self.tfms)])
        self.n_inp = (1 if len(self.tls)==1 else len(self.tls)-1) if n_inp is None else n_inp
        self.ptls = L([tl.items if is_none(tfm) else np.stack(tl[:]) if preprocess else tl for tl,tfm in zip(self.tls, self.tfms)])
        self.preprocess = preprocess

    def __getitem__(self, it):
        return tuple([typ(ptl[it][self.sel_vars, self.sel_steps] if i==0 else ptl[it]) for i,(ptl,typ) in enumerate(zip(self.ptls,self.types))])

    def subset(self, i): return type(self)(tls=L(tl.subset(i) for tl in self.tls), n_inp=self.n_inp,
                                           preprocess=self.preprocess, tfms=self.tfms, sel_vars=self.sel_vars, sel_steps=self.sel_steps)

    def _new(self, X, *args, y=None, **kwargs):
        items = ifnone(items,ifnoneelse(y,tuple((X,)),tuple((X, y))))
        return super()._new(items, tfms=self.tfms, do_setup=False, **kwargs)

    @property
    def vars(self): return self[0][0].shape[-2]

    @property
    def length(self): return self[0][0].shape[-1]

    @property
    def types(self):
        if self.tls:
            types = [type(tl[0]) if isinstance(tl[0], torch.Tensor) else torch.as_tensor for tl in self.tls]
            if self._xtype is not None: types[0] = self._xtype
            if len(types) == 2 and self._ytype is not None: types[1] = self._ytype
            return types


class TSDatasets(NumpyDatasets):
    "A dataset that creates tuples from X (and y) and applies `item_tfms`"
    _xtype, _ytype = TSTensor, None # Expected X and y output types (torch.Tensor - default - or subclass)

# Cell
class NumpyDataLoader(TfmdDL):
    do_item = noops

    def create_batch(self, b): return self.dataset[b]

    @property
    def vars(self): return self.dataset[0][0].shape[-2]

    @property
    def length(self): return self.dataset[0][0].shape[-1]

    @delegates(plt.subplots)
    def show_batch(self, b=None, ctxs=None, max_n=9, nrows=3, ncols=3, figsize=(16, 10), **kwargs):
        b = self.one_batch()
        db = self.decode_batch(b, max_n=max_n)
        if figsize is None: figsize = (ncols*6, max_n//ncols*4)
        if ctxs is None: ctxs = get_grid(min(len(db), nrows*ncols), nrows=None, ncols=ncols, figsize=figsize, **kwargs)
        for i,ctx in enumerate(ctxs):
            show_tuple(db[i], ctx=ctx)

    @delegates(plt.subplots)
    def show_results(self, b, preds, ctxs=None, max_n=9, nrows=3, ncols=3, figsize=(16, 10), **kwargs):
        t = self.decode_batch(b, max_n=max_n)
        p = self.decode_batch((b[0],preds), max_n=max_n)
        if figsize is None: figsize = (ncols*6, max_n//ncols*4)
        if ctxs is None: ctxs = get_grid(min(len(t), nrows*ncols), nrows=None, ncols=ncols, figsize=figsize, **kwargs)
        for i,ctx in enumerate(ctxs):
            title = f'True: {t[i][1]}\nPred: {p[i][1]}'
            color = 'green' if t[i][1] == p[i][1] else 'red'
            t[i][0].show(ctx=ctx, title=title, title_color=color)


@delegates(plt.subplots)
def show_tuple(tup, **kwargs):
    "Display a timeseries plot from a decoded tuple"
    tup[0].show(title='unlabeled' if len(tup) == 1 else tup[1], **kwargs)

class TSDataLoader(NumpyDataLoader): pass

# Cell
def add_ds(dsets, X, y=None, test_items=None, rm_tfms=None, with_labels=False):
    "Create test datasets from X (and y) using validation transforms of `dsets`"
    items = tuple((X,)) if y is None else tuple((X, y))
    with_labels = False if y is None else True
    if isinstance(dsets, (Datasets, NumpyDatasets, TSDatasets)):
        tls = dsets.tls if with_labels else dsets.tls[:dsets.n_inp]
        new_tls = L([tl._new(item, split_idx=1) for tl,item in zip(tls, items)])
        if rm_tfms is None: rm_tfms = [tl.infer_idx(get_first(item)) for tl,item in zip(new_tls, items)]
        else:               rm_tfms = tuplify(rm_tfms, match=new_tls)
        for i,j in enumerate(rm_tfms): new_tls[i].tfms.fs = new_tls[i].tfms.fs[j:]
        if isinstance(dsets, (NumpyDatasets, TSDatasets)):
            cls = dsets.__class__
            return cls(tls=new_tls, n_inp=dsets.n_inp, preprocess=dsets.preprocess, tfms=dsets.tfms, sel_vars=dsets.sel_vars, sel_steps=dsets.sel_steps)
        elif isinstance(dsets, Datasets): return Datasets(tls=new_tls)
    elif isinstance(dsets, TfmdLists):
        new_tl = dsets._new(items, split_idx=1)
        if rm_tfms is None: rm_tfms = dsets.infer_idx(get_first(items))
        new_tl.tfms.fs = new_tl.tfms.fs[rm_tfms:]
        return new_tl
    else: raise Exception(f"This method requires using the fastai library to assemble your data.Expected a `Datasets` or a `TfmdLists` but got {dsets.__class__.__name__}")

def add_test(dsets, X, y=None, test_items=None, rm_tfms=None, with_labels=False):
    return add_ds(dsets, X, y=y, test_items=test_items, rm_tfms=rm_tfms, with_labels=with_labels)

NumpyDatasets.add_test = add_test
# TSDatasets.add_test = add_test

def add_unlabeled(dsets, X, test_items=None, rm_tfms=None, with_labels=False):
    return add_ds(dsets, X, y=None, test_items=test_items, rm_tfms=rm_tfms, with_labels=with_labels)

NumpyDatasets.add_unlabeled = add_unlabeled
# TSDatasets.add_unlabeled = add_unlabeled