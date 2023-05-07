import json
import os
import requests
import eyed3
from tqdm import tqdm


def getWorkInfo(code):
    url = "https://api.asmr.one/api/work/{id}"
    url = url.replace("{id}", code)
    try:
        r = requests.get(url)
        return r.json()
    except Exception as e:
        print(e)
        return None


def getWorkTracks(code):
    url = "https://api.asmr.one/api/tracks/{id}"
    url = url.replace("{id}", code)
    try:
        r = requests.get(url)
        return r.json()
    except Exception as e:
        print(e)
        return None


def downloadFile(url, path, name):
    try:
        r = requests.get(url, stream=True)
        with open(path + "/" + name, "wb") as f:
            for chunk in tqdm(r.iter_content(chunk_size=1024*1024), total=int(int(r.headers['Content-Length'])/1024/1024), unit="MB", desc="Downloading " + name + "..."):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(e)
        return False


if __name__ == '__main__':
    if not os.path.exists("data"):
        os.mkdir("data")

    workCode = ""
    while True:
        workCode = input("Enter work code: ")
        if workCode.startswith("RJ"):
            workCode = workCode[2:]
        if not workCode.isdigit():
            print("Invalid work code.")
            continue

        # Request work info

        workInfo = getWorkInfo(workCode)
        if workInfo is None or not 'title' in workInfo:
            print("Work not found.")
            continue
        print("Title:\t" + workInfo["title"])
        print("Artist:\t", end="")
        vas = list()
        for va in workInfo["vas"]:
            vas.append(va)
            print(va["name"] + " ", end="")
        print()
        print("Tags:\t", end="")
        for tag in workInfo["tags"]:
            print(tag["i18n"]["zh-cn"]["name"] + " ", end="")
        print()
        print("Date:\t" + workInfo["release"])
        print("Rate:\t" + str(workInfo["rate_average_2dp"]))
        print()
        if not os.path.exists("data/" + workCode):
            os.mkdir("data/" + workCode)
        with open("data/" + workCode + "/info.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(workInfo, indent=4, ensure_ascii=False))

        # Download cover
        if not os.path.exists("data/" + workCode + "/covers"):
            os.mkdir("data/" + workCode + "/covers")
        coverUrlIndex = ["samCoverUrl", "thumbnailCoverUrl", "mainCoverUrl"]
        for idx in coverUrlIndex:
            filename = idx[:-3]
            if workInfo[idx] is not None:
                if not downloadFile(workInfo[idx], "data/" + workCode + "/covers", filename + ".jpg"):
                    print("Download " + filename + " failed.")

        # Request work tracks

        workTracks = getWorkTracks(workCode)
        if workTracks is None:
            print("Tracks not found.")
            continue
        with open("data/" + workCode + "/tracks.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(workTracks, indent=4, ensure_ascii=False))

        # show folders
        print()
        folders = []
        for track in workTracks:
            if track["type"] == "folder":
                folders.append(track)
        for index, folder in enumerate(folders):
            print(str(index) + ":\t" + folder["title"])
        print()
        folderIndex = -1
        while True:
            folderIndex = input("Select: ")
            if not folderIndex.isdigit():
                print("Invalid folder index.")
                continue
            folderIndex = int(folderIndex)
            if folderIndex < 0 or folderIndex >= len(folders):
                print("Invalid folder index.")
                continue
            break

        audios = []
        lyrics = []
        for media in folders[folderIndex]["children"]:
            if media["type"] == "audio":
                audios.append(media)
            elif media["type"] == "text":
                lyrics.append(media)

        for lyric in lyrics:
            lyricTitle = lyric["title"].rsplit(".", 1)[0]
            for i in range(len(audios)):
                audioTitle = audios[i]["title"].rsplit(".", 1)[0]
                if audioTitle == lyricTitle:
                    audios[i]["lyricUrl"] = lyric["mediaDownloadUrl"]
                    break

        for audio in audios:
            audioTitle = audio["title"].rsplit(".", 1)[0]
            print(audioTitle + " " + ("√" if "lyricUrl" in audio else ""))

        print("Download all audios? (Y/n)", end="")
        downloadAll = input()
        if not downloadAll in ["", "Y", "y", "yes", "Yes", "YES"]:
            continue
        print("Downloading...")

        for index, audio in enumerate(audios):
            mainCoverExists = os.path.exists(
                "data/" + workCode + "/covers/mainCover.jpg")
            audioTitle = audio["title"].rsplit(".", 1)[0]
            if not downloadFile(audio["mediaDownloadUrl"], "data/" + workCode, audioTitle + ".mp3"):
                print("Download " + audioTitle + " failed.")
            if "lyricUrl" in audio:
                if not downloadFile(audio["lyricUrl"], "data/" + workCode, audioTitle + ".lrc"):
                    print("Download " + audioTitle + " lyric failed.")
            # add cover
            audioFile = eyed3.load(
                "data/" + workCode + "/" + audioTitle + ".mp3")
            if audioFile is None:
                print("Load " + audioTitle + " failed. Skip.")
                continue
            if mainCoverExists:
                audioFile.tag.images.set(3, open(
                    "data/" + workCode + "/covers/mainCover.jpg", "rb").read(), "image/jpeg")
            else:
                print("Main cover not found. Skip.")
                
            if "lyricUrl" in audio:
                audioFile.tag.lyrics.set(open(
                    "data/" + workCode + "/" + audioTitle + ".lrc", "r", encoding="utf-8").read())
            vasStr = ""
            for i in range(len(vas) - 1):
                vasStr += vas[i]["name"] + "\\\\"
            vasStr += vas[-1]["name"]
            
            audioFile.tag.release_date = workInfo["release"]
            audioFile.tag.album = workInfo["title"]
            audioFile.tag.artist = vasStr
            audioFile.tag.album_artist = workInfo["name"]
            audioFile.tag.track_num = index + 1

            audioFile.tag.save()

        print("Done.")
