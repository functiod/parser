from collections import defaultdict
import requests
from requests.exceptions import Timeout, ConnectionError
from bs4 import BeautifulSoup
import validators
import re
import numpy as np
import html

video_url: str = 'https://animego.org/anime//player?_allow=true'
change_series_url: str = 'https://animego.org/anime/series?dubbing=1&provider=19&episode=&id='
requests_iter: int = 0
link_iter: int = 1

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

def extract_info_from_html(html: str) -> dict:
    parser = BeautifulSoup(html, features="html.parser")
    title: str = parser.find('div', class_ ='anime-title').find('h1').get_text()
    dl_element: list = parser.find('dl', class_='row')
    dt_elements: list = dl_element.find_all('dt')
    dd_elements: list = dl_element.find_all('dd')
    param_dict: dict = {}
    parameter: str = ''
    value: str = ''
    param_dict['Название'] = title
    for dt, dd in zip(dt_elements, dd_elements):
        parameter = dt.text.strip()
        value = dd.text.strip()
        correct_value: str = re.sub(r'\s+', ' ', value)
        param_dict[parameter] = correct_value
    return param_dict

def get_url_last_numbers(html: str) -> int:
    last_place: int = html.rfind('-')
    return html[last_place+1:]

def make_video_url_requests(html: str) -> tuple:
    links_list: list = parse_links_to_movies(html)
    last_number_list: list = list(map(get_url_last_numbers, links_list))
    input_before: int = video_url.rfind('/')
    requests_list: list = [video_url[:input_before]+last_number_list[i]+video_url[input_before:] for i in range(len(last_number_list))]
    return requests_list, links_list

def extract_video_page_info(html: str) -> list[list]:
    video_urls: tuple = make_video_url_requests(html)
    requests_list: list = video_urls[requests_iter]
    links_list: list = video_urls[link_iter]
    page_content: list = [download_html_video_page(requests_list[i])['content'] for i in range(len(requests_list))]
    return page_content, links_list

def extract_video_page_info_series(html) -> list:
    video_page_info: list[list] = extract_video_page_info(html)
    page_content: list = video_page_info[requests_iter]
    from_page: str = "video-player-bar-series-item d-inline-block br-4 mb-0 video-player__active"
    to_page: str = 'class="video-player-bar-series-watch text-player-gray px-3 py-2 text-nowrap cursor-pointer  modal-btn modal.ajax"'
    page_content_series: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find(from_page):page_content[i].rfind(to_page)].split('\n') for i in range(len(page_content))]))
    page_content_series = [filter_series_list(sublist) for sublist in page_content_series if sublist]
    return page_content_series

def extract_video_page_info_voices(html) -> list:
    video_page_info: list[list] = extract_video_page_info(html)
    page_content: list = video_page_info[requests_iter]
    page_content_voices: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find("data-dubbing"):page_content[i].find('Kodik')].split('\n') for i in range(len(page_content))]))
    page_content_voices = [filter_voice_list(sublist) for sublist in page_content_voices]
    return page_content_voices

def extract_video_page_info_player(html) -> list:
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
    # good_word: list = ['data-provider', 'data-player', 'data-provide-dubbing']
    bad_words: list = ['data-provider']
    good_words: list = ['data-provide-dubbing', 'data-player']
    new_buff = [elem for elem in new_buff if any(key_word in elem for key_word in good_words) and not any(string in elem for string in bad_words)]
    result: list = []
    for i, elem in enumerate(new_buff):
        if 'data-provide-dubbing' in elem:
            result.append(new_buff[i][beginning:new_buff[i].find('>')].replace('-provide-', '-'))
        else:
                result.append(new_buff[i])
    return result

def delete_extra_info(buff: list[list]) -> list:
    my_buff: list = buff
    for i, elem in enumerate(buff):
        my_buff[i] = list(filter(None, elem))
        for j, N in enumerate(my_buff[i]):
            my_buff[i][j] = N.strip()
    return my_buff

