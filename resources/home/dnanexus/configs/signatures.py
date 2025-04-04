from openpyxl.styles import Border, Side

# prepare formatting
THIN = Side(border_style="thin", color="000000")
LOWER_BORDER = Border(bottom=THIN)

CONFIG = {
    "cells_to_write": {
        (1, 1): "=SOC!A2",
        (2, 1): "=SOC!A3",
        (1, 3): "=SOC!A5",
        (2, 3): "=SOC!A6",
        (1, 5): "=SOC!A9",
        (35, 1): "Pertinent chromosomal CNVs",
        (35, 3): "Pertinent signatures",
        (36, 1): "v2 (March 2015)",
        (36, 3): "None",
    },
    "to_bold": ["A1", "A35", "C35"],
    "col_width": (
        ("A", 18),
        ("B", 22),
        ("C", 18),
        ("D", 22),
        ("E", 22),
    ),
    "borders": {
        "single_cells": [
            ("A35", LOWER_BORDER),
            ("C35", LOWER_BORDER),
        ],
    },
    "images": [
        {"cell": "A4", "img_index": 5, "size": (600, 800)},
        {"cell": "H4", "img_index": 6, "size": (600, 800)},
        {"cell": "V4", "img_index": 7, "size": (600, 1100)},
    ],
}
