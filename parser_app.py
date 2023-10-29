from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import psycopg2
import validators
import re
import numpy as np
import json
import pickle
import os
import schedule
import time
import threading

new_page_url: str = 'https://animego.org/anime?sort=a.startDate&direction=asc&type=animes&page=2'
video_url: str = 'https://animego.org/anime//player?_allow=true'
change_series_url: str = 'https://animego.org/anime/series?dubbing=1&provider=19&episode=&id='
main_menu_url: str = 'https://animego.org/'
requests_iter: int = 0
link_iter: int = 1
titles_iter: int = 2

def download_html_page(url: str) -> str | int:
    try:
        return requests.get(url).content.decode('utf-8')
    except:
        return None

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

def parse_links_to_updated_movies(url: str = 'https://animego.org/') -> list:
    parser = BeautifulSoup(download_html_page(url), features="html.parser")
    title_element: str = parser.find('div', class_ ='last-update-container scroll collapse show').find_all(attrs={"onclick": True})
    preffix: str = 'https://animego.org'
    titles: list = []
    links: list = []
    for element in title_element:
        title_span: str = element.find('span', class_='last-update-title')
        if title_span:
            anime_title: str = title_span.text
            titles.append(anime_title)
        link_to_anime: str = preffix+element.get('onclick').removeprefix("location.href='").replace("'", "")
        links.append(link_to_anime)
    return links

def extract_info_from_html(url: str) -> dict:
    parser = BeautifulSoup(url, features="html.parser")
    title_element: str = parser.find('div', class_ ='anime-title')
    if title_element:
        title: str = title_element.find('h1').get_text()
    else:
        title: str = "Название не найдено"
    img_element: str = parser.find('div', class_='anime-poster position-relative cursor-pointer')
    if not img_element:
        img_element = 'Изображения не найдено'
    else:
        img_element = img_element.find('img')['src']
    anime_info: str = parser.find('div', class_='anime-info')
    if not anime_info:
        anime_info = 'Информации не найдено'
        dt_list: list = ['Информации не найдено']
        dd_list: list = ['Информации не найдено']
    else:
        anime_info = anime_info.find('dl')
        dt_list: list = [elem.get_text().strip() for elem in anime_info.find_all('dt')]
        dd_list: list = [elem.get_text().strip() for elem in anime_info.find_all('dd')]
    anime_info_dict: dict = {key: value for (key, value) in zip(dt_list, dd_list)}
    param_dict: dict = {}
    param_dict['Название'] = title
    param_dict['Обложка'] = img_element
    param_dict['Информация'] = anime_info_dict
    return param_dict

def get_url_last_numbers(html: str) -> int:
    last_place: int = html.rfind('-')
    return html[last_place+1:]

def make_video_url_requests(html: str, update: bool = False) -> tuple:
    if not update:
        links_list: list = parse_links_to_movies(html)
    else:
        links_list: list = parse_links_to_updated_movies()
    last_number_list: list = list(map(get_url_last_numbers, links_list))
    input_before: int = video_url.rfind('/')
    requests_list: list = [video_url[:input_before]+last_number_list[i]+video_url[input_before:] for i in range(len(last_number_list))]
    titles_list: list = [extract_info_from_html(download_html_page(link)) for link in links_list]
    return requests_list, links_list, titles_list

def extract_video_page_info(html: str, update: bool = False) -> list[list]:
    video_urls: tuple = make_video_url_requests(html, update)
    requests_list: list = video_urls[requests_iter]
    links_list: list = video_urls[link_iter]
    titles_list: list = video_urls[titles_iter]
    page_content: list = []
    for url in requests_list:
        response: requests.Response = download_html_video_page(url)
        if response is not None and 'content' in response:
            page_content.append(response['content'])
    return page_content, links_list, titles_list

def extract_video_page_info_series(html: str, update: bool = False) -> list:
    video_page_info: list[list] = extract_video_page_info(html, update)
    page_content: list = video_page_info[requests_iter]
    titles_list: list = video_page_info[titles_iter]
    from_page: str = "video-player-bar-series-item d-inline-block br-4 mb-0 video-player__active"
    to_page: str = 'class="video-player-bar-series-watch text-player-gray px-3 py-2 text-nowrap cursor-pointer  modal-btn modal.ajax"'
    page_content_series: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find(from_page):page_content[i].rfind(to_page)].split('\n') for i in range(len(page_content))]))
    page_content_series = [filter_series_list(sublist) for sublist in page_content_series if sublist]
    return page_content_series, titles_list

