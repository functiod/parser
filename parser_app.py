from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import validators
import re
import numpy as np
import html
import pickle
import os

video_url: str = 'https://animego.org/anime//player?_allow=true'
change_series_url: str = 'https://animego.org/anime/series?dubbing=1&provider=19&episode=&id='
requests_iter: int = 0
link_iter: int = 1
titles_iter: int = 2

def download_html_page(url: str) -> str | int:
    try:
        return requests.get(url).content.decode('utf-8')
    except:
        return 0

def download_html_video_page(url: str) -> str | None:
    try:
        return requests.get(url, headers={"x-requested-with": "XMLHttpRequest"}).json()
    except:
        return None

def check_if_link(url: str) -> bool:
    try:
        response: requests.Response = requests.head(url)
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False

def extract_links_from_html(html: str) -> list:
    parser = BeautifulSoup(html, features="html.parser")
    return parser.find_all('a', href=True)

def parse_links_to_movies(html: str) -> list:
    false_name_list: list = ['manga', 'characters', 'random', 'connect', 'vkontakte', 'genre', 'type', 'season']
    link_list: list = list(set([elem['href'] for elem in extract_links_from_html(html)]))
    valid_links: list = []
    for link in link_list:
        if validators.url(link):
            valid_links.append(link)
    filtered_links: list = [link for link in valid_links if not any(elem in link for elem in false_name_list)
                             and link.split('/')[-1] != 'anime' and check_if_link(link)]
    return filtered_links

def extract_info_from_html(url: str) -> dict:
    parser = BeautifulSoup(url, features="html.parser")
    title_element: str = parser.find('div', class_ ='anime-title')
    title: str
    if title_element:
        title = title_element.find('h1').get_text()
    else:
        title = "Название не найдено"
    param_dict: dict = {}
    param_dict['Название'] = title
    return param_dict

def get_url_last_numbers(html: str) -> int:
    last_place: int = html.rfind('-')
    return html[last_place+1:]

def make_video_url_requests(html: str) -> tuple:
    links_list: list = parse_links_to_movies(html)
    last_number_list: list = list(map(get_url_last_numbers, links_list))
    input_before: int = video_url.rfind('/')
    requests_list: list = [video_url[:input_before]+last_number_list[i]+video_url[input_before:] for i in range(len(last_number_list))]
    titles_list: list = [extract_info_from_html(download_html_page(link)) for link in links_list]
    return requests_list, links_list, titles_list

def extract_video_page_info(html: str) -> list[list]:
    video_urls: tuple = make_video_url_requests(html)
    requests_list: list = video_urls[requests_iter]
    links_list: list = video_urls[link_iter]
    titles_list: list = video_urls[titles_iter]
    page_content: list = []
    for url in requests_list:
        response: requests.Response = download_html_video_page(url)
        if response is not None and 'content' in response:
            page_content.append(response['content'])
    return page_content, links_list, titles_list

def extract_video_page_info_series(html: str) -> list:
    video_page_info: list[list] = extract_video_page_info(html)
    page_content: list = video_page_info[requests_iter]
    titles_list: list = video_page_info[titles_iter]
    from_page: str = "video-player-bar-series-item d-inline-block br-4 mb-0 video-player__active"
    to_page: str = 'class="video-player-bar-series-watch text-player-gray px-3 py-2 text-nowrap cursor-pointer  modal-btn modal.ajax"'
    page_content_series: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find(from_page):page_content[i].rfind(to_page)].split('\n') for i in range(len(page_content))]))
    page_content_series = [filter_series_list(sublist) for sublist in page_content_series if sublist]
    return page_content_series, titles_list

def extract_video_page_info_voices(html: str) -> list:
    video_page_info: list[list] = extract_video_page_info(html)
    page_content: list = video_page_info[requests_iter]
    page_content_voices: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find("data-dubbing"):page_content[i].find('Kodik')].split('\n') for i in range(len(page_content))]))
    page_content_voices = [filter_voice_list(sublist) for sublist in page_content_voices]
    return page_content_voices

