import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec

COLUMN1_FIGSIZE = (7, 4)
COLUMN2_FIGSIZE = (14, 4)
FONTSIZE = 12
ISBETTER_FONTSIZE = FONTSIZE + 2
HIGHERISBETTER = "Higher is better ↑"
LOWERISBETTER = "Lower is better ↓"

line_markers = [
    "o",
    "v",
    "s",
    "^",
    "<",
    ">",
    "8",
    ]

hatches = [
    "/",
    "\\",
    "//",
    "\\\\",
    "x",
    ".",
    ",",
    "*",
    "o",
    "O",
    "+",
    "X",
    "s",
    "S",
    "d",
    "D",
    "^",
    "v",
    "<",
    ">",
    "p",    
    "P",
    "$",
    "#",
    "%",
]