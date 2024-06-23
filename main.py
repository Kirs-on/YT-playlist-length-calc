import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
import sys
from isodate import parse_duration
import json
import os


# checks if api key is valid
def test_api_key(api_key: str) -> bool:
    youtube = build("youtube", "v3", developerKey=api_key)
    channel = youtube.channels().list(part="id", forUsername="youtube")
    try:
        channel.execute()
        return True
    except HttpError:
        return False


# checks if credentials.json file exists, if it does fetches the key from the file and checks
# its credibility, if file doesn't exist or the key isn't valid it prompts user for an input,
# then creates a new file called credentials.json with api key in it.
def check_creds() -> str:
    if os.path.exists("credentials.json"):
        with open("credentials.json", "r") as creds:
            dic = json.load(creds)
            api_key = dic["api_key"]
        youtube = test_api_key(api_key=api_key)
        if youtube == False:
            print("API key not valid")
            os.remove("credentials.json")
        else:
            return api_key
    else:
        api_key = input("Input a valid API Key: ")
        dic = {}
        dic["api_key"] = api_key
        youtube = test_api_key(api_key=api_key)
        if not youtube == False:
            with open("credentials.json", "w") as creds:
                key = json.dumps(dic)
                creds.write(key)
                return api_key
        else:
            print("API key invalid")


# fetches the playilst id from given url
def get_playlist_id(url: str) -> str:
    obj = re.compile(r"list=(.+)")
    list_id = obj.search(url)
    if list_id:
        return list_id.group(1)
    else:
        raise ValueError


def get_playlist_duration(
    api_key: str, playlist_id: str
) -> tuple[datetime.timedelta, int]:
    youtube = build("youtube", "v3", developerKey=api_key)
    if playlist_id[0:2] != "PL":
        raise ValueError
    videos_no = 0
    pl_page_token = None
    total_duration = datetime.timedelta()
    # creates connection object to the api
    while True:
        video_ids = []
        # fetches the ids of 50 (max amount per page) videos
        pl_request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            pageToken=pl_page_token,
            maxResults=50,
        )
        try:
            pl_response = pl_request.execute()
        except HttpError:
            print("Playlist doesn't exist or isn't public")
            sys.exit()
        # adds ids to list called video_ids and than creates a csv string with them
        for item in pl_response["items"]:
            id = item["contentDetails"]["videoId"]
            video_ids.append(id)
        ids = ",".join(video_ids)
        # fetches the details of videos in "ids" string
        vid_request = youtube.videos().list(part="contentDetails", id=ids)
        vid_response = vid_request.execute()
        items = vid_response["items"]
        # exctracts durations from response and parses them into timedelta object using isodate package, adds each video
        # duration to total duration and increments the total videos number by one
        for item in items:
            duration = parse_duration(item["contentDetails"]["duration"])
            total_duration += duration
            videos_no += 1
        # checks if there are more than 50 videos in playlist by checking if there is a "nextPageToken" key in response,
        # if so assigns its value to pl_page_token variable and repeats whole loop, if not breaks from the loop
        try:
            pl_page_token = pl_response["nextPageToken"]
        except KeyError:
            break
    # returns total duration and number of videos
    return (total_duration, videos_no)


# presents results in a nice way
def present_result(duration: datetime.timedelta, vid_no: int) -> str:
    total_seconds = duration.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds - (hours * 3600)) // 60)
    seconds = int((total_seconds - (hours * 3600) - (minutes * 60)))
    result = f"Playlist contains of {vid_no} available videos, with total duration of"
    if hours == 0:
        pass
    else:
        result += f" {hours} hour" if hours == 1 else f" {hours} hours"
    if minutes != 0 and hours != 0:
        result += ","
    if minutes == 0:
        pass
    else:
        result += f" {minutes} minute" if minutes == 1 else f" {minutes} minutes"
    if not (hours == 0 and minutes == 0):
        result += " and"
    result += f" {seconds} second." if seconds == 1 else f" {seconds} seconds."
    return result


def main():
    api_key = None
    while api_key == None:
        api_key = check_creds()

    while True:
        url = input("Input yt url: ")
        try:
            playlist_id = get_playlist_id(url)
            break
        except ValueError:
            print("That URL does not contain a playlist id")
    try:
        duration, number = get_playlist_duration(api_key, playlist_id)
    except ValueError:
        print("Incorrect playlist ID")
        sys.exit()
    print()
    result = present_result(duration, number)
    print(result, end="\n\n")


if __name__ == "__main__":
    main()
