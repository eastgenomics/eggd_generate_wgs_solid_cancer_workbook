import re
import urllib.request

from bs4 import BeautifulSoup
from bs4 import MarkupResemblesLocatorWarning
import pandas as pd
from PIL import Image

import warnings

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def open_html(file: str) -> BeautifulSoup:
    """Open HTML file using BeautifulSoup

    Parameters
    ----------
    file : str
        File path to the HTML

    Returns
    -------
    BeautifulSoup
        BeautifulSoup object for the HTML page
    """

    with open(file) as f:
        return BeautifulSoup(f, features="lxml")


def download_images(html: BeautifulSoup) -> list:
    """Get all images in the BeautifulSoup object

    Parameters
    ----------
    html : BeautifulSoup
        BeautifulSoup object

    Returns
    -------
    list
        List of images in the HTML
    """

    images = []

    for i, img in enumerate(html.findAll("img"), 1):
        img_path = f"figure_{i}.jpg"
        urllib.request.urlretrieve(img.get("src"), img_path)

        if i == 2:
            figure_2 = Image.open(img_path)
            cropped_figure_2 = figure_2.crop((600, 600, 2400, 2400))
            cropped_figure_2.save(img_path)

        images.append(img_path)

    return images


def get_tables(html: str) -> list:
    """Get all the tables in the HTML

    Parameters
    ----------
    html : str
        File path to the HTML file

    Returns
    -------
    list
        List of dataframes for the tables in the HTML file
    """

    return pd.read_html(html)


def get_tag_sibling(soup: BeautifulSoup, tag: str, pattern: str) -> str:
    """Given a tag and a pattern, get the adjacent element value

    Parameters
    ----------
    soup : BeautifulSoup
        Beautiful soup object
    tag : str
        Tag to look the pattern in
    pattern : str
        Pattern to look for

    Returns
    -------
    str
        Value of the next sibling
    """

    return soup.find(tag, text=re.compile(pattern)).next_sibling.strip()