def get_content_all_series(main_page_url: str) -> list[list]:
    url: str = 'https://animego.org/anime/series?&'
    page_content_series: list[list] = extract_video_page_info_series(download_html_page(main_page_url))
    anime_list: list = []
    anime_content: list = []
    for anime in page_content_series:
        series_list: list = [url + series for series in anime if series]
        anime_list.append(series_list)
    anime_content = [download_html_video_page(series)['content'] for series in anime_list[0]]
    # for anime in my_anime_list:
    #     anime_content_series: list = []
    #     for series in anime:
    #         if download_html_video_page(series)['content'] is not None:
    #             anime_content_series: list = download_html_video_page(series)['content']
    #     anime_content.append(anime_content_series)
    return anime_content

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

if __name__ == '__main__':
    anime_content: list[list] = get_content_all_series('https://animego.org/anime?sort=r.rating&direction=desc')
    # voices: list = [['data-dubbing="2"', 'AniLibria', 'data-dubbing="4"', 'SHIZA Project'], ['data-dubbing="2"', 'AniLibria', 'data-dubbing="4"', 'SHIZA Project'], ['data-dubbing="2"', 'AniLibria', 'data-dubbing="4"', 'SHIZA Project'], ['data-dubbing="2"', 'AniLibria', 'data-dubbing="4"', 'SHIZA Project']]
    # player: list = [['data-player="//video.sibnet.ru/shell.php?videoid=3543126"', 'data-dubbing="2"', 'data-player="//myvi.top/embed/o8kkoxb3c1owfpoojxiohra9ow"', 'data-dubbing="2"', 'data-player="//video.sibnet.ru/shell.php?videoid=3073987"', 'data-dubbing="4"', 'data-player="//myvi.top/player/embed/html/oyMH-Da75uLmfesMd9bCk0CjwRV3PQg5xToQZds96wn65Kuo7OrV4b_y8gS5Cdagy0"', 'data-dubbing="4"'], ['data-player="//video.sibnet.ru/shell.php?videoid=3543816"', 'data-dubbing="2"', 'data-player="//myvi.top/embed/za8edq3htouwdjbsmkjb4h8sho"', 'data-dubbing="2"', 'data-player="//video.sibnet.ru/shell.php?videoid=3073988"', 'data-dubbing="4"', 'data-player="//myvi.top/player/embed/html/oWs5SnCKEkuaGhH5HH9u-8SWKWLvOqPXAZmZgPDK71nseflM0PeRiu3zboi_dUJ9w0"', 'data-dubbing="4"'], ['data-player="//video.sibnet.ru/shell.php?videoid=3544153"', 'data-dubbing="2"', 'data-player="//myvi.top/embed/6juunr5oqfuw3nqycfm1grfj1r"', 'data-dubbing="2"', 'data-player="//vk.com/video_ext.php?oid=-46767995&amp;id=456240556&amp;hash=5d4b490f71f6141b"', 'data-dubbing="4"'], ['data-player="//video.sibnet.ru/shell.php?videoid=3544768"', 'data-dubbing="2"', 'data-player="//myvi.top/embed/gdc44adykzaw3qgq61nceqobgy"', 'data-dubbing="2"', 'data-player="//video.sibnet.ru/shell.php?videoid=2684053"', 'data-dubbing="4"', 'data-player="//myvi.top/player/embed/html/ogMR2sN5pdJkqPPriFYLyO4fD7C3okrBijp8K9uQJU8pzAHy0Cr8Rit66Vo0BsKZd0"', 'data-dubbing="4"']]
    voices = get_voices_all_series(anime_content)
    player = get_player_all_series(anime_content)
    print(voices)
    print(player)
    d_voices: dict = {}
    d_player: dict = defaultdict(list)
    for sublist in voices:
        dub_keys: list = [elem for elem in sublist if 'data-dubbing' in elem]
        voices_values: list = [voice for voice in sublist if 'data-dubbing' not in voice]
        d_voices.update(dict(zip(dub_keys, voices_values)))
    for sublist in player:
        player_value: list = [voice for voice in sublist if 'data-dubbing' not in voice]
        dub_keys_2: list = [elem for elem in sublist if 'data-dubbing' in elem]
    for key, value in zip(dub_keys_2, player_value):
        d_player[key].append(value)
    d_player = dict(d_player)
    result: dict = {d_voices[key]: d_player[key] for key in d_voices.keys()}

    print(result)
