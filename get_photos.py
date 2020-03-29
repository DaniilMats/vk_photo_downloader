import requests
from threading import Thread
from redis import Redis
from vk_token import TOKEN
from typing import Generator, Optional
import logging
import os


class VkWrapper:
    """
    Класс служит для создания генератора ссылок.
    Экземпляр класса инициализируется токеном авторизации.
    Служит исключительно как загрузчик фотографий.
    """
    url: str = "https://api.vk.com/method/photos.getAll"

    def __init__(self, token):
        self.token: str = token

    def get_link_generator(self) -> Optional[Generator]:
        """
        Возвращает генератор фотографий 1280 пх
        из моего аккаунта.
        :return: Generator
        """
        params: dict = {
            "v": "5.52",
            "access_token": self.token
        }
        try:
            r: requests.Response = requests.get(VkWrapper.url, params=params)
        except Exception as e:
            logging.error(f"Не удалось выполнить запрос к серверу по следующей причине: {e}")
        else:
            items: list = r.json()['response']["items"]
            logging.info(f"Получено {len(items)} ссылок")
            for item in items:
                yield item['photo_1280']


class ImgGetter:
    """
    Класс создает подключение к редису и достает последовательно каждую
    фотографию. На вход получает последовательность ключей.
    """

    def __init__(self, keys: set):
        self.keys: set = keys

    def save_to_file(self) -> None:
        """
        Подключается к редису и сохраняет файлы из него.
        :return: None
        """
        path: str = "/photos"
        os.mkdir(path)
        with Redis(host="redis") as redis:
            for key in self.keys:
                with open(f"./photos/{key}.jpg", "wb") as f:
                    f.write(redis.get(key))
                    logging.info(f"Создан файл {key}.jpg")


class Handler(Thread):
    """
    Этот класс наследуется от класса Thread.
    Класс инициируется ссылкой на картинку
    и именем картинки.
    """

    def __init__(self, url: str, name: str):
        Thread.__init__(self)
        self.name: str = name
        self.url: str = url

    def run(self) -> None:
        """
        Переопределяем метод run в модуле Thread, чтобы при вызове start()
        запускалась именно эта функция.
        :return: None
        """
        try:
            r: requests.Response = requests.get(self.url)
        except Exception as e:
            logging.error(f"Не удалось выполнить запрос к серверу по следующей причине: {e}")
        else:
            with Redis(host="redis") as redis:
                redis.set(self.name, r.content)
                logging.info(f"Фотография {self.name} загружена в редис")


def main() -> set:
    """
    Основная функция скрипта. Запрашивает все фотографии.
    Для каждой ссылки создает свой поток.
    Каждая ссылка грузится в сыром виде в Редис.
    Название фотографий формируется по принципу photo_№
    :return: множество имен фотографий
    """
    links: VkWrapper = VkWrapper(TOKEN)
    workers: set = set()
    names: set = set()
    for counter, link in enumerate(links.get_link_generator()):
        name: str = f"photo_{counter}"
        names.add(name)
        worker: Handler = Handler(link, name)
        worker.start()
        workers.add(worker)
    for worker in workers:
        worker.join()
    return names


if __name__ == "__main__":
    # запускаем главную функцию и грузим все в редис
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO )
    names: set = main()

    # создаем экземпляр класса, который будет грузить для нас фотки из редиса
    file_handler: ImgGetter = ImgGetter(names)

    # запускаем загрузчик в файлы
    file_handler.save_to_file()
