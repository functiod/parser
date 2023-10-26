import requests
from bs4 import BeautifulSoup
import validators
import re
import numpy as np
import html
from parser_app import extract_video_page_info_player, extract_video_page_info_series, extract_video_page_info_voices
from parser_app import download_html_page, download_html_video_page


# 'https://animego.org/anime/series?dubbing=2&provider=19&episode=1&id=24907'
def make_request_url(html: str) -> None:
    url: str = 'https://animego.org/anime/series?'
    url_list: list = []
    series_info: list = extract_video_page_info_series(html)
    voices_info: list = extract_video_page_info_voices(html)
    player_info: list = extract_video_page_info_player(html)
    for i, provider in enumerate(player_info):
        for j, series in enumerate(series_info):

