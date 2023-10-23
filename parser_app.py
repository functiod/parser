import requests
from bs4 import BeautifulSoup
import validators
import re
import numpy as np
import html

video_url: str = 'https://animego.org/anime//player?_allow=true'
change_series_url: str = 'https://animego.org/anime/series?dubbing=1&provider=19&episode=&id='
requests_iter: int = 0
link_iter: int = 1

def download_html_page(url: str) -> str | None:
    try:
        return requests.get(url).content.decode('utf-8')
    except KeyboardInterrupt:
        raise
    except:
        return None

def download_html_video_page(url: str) -> str | None:
    try:
        return requests.get(url, headers={"x-requested-with": "XMLHttpRequest"}).json()
    except KeyboardInterrupt:
        raise
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
    links_list: list = video_page_info[link_iter]
    page_content_series: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find("data-episode"):page_content[i].find('data-episode-description=')].split('\n') for i in range(len(page_content))]))
    page_content_series = [filter_series_list(sublist) for i, sublist in enumerate(page_content_series)]

    page_content = extract_video_page_info(info)[requests_iter]
    page_content_series: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find("video-player-bar-series-item d-inline-block br-4 mb-0 video-player__active"):page_content[i].rfind('class="video-player-bar-series-watch text-player-gray px-3 py-2 text-nowrap cursor-pointer  modal-btn modal.ajax"')].split('\n') for i in range(len(page_content))]))
    page_content_series = [filter_series_list(sublist) for i, sublist in enumerate(page_content_series) if sublist]

    return page_content_series

def extract_video_page_info_voices(html) -> list:
    video_page_info: list[list] = extract_video_page_info(html)
    page_content: list = video_page_info[requests_iter]
    # links_list: list = video_page_info[link_iter]
    page_content_voices: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find("data-dubbing"):page_content[i].find('Kodik')].split('\n') for i in range(len(page_content))]))
    page_content_voices = [filter_voice_list(sublist) for i, sublist in enumerate(page_content_voices)]
    return page_content_voices

def extract_video_page_info_player(html) -> list:
    video_page_info: list[list] = extract_video_page_info(html)
    page_content: list = video_page_info[requests_iter]
    # links_list: list = video_page_info[link_iter]
    page_content_players: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find("video-dubbing"):page_content[i].rfind('video-player-toggle-item-name text-underline-hover')].split('\n') for i in range(len(page_content))]))
    page_content_players = [np.unique(filter_player_list(sublist)).tolist() for i, sublist in enumerate(page_content_players)]
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
    good_word: list = ['data-provider', 'data-player', 'data-provide-dubbing']
    new_buff = [elem for elem in new_buff if any(key_word in elem for key_word in good_word)]
    result: list = []
    for i, elem in enumerate(new_buff):
        if 'data-provide-dubbing' in elem:
            result.append(new_buff[i][beginning:new_buff[i].find('>')])
        else:
                result.append(new_buff[i])
    return result

def delete_extra_info(buff: list) -> list:
    my_buff: list = buff
    for i, elem in enumerate(buff):
        my_buff[i] = list(filter(None, elem))
        for j, N in enumerate(my_buff[i]):
            my_buff[i][j] = N.strip()
    return my_buff

def

if __name__ == '__main__':
    info: str = download_html_page('https://animego.org/anime?sort=r.rating&direction=desc')
    url: str = 'https://animego.org/anime/series?&'

    page_content = extract_video_page_info(info)[requests_iter]
    page_content_series: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find("video-player-bar-series-item d-inline-block br-4 mb-0 video-player__active"):page_content[i].rfind('class="video-player-bar-series-watch text-player-gray px-3 py-2 text-nowrap cursor-pointer  modal-btn modal.ajax"')].split('\n') for i in range(len(page_content))]))
    page_content_series = [filter_series_list(sublist) for i, sublist in enumerate(page_content_series) if sublist]

    anime_list: list = page_content_series[0]
    anime_urls: list = [url + data_id for i, data_id in enumerate(anime_list) if data_id]
    anime_content: list = []
    tag: str = ''
    for i in range(len(anime_urls)):
        tag = download_html_video_page(anime_urls[i])['content']
        if tag:
            anime_content.append(tag)
        else:
            print(i, download_html_video_page(anime_urls[i])['content'])
    # anime_content: list = [download_html_video_page(anime_urls[i])['content'] for i in range(len(anime_urls))]

    anime_content_for_voices = anime_content
    anime_content_for_player = anime_content

    anime_content_voices: list = delete_extra_info([anime_content_for_voices[i][anime_content_for_voices[i].find("video-player-toggle-item d-inline-block text-truncate mb-1 br-3 cursor-pointer"):anime_content_for_voices[i].find('class="tab-pane video-player-toggle scroll"')].split('\n') for i in range(len(anime_content_for_voices))])
    anime_content_voices = [filter_voice_list(sublist) for i, sublist in enumerate(anime_content_voices) if sublist]

    anime_content_player: list = delete_extra_info(delete_extra_info([anime_content_for_player[i][anime_content_for_player[i].find("video-player-toggle-item text-truncate mb-1 br-3"):anime_content_for_player[i].rfind('class="video-player-toggle-item-name text-underline-hover"')].split('\n') for i in range(len(anime_content_for_player))]))
    anime_content_player = [filter_player_list(sublist) for i, sublist in enumerate(anime_content_player) if sublist]
    print(anime_content_voices)
    print(anime_content_player)