def extract_video_page_info_voices(html: str, update: bool = False) -> list:
    video_page_info: list[list] = extract_video_page_info(html, update)
    page_content: list = video_page_info[requests_iter]
    page_content_voices: list = delete_extra_info(delete_extra_info([page_content[i][page_content[i].find("data-dubbing"):page_content[i].find('Kodik')].split('\n') for i in range(len(page_content))]))
    page_content_voices = [filter_voice_list(sublist) for sublist in page_content_voices]
    return page_content_voices

def extract_video_page_info_player(html: str, update: bool = False) -> list:
    video_page_info: list[list] = extract_video_page_info(html, update)
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
    bad_words: list = ['class', 'span', 'div', 'data-provider', 'cursor', 'data-title', 'data-placement', 'data-toggle']
    result: list = []
    new_buff = [elem for elem in new_buff if any(key_word in elem for key_word in good_words) or not any(name in elem for name in bad_words)]
    for i, elem in enumerate(new_buff):
        if 'data-dubbing' in elem:
            if '>' in elem:
                result.append(new_buff[i][beginning:new_buff[i].find('>')])
            else:
                result.append(elem)
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

def get_content_all_series(main_page_url: str, update: bool = False) -> list[list[list]]:
    url: str = 'https://animego.org/anime/series?&'
    request: list[list[list]] = extract_video_page_info_series(download_html_page(main_page_url), update)
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

def get_cached_result(main_page_url: str, update: bool = False) -> list[list[list]]:
    cache_folder = "cached_results"
    os.makedirs(cache_folder, exist_ok=True)
    cache_file: str = os.path.join(cache_folder, f"{main_page_url.replace('/', '_')}.pkl")
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            result = pickle.load(f)
    else:
        result: list[list] = get_content_all_series(main_page_url, update)
        with open(cache_file, "wb") as f:
            pickle.dump(result, f)
    return result

def prepare_anime_buffer(url: str, update: bool = False) -> tuple:
    info: list = get_cached_result(url, update)
    titles_dict: dict = info[1]
    anime_content: list[list[list]] = [elem for elem in info[requests_iter] if not all(elements == '' for elements in elem)]
    return anime_content, titles_dict

def check_if_substring_list(buff: list) -> str | None:
    my_buff: list = buff
    for string in my_buff:
        for another_string in my_buff:
            if another_string in string and string != another_string:
                return another_string
    return None

def voices(anime_content: list) -> dict:
    d_voices: dict = {}
    my_anime_content: list = anime_content
    anime_voices: list = [get_voices_all_series(anime) for anime in my_anime_content if anime]
    voices_values: list = []
    for i, anime in enumerate(anime_voices):
        d_sub_voices_for_series: dict = {}
        for voice_series in anime:
            dub_keys: list = [elem for elem in voice_series if 'data-dubbing' in elem]
            check_substring: str | None = check_if_substring_list(voice_series)
            if check_substring:
                voices_values = [check_substring]
            else:
                voices_values: list = [voice for voice in voice_series if 'data-dubbing' not in voice]
            d_sub_voices_for_series.update(dict(zip(dub_keys, voices_values)))
        d_voices[i] = d_sub_voices_for_series
    return d_voices

def players(anime_content: list) -> list:
    player_list: list = []
    my_anime_content: list = anime_content
    anime_player: list = [get_player_all_series(anime) for anime in my_anime_content if anime]
    for anime in anime_player:
        player_sub_list: list = []
        for player_series in anime:
            dub_keys_2: list = [elem for elem in player_series if 'data-dubbing' in elem]
            player_value: list = [voice for voice in player_series if 'data-dubbing' not in voice]
            player_sub_list.append([dub_keys_2, player_value])
        player_list.append(player_sub_list)
    return player_list

def dict_players(player_list: list) -> dict:
    d_player: dict = {}
    my_player_list: list = player_list
    new_player_list: list = players(my_player_list)
    for i, anime in enumerate(new_player_list):
        d_series_player: list = []
        for series in anime:
            d_sub_player: dict = defaultdict(list)
            for key, value in zip(series[0], series[1]):
                d_sub_player[key].append(value)
            d_sub_player = dict(d_sub_player)
            d_series_player.append(d_sub_player)
        d_player[i] = d_series_player
    return d_player