def extract_video_page_info_player(html: str) -> list:
    video_page_info: list[list] = extract_video_page_info(html)
    page_content: list = video_page_info[requests_iter]
    page_content_players: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find("video-dubbing"):page_content[i].rfind('video-player-toggle-item-name text-underline-hover')].split('\n') for i in range(len(page_content))]))
    page_content_players = [np.unique(filter_player_list(sublist)).tolist() for sublist in page_content_players]
    return page_content_players

def filter_series_list(buff: list) -> list:
    new_buff: list = buff
    bad_words: list = ['role', 'video', 'description', 'div', 'span', 'class', 'title', 'episode']
    new_buff = [string.removeprefix('data-').replace('"', '') for string in new_buff if not any(elem in string for elem in bad_words)]
    return new_buff

def filter_voice_list(buff: list) -> list:
    new_buff: list = buff
    beginning: int = 0
    good_words: list = ['data-dubbing']
    bad_words: list = ['class', 'span', 'div', 'data-provider', 'cursor']
    result: list = []
    new_buff = [elem for elem in new_buff if any(key_word in elem for key_word in good_words) or not any(name in elem for name in bad_words)]
    for i, elem in enumerate(new_buff):
        if 'data-dubbing' in elem:
            result.append(new_buff[i][beginning:new_buff[i].find('>')])
        else:
                result.append(new_buff[i])
    return result

def filter_player_list(buff: list) -> list:
    new_buff: list = buff
    beginning: int = 0
    good_words: list = ['data-provide-dubbing', 'data-player']
    new_buff = [elem for elem in new_buff if any(key_word in elem for key_word in good_words)]
    result: list = []
    for i, elem in enumerate(new_buff):
        if 'data-provide-dubbing' in elem:
            result.append(new_buff[i][beginning:new_buff[i].find('>')].replace('-provide-', '-'))
        else:
            match: re.Match[str] = re.search(r'data-player="(.*?)"', elem)
            if match:
                data_player_attribute: str = match.group(0)
                result.append(data_player_attribute)
    return result

def delete_extra_info(buff: list[list]) -> list:
    my_buff: list = buff
    for i, elem in enumerate(buff):
        my_buff[i] = list(filter(None, elem))
        for j, N in enumerate(my_buff[i]):
            my_buff[i][j] = N.strip()
    return my_buff

def get_content_all_series(main_page_url: str) -> list[list[list]]:
    url: str = 'https://animego.org/anime/series?&'
    request: list[list[list]] = extract_video_page_info_series(download_html_page(main_page_url))
    page_content_series: list[list] = request[requests_iter]
    titles_list: list = request[1]
    anime_list: list = []
    anime_content: list = []
    for anime in page_content_series:
        series_list: list = [url + series for series in anime if series]
        anime_list.append(series_list)
    for anime in anime_list:
        anime_content_series: list = []
        for series in anime:
            response: requests.Response = download_html_video_page(series)
            if response is not None and 'content' in response:
                anime_content_series.append(response['content'])
        anime_content.append(anime_content_series)
    return anime_content, titles_list

def get_voices_all_series(anime_content_list: list[list]) -> list[list]:
    my_anime_content_list: list[list] = anime_content_list
    anime_content_voices: list = delete_extra_info([my_anime_content_list[i][my_anime_content_list[i].find("video-player-toggle-item d-inline-block text-truncate mb-1 br-3 cursor-pointer"):my_anime_content_list[i].find('class="tab-pane video-player-toggle scroll"')].split('\n') for i in range(len(my_anime_content_list))])
    anime_content_voices = [filter_voice_list(sublist) for sublist in anime_content_voices if sublist]
    return anime_content_voices

def get_player_all_series(anime_content_list: list[list]) -> list[list]:
    my_anime_content_list: list[list] = anime_content_list
    anime_content_player: list = delete_extra_info(delete_extra_info([my_anime_content_list[i][my_anime_content_list[i].find("video-player-toggle-item text-truncate mb-1 br-3"):my_anime_content_list[i].rfind('class="video-player-toggle-item-name text-underline-hover"')].split('\n') for i in range(len(my_anime_content_list))]))
    anime_content_player = [filter_player_list(sublist) for sublist in anime_content_player if sublist]
    return anime_content_player

