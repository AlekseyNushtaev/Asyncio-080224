import asyncio
import datetime

import aiohttp
from more_itertools import chunked
from models import init_db, Person, Session, engine


MAX_CHUNK = 50

async def get_person(client, person_id):
    result = await client.get(f'https://swapi.dev/api/people/{person_id}/')
    json_res = await result.json()
    return json_res

async def get_property(client, url):
    result = await client.get(url)
    json_res = await result.json()
    if json_res.get("title"):
        return json_res.get("title")
    if json_res.get("name"):
        return json_res.get("name")


async def get_url_dict_for_chunk(client, list_of_json):
    url_list = []
    for res in list_of_json:
        url_list.extend(res["films"] + res["species"] + res["starships"] + res["vehicles"] + [res["homeworld"]])
    url_list = list(set(url_list))
    url_coros = [get_property(client, url) for url in url_list]
    url_result = await asyncio.gather(*url_coros)
    return dict(zip(url_list, url_result))


async def insert_to_db(list_of_json):
    lst_of_dct = []
    for json_item in list_of_json:
        person_dict = {
            "id": json_item["id"],
            "name": json_item["name"],
            "birth_year": json_item["birth_year"],
            "eye_color": json_item["eye_color"],
            "films": json_item["films"],
            "gender": json_item["gender"],
            "hair_color": json_item["hair_color"],
            "height": json_item["height"],
            "homeworld": json_item["homeworld"],
            "mass": json_item["mass"],
            "skin_color": json_item["skin_color"],
            "species": json_item["species"],
            "starships": json_item["starships"],
            "vehicles": json_item["vehicles"]
        }
        lst_of_dct.append(person_dict)
    models = [Person(**dct_item) for dct_item in lst_of_dct]
    async with Session() as session:
        session.add_all(models)
        await session.commit()

async def main():
    await init_db()
    client = aiohttp.ClientSession()
    for chunk in chunked(range(1, 200), MAX_CHUNK):
        coros = [get_person(client, person_id) for person_id in chunk]
        result = await asyncio.gather(*coros)
        for id in chunk:                   # добавляем id к каждому персонажу в json
            result[id % MAX_CHUNK - 1]["id"] = id
        result_real = [res for res in result if not res.get("detail")] # убираем пустые id
        url_dict = await get_url_dict_for_chunk(client, result_real)
        # получаем словарь с ключами - все url в персонажах, которые в chunkе (films, species, starships, vehicles)
        # и значениями - названия (films, species, starships, vehicles) асинхронными http-запросами

        for res in result_real:    # переводим значения из списков с url в строки с названиями
            for name in ["films", "species", "starships", "vehicles", "homeworld"]:
                if name == "homeworld":
                    res[name] = url_dict[res[name]]
                elif res.get(name):
                    res[name] = ' ,'.join([url_dict[i] for i in res[name]])
                else:
                    res[name] = ''
        asyncio.create_task(insert_to_db(result_real))
        if result[-1].get('detail'): # прерываем цикл, если есть пустой персонаж в конце списка с результатами
            break
    tasks_set = asyncio.all_tasks() - {asyncio.current_task()}
    await asyncio.gather(*tasks_set)
    await client.close()
    await engine.dispose()

if __name__ == "__main__":
    start = datetime.datetime.now()
    asyncio.run(main())
    print(f'Загрузка в базу завершена {datetime.datetime.now() - start}')