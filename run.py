import os
import ssl

import certifi
import ujson as json
from aiohttp import ClientSession
from alive_progress.animations import bar_factory
from pydantic import BaseModel
from yarl import URL

from typing import (
    TYPE_CHECKING,
    Optional,
)
from github3 import GitHub

if TYPE_CHECKING:
    from github3.gists.gist import ShortGist
api = URL("https://wakatime.com/api/v1/users/current/stats/last_7_days")
ssl_context = ssl.create_default_context(cafile=certifi.where())
# noinspection SpellCheckingInspection
BAR_STYLES = {
    "SOLIDLT": "░▏▎▍▌▋▊▉█",
    "SOLIDMD": "▒▏▎▍▌▋▊▉█",
    "SOLIDDK": "▓▏▎▍▌▋▊▉█",
    "EMPTY": " ▏▎▍▌▋▊▉█",
    "UNDERSCORE": "▁▏▎▍▌▋▊▉█",
}


class Model(BaseModel):
    class Config:
        json_dumps = json.dumps
        json_loads = json.loads


class Language(Model):
    decimal: float
    digital: str
    hours: int
    minutes: int
    name: str
    percent: float
    text: str
    total_seconds: float

    class Config:
        json_dumps = json.dumps
        json_loads = json.loads


class WakaResult(Model):
    languages: list[Language]


API_KEY = os.environ['API_KEY']
GIST_ID = os.environ['GIST_ID']
GH_TOKEN = os.environ['GH_TOKEN']
FILE_NAME = os.environ.get('FILE_NAME', '📊 本周开发报告')
BAR_STYLE = BAR_STYLES.get(os.environ.get('BAR_STYLE', 'EMPTY').upper())


def format_time(hours, minutes) -> str:
    if hours == 0:
        return f"{minutes}m"
    else:
        return f"{hours}h{minutes}m"


def format_process(percent: float) -> str:
    bar = bar_factory(BAR_STYLE[1:], background=BAR_STYLE[0])
    return ''.join(bar(25)(percent / 100)).strip('|')


def format_percent(percent: float) -> str:
    return f"{round(percent, 1)}%"


def make_box(languages: list[Language]) -> list[str]:
    names = map(lambda x: x.name, languages)
    times = map(lambda x: format_time(x.hours, x.minutes), languages)
    processes = map(lambda x: format_process(x.percent), languages)
    percents = map(lambda x: format_percent(x.percent), languages)
    result = []
    for name, time, process, percent in zip(names, times, processes, percents):
        name: str
        time: str
        process: str
        percent: str
        result.append(
            name.ljust(15) + '🕓 ' + time.ljust(7) + process.ljust(26) +
            percent.rjust(5)
        )
    return result


async def main():
    github_client = GitHub()
    github_client.login(token=GH_TOKEN)
    gist: Optional["ShortGist"] = None

    async with ClientSession(
            json_serialize=json.dumps, raise_for_status=True
    ) as client:
        async with client.get(
                api,
                params={'api_key': API_KEY},
                ssl_context=ssl_context
        ) as response:
            waka_result = WakaResult.parse_obj((await response.json())['data'])
    box_str = '\n'.join(make_box(waka_result.languages[:5]))
    files = {FILE_NAME: {'content': box_str}}

    for g in github_client.gists():
        if g.id == GIST_ID:
            gist = g
    if not gist:
        github_client.create_gist(
            "Weekly development breakdown", files, public=True
        )
    else:
        gist.edit("Weekly development breakdown", files=files)
    print("Updating gist successfully")

    await client.close()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