def get_cached_result(main_page_url: str) -> list[list[list]]:
    cache_file = "cached_result.pkl"
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            result = pickle.load(f)
    else:
        result: list[list] = get_content_all_series(main_page_url)
        with open(cache_file, "wb") as f:
            pickle.dump(result, f)
    return result

def voices() -> dict:
    for i, anime in enumerate(anime_voices):
    d_sub_voices_for_anime: dict = {}
    d_sub_voices_for_series: dict = {}
    for voice_series in anime:
        dub_keys: list = [elem for elem in voice_series if 'data-dubbing' in elem]
        voices_values: list = [voice for voice in voice_series if 'data-dubbing' not in voice]
        d_sub_voices_for_series.update(dict(zip(dub_keys, voices_values)))
    d_voices[i] = d_sub_voices_for_series

def players() -> list:
    for anime in anime_player:
        player_sub_list: list = []
        for player_series in anime:
            dub_keys_2: list = [elem for elem in player_series if 'data-dubbing' in elem]
            player_value: list = [voice for voice in player_series if 'data-dubbing' not in voice]
            player_sub_list.append([dub_keys_2, player_value])
        player_list.append(player_sub_list)

def dict_players() -> dict:
    for i, anime in enumerate(player_list):
        d_series_player: list = []
        for series in anime:
            d_sub_player: dict = defaultdict(list)
            for key, value in zip(series[0], series[1]):
                d_sub_player[key].append(value)
            d_sub_player = dict(d_sub_player)
            d_series_player.append(d_sub_player)
        d_player[i] = d_series_player

def final_dict() -> dict:
    for d_num, d_final in d_player.items():
        subvoices = d_voices.get(d_num, {})
        series_result: dict = {}
        for i, d_sub_final in enumerate(d_final):
            subresult: dict = {}
            for key in subvoices.keys():
                if key in d_sub_final.keys():
                    subresult[subvoices[key]] = d_sub_final[key]
            series_result[i] = subresult
        result[list(titles_dict[d_num].values())[0]] = series_result

if __name__ == '__main__':
    info: list = get_cached_result('https://animego.org/anime?sort=r.rating&direction=desc')
    titles_dict: dict = info[1]
    anime_content: list[list[list]] = info[requests_iter]
    anime_voices: list = [get_voices_all_series(anime) for anime in anime_content if anime]
    anime_player: list = [get_player_all_series(anime) for anime in anime_content if anime]
    voices_list: list = []
    player_list: list = []
    d_voices: dict = {}
    d_final: list = []
    series_result: dict = {}
    d_player: dict = {}
    result: dict = {}
    for i, anime in enumerate(anime_voices):
        d_sub_voices_for_anime: dict = {}
        d_sub_voices_for_series: dict = {}
        for voice_series in anime:
            dub_keys: list = [elem for elem in voice_series if 'data-dubbing' in elem]
            voices_values: list = [voice for voice in voice_series if 'data-dubbing' not in voice]
            d_sub_voices_for_series.update(dict(zip(dub_keys, voices_values)))
        d_voices[i] = d_sub_voices_for_series

    for anime in anime_player:
        player_sub_list: list = []
        for player_series in anime:
            dub_keys_2: list = [elem for elem in player_series if 'data-dubbing' in elem]
            player_value: list = [voice for voice in player_series if 'data-dubbing' not in voice]
            player_sub_list.append([dub_keys_2, player_value])
        player_list.append(player_sub_list)

    for i, anime in enumerate(player_list):
        d_series_player: list = []
        for series in anime:
            d_sub_player: dict = defaultdict(list)
            for key, value in zip(series[0], series[1]):
                d_sub_player[key].append(value)
            d_sub_player = dict(d_sub_player)
            d_series_player.append(d_sub_player)
        d_player[i] = d_series_player

    for d_num, d_final in d_player.items():
        subvoices = d_voices.get(d_num, {})
        series_result: dict = {}
        for i, d_sub_final in enumerate(d_final):
            subresult: dict = {}
            for key in subvoices.keys():
                if key in d_sub_final.keys():
                    subresult[subvoices[key]] = d_sub_final[key]
            series_result[i] = subresult
        result[list(titles_dict[d_num].values())[0]] = series_result
    print(result)
