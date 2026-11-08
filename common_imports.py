# General-purpose imports (standard library only)
import os
import sys
import json
import time
import re
import math
import logging
import random
import shutil
import pathlib
import argparse
import itertools
import datetime
import collections
import subprocess

# Data manipulation and analysis
import csv
import json
import yaml
import sqlite3
import pickle

# File handling and I/O
import io
import gzip
import zipfile
import tarfile
import glob

# Parallel processing
import multiprocessing
from multiprocessing import Pool

# Miscellaneous utilities
import hashlib
import uuid
import base64
import warnings
from contextlib import contextmanager
from functools import partial, lru_cache

# ---- Optional imports ------------------------------------------------
# A minimal install (openai, tiktoken, PyYAML, numpy, requests, aiohttp, tqdm, pydantic)
# must be enough to import this module: the agent loop does not need the ML/visual stack.
# Missing libraries become None instead of raising, so `import common_imports` never fails.
MISSING = set()

def _opt(name, alias=None):
    """Best-effort import; records the failure in MISSING and binds the name to None."""
    try:
        mod = __import__(name)
    except ImportError:
        MISSING.add(name)
        globals()[alias if alias else name] = None
        return None
    globals()[alias if alias else name] = mod
    return mod

# Data stack
_opt("pandas", "pd")
_opt("numpy", "np")
_opt("h5py")

# Visualization
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    MISSING.update({"matplotlib", "seaborn"})
    plt = sns = None
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    MISSING.add("plotly")
    px = go = None

# Deep learning frameworks
for _name in ("transformers", "torch", "tensorflow"):
    _opt(_name)
try:
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, Dataset, random_split
except ImportError:
    nn = optim = F = None
    DataLoader = Dataset = random_split = None

# NLP libraries
_opt("tiktoken")
_opt("nltk")
try:
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer, WordNetLemmatizer
except ImportError:
    word_tokenize = sent_tokenize = stopwords = None
    PorterStemmer = WordNetLemmatizer = None
_opt("spacy")
_opt("sacremoses")

# Diffusers for image generation and stable diffusion
_opt("diffusers")
try:
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
except ImportError:
    StableDiffusionPipeline = DPMSolverMultistepScheduler = None

# Performance acceleration libraries
_opt("accelerate")
try:
    from accelerate import Accelerator
except ImportError:
    Accelerator = None

# Hugging Face Hub utilities
_opt("huggingface_hub")
try:
    from huggingface_hub import HfApi, notebook_login
except ImportError:
    HfApi = notebook_login = None

# Scikit-learn for machine learning
_opt("sklearn")
try:
    from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans
    from sklearn.svm import SVC
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.metrics.pairwise import linear_kernel, cosine_similarity
except ImportError:
    train_test_split = GridSearchCV = RandomizedSearchCV = None
    accuracy_score = precision_score = recall_score = f1_score = None
    classification_report = confusion_matrix = None
    StandardScaler = MinMaxScaler = LabelEncoder = None
    PCA = KMeans = SVC = None
    TfidfVectorizer = CountVectorizer = None
    linear_kernel = cosine_similarity = None

# Statistical analysis
_opt("scipy")
try:
    from scipy import stats, signal, spatial
    from scipy.optimize import minimize
    from scipy.spatial.distance import euclidean, cosine
    from scipy.linalg import svd, eig
except ImportError:
    stats = signal = spatial = None
    minimize = euclidean = cosine = svd = eig = None
try:
    from statsmodels.api import OLS, Logit
    from statsmodels.tsa.arima_model import ARIMA
    from statsmodels.tsa.stattools import adfuller, pacf, acf
except ImportError:
    OLS = Logit = ARIMA = None
    adfuller = pacf = acf = None

# Image processing and handling
_opt("PIL")
try:
    from PIL import Image
except ImportError:
    Image = None
_opt("imageio")
try:
    from skimage import io as _skimage_io, color as _skimage_color, filters as _skimage_filters
    from skimage import transform as _skimage_transform, exposure as _skimage_exposure
    io_skimage, color, filters, transform, exposure = (_skimage_io, _skimage_color,
                                                        _skimage_filters, _skimage_transform,
                                                        _skimage_exposure)
except ImportError:
    color = filters = transform = exposure = None

# Progress and typing helpers
try:
    from tqdm import tqdm
except ImportError:
    MISSING.add("tqdm")
    tqdm = None
from typing import Dict, List

# Other advanced libraries
_opt("pydantic")
_opt("requests")
_opt("aiohttp")