def final_dict(url: str, update: bool = False) -> dict:
    anime_buffer: list = prepare_anime_buffer(url, update)
    d_player: dict = dict_players(anime_buffer[requests_iter])
    d_voices: dict = voices(anime_buffer[requests_iter])
    d_titles: dict = anime_buffer[1]
    result: dict = {}
    for d_num, d_final in d_player.items():
        subvoices: dict = d_voices.get(d_num, {})
        series_result: dict = {}
        for i, d_sub_final in enumerate(d_final):
            subresult: dict = {}
            for key in subvoices.keys():
                if key in d_sub_final.keys():
                    subresult[subvoices[key]] = [elem.removeprefix('data-player=').replace('"', '') for elem in d_sub_final[key]]
            series_result[i+1] = subresult
        result[d_titles[d_num]['Название']] = [series_result, d_titles[d_num]]
    return result

def get_last_id(cursor: psycopg2.connect) -> int:
    cursor.execute("SELECT MAX(id) FROM anime")
    last_id: int = cursor.fetchone()[0]
    if last_id is not None:
        return last_id
    else:
        return 0

def to_db(data_to_db: dict) -> None:
    data: dict = data_to_db
    db_params: dict[str, str] = {
    "dbname": "anime_go",
    "user": "postgres",
    "password": "01012002",
    "host": "localhost",
    "port": "5432"
}
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()
    last_id: int = get_last_id(cur)
    for i, anime_name in enumerate(data):
        cur.execute('INSERT INTO anime (id, anime, anime_jpg_link) VALUES (%s, %s, %s)', (last_id+i+1, anime_name, data[anime_name][-1]['Обложка']))
        cur.execute('INSERT INTO information (id, anime_id, anime_genre, anime_description) VALUES (%s, %s, %s, %s)', (last_id+i+1, last_id+i+1, data[anime_name][-1]['Информация']['Жанр'], json.dumps(data[anime_name][-1]['Информация'], ensure_ascii=False)))
        for episode, links in data[anime_name][0].items():
                for episode_voice, player_links in links.items():
                        for link in player_links:
                            cur.execute('INSERT INTO episodes (anime_id, episode_voice, voice_link, episode_id) VALUES (%s, %s, %s, %s)', (last_id+i+1, episode_voice, link, episode))
    conn.commit()
    cur.close()
    conn.close()

def parse_all_pages(update: bool = False) -> dict:
    page_url: str = 'https://animego.org/anime?sort=a.startDate&direction=asc&type=animes&'
    i: int = 1
    page_number: str = f'page={i}'
    html: str = True
    while html:
        result: dict = final_dict(page_url+page_number, update)
        to_db(result)
        i += 1
        page_number: str = f'page={i}'
        html: str = download_html_page(page_url+page_number)

def parse_update_pages(update: bool = True) -> dict:
    data: dict = final_dict('any_string', update)
    db_params: dict[str, str] = {
    "dbname": "anime_go",
    "user": "postgres",
    "password": "01012002",
    "host": "localhost",
    "port": "5432"
}
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()
    last_id: int = get_last_id(cur)
    for i, anime_name in enumerate(data):
        cur.execute('INSERT INTO anime (id, anime, anime_jpg_link) VALUES (%s, %s, %s)', (last_id+i+1, anime_name, data[anime_name][-1]['Обложка']))
        cur.execute('INSERT INTO information (id, anime_id, anime_genre, anime_description) VALUES (%s, %s, %s, %s)', (last_id+i+1, last_id+i+1, data[anime_name][-1]['Информация']['Жанр'], json.dumps(data[anime_name][-1]['Информация'], ensure_ascii=False)))
        for episode, links in data[anime_name][0].items():
                for episode_voice, player_links in links.items():
                        for link in player_links:
                            cur.execute('INSERT INTO episodes (anime_id, episode_voice, voice_link, episode_id) VALUES (%s, %s, %s, %s)', (last_id+i+1, episode_voice, link, episode))
    conn.commit()
    cur.close()
    conn.close()

def update_db() -> None:
    update_after_minutes: int = 1440
    schedule.every(update_after_minutes).minutes.do(parse_update_pages)  # Вызывает parse_all_pages каждые 30 минут
    check = False
    while check:
        schedule.run_pending()
        time.sleep(1)

def update_thread() -> None:
    update_thread = threading.Thread(target=update_db)
    update_thread.start()

if __name__ == '__main__':
    # Парсинг всех аниме на сайте
    # parse_all_pages()
    # Парсинг ежедневных обновлений
    update_thread()