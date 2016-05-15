#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess as sp
import xmlrpc.client as rpc
import urllib.parse as up
import urllib.request as request
from lxml import etree
import sys
import os
import os.path
import json
import time
import tempfile

def get_download_list_youtube(url, autonumber):
    dllist = []
    with open("info.json", "r") as f:
        info = f.read().split("\n")[:-1]
    # with sp.Popen(["youtube-dl", "-j", url], stdout=sp.PIPE) as proc:
    #     # discard the last empty line
    #     info = proc.stdout.read().decode("utf-8").split("\n")[:-1]
        number = 0
        for line in info:
            episode = json.loads(line)
            if episode["playlist"]:
                playlist = episode["playlist"]
            else:
                playlist = ""
            formats = episode["formats"]
            index = 0
            for fmt in formats:
                if fmt["format_note"] == "DASH audio":
                    index += 1
                else:
                    break
            number += 1
            if autonumber:
                prefix = str(number)+" - "
            else:
                prefix = ""
            basename = prefix + os.path.splitext(episode["_filename"])[0].replace('-'+episode["id"], '')
            name = basename+"-audio."+formats[index - 1]["ext"]
            # download the audio with best quality
            dllist.append({"dir":os.path.join(os.getcwd(), playlist.replace('/', '_').replace(':', '-')),
                "out":name, "url":formats[index - 1]["url"], "id":episode["id"]})
            videoWidth = 0
            videoSize = 0
            for index in range(index, len(formats)):
                if formats[index+1]["format_note"] != "DASH video" and int(formats[index]["width"]) == videoWidth and formats[index]["filesize"] > videoSize:
                    break
                elif formats[index]["format_note"] != "DASH video":
                    break
                videoWidth = int(formats[index]["width"])
                videoSize = formats[index]["filesize"]
            name = basename+"-video."+formats[index - 1]["ext"]
            # download the video with best quality but least size
            dllist.append({"dir":os.path.join(os.getcwd(), playlist.replace('/', '_').replace(':', '-')),
                "out":name, "url":formats[index - 1]["url"], "id":episode["id"]})
    return dllist

def download_youtube_subtitle(videoID, filename):
    keepVid = "http://keepvid.com/?url="+up.quote_plus("http://youtube.com/watch?v="+videoID)+"&mode=subs"
    print(keepVid)
    parser = etree.HTMLParser()
    root = etree.parse(keepVid, parser)
    anchor = root.find("//div[@id='dl']/a")
    if hasattr(anchor, "attrib") and "href" in anchor.attrib:
        href = anchor.attrib["href"]
        with request.urlopen(href) as html:
            with open(filename, "w") as f:
                f.write(html.read().decode("utf-8"))
                print("finish: "+filename)

def get_download_list_ted(url):
    dllist = []
    # with open("info.json", "r") as f:
    #     info = f.read().split("\n")[:-1]
    with sp.Popen(["youtube-dl", "--sub-format", "srt", "--sub-lang", "en", "--write-sub", "-j", url], stdout=sp.PIPE) as proc:
        # discard the last empty line
        info = proc.stdout.read().decode("utf-8").split("\n")[:-1]
        for line in info:
            episode = json.loads(line)
            if episode["playlist"]:
                playlist = episode["playlist"]
            else:
                playlist = ""
            dllist.append({"dir":os.path.join(os.getcwd(), playlist.replace('/', '_').replace(':', '-')),
                "out":episode["_filename"].replace('-'+episode["id"], ''), "url":episode["url"]})
            if episode["requested_subtitles"]:
                dllist.append({"dir":os.path.join(os.getcwd(), playlist.replace('/', '_').replace(':', '-')),
                    "out":os.path.splitext(episode["_filename"].replace('-'+episode["id"], ''))[0]+".srt", "url":episode["requested_subtitles"]["en"]["url"]})
    return dllist

def get_download_list_others(url):
    dllist = []
    with sp.Popen(["youtube-dl", "-j", url], stdout=sp.PIPE) as proc:
        # discard the last empty line
        info = proc.stdout.read().decode("utf-8").split("\n")[:-1]
        for line in info:
            episode = json.loads(line)
            dllist.append({"dir":os.path.join(os.getcwd()),
                "out":episode["_filename"], "url":episode["url"]})
    # if the url is not supported, exit the application
    if "episode" not in locals():
        sys.exit("url not supported")
    # assume that even if there are several parts, they belong to one file 
    # after download finish, we will concatenate them.
    return dllist, episode["title"]+'.'+episode["ext"]

def aria2c_download(dllist):
    fail = False
    with rpc.ServerProxy('http://localhost:6800/rpc') as s:
        mc = rpc.MultiCall(s)
        for download in dllist:
            print(download["url"])
            mc.aria2.addUri([download["url"]], {"dir":download["dir"], "out":download["out"]})
            print("downloading: "+download["out"])
        gids = list(mc()) #real execute, don't forget to call this
        print("waiting for download finish......")

        while True:
            mc = rpc.MultiCall(s)
            for gid in gids:
                mc.aria2.tellStatus(gid, ["gid", "status", "completedLength"])
            completed = 0
            for stat in mc():
                if stat["status"] == "error":
                    if stat["completedLength"] == 0:
                        fail = True
                        break
                    index = gids.index(stat["gid"])
                    gids.remove(stat["gid"])
                    print("download again: " + dllist[index]["out"])
                    s.aria2.removeDownloadResult(stat["gid"])
                    gid = s.aria2.addUri([dllist[index]["url"]], {"dir":dllist[index]["dir"], "out":dllist[index]["out"]})
                    gids.insert(index, gid)
                elif stat["status"] == "complete":
                    completed += 1
            if fail or completed == len(gids):
                break
            else:
                time.sleep(3)
    if fail:
        sys.exit("download fail!")
    else:
        print("congratulation: download finish!")

def main(url, autonumber=False):
    youtube = False
    ted = False
    if "youtube" in url:
        youtube = True
        dllist = get_download_list_youtube(url, autonumber)
    elif "ted.com" in url:
        ted = True
        dllist = get_download_list_ted(url)
    else:
        dllist, final = get_download_list_others(url)

    aria2c_download(dllist)

    if youtube:
        for i in range(len(dllist)):
            # each download has two parts, dash audio and dash video file
            if i % 2 == 0:
                audioFile = os.path.join(dllist[i]["dir"], dllist[i]["out"])
            else:
                videoFile = os.path.join(dllist[i]["dir"], dllist[i]["out"])
                # if video file format is webm, use mkv to merge the video and audio
                final = videoFile.replace('-video', '').replace('webm', 'mkv')
                # when audio file format is webm, codec is opus which ffmpeg doesn't support to encode for mp4.
                if os.path.splitext(audioFile)[1] == ".webm" and os.path.splitext(videoFile)[1] == ".mp4":
                    acodec = "mp3"
                else:
                    acodec = "copy"
                sp.run(['ffmpeg', '-i', videoFile, '-i', audioFile, '-map', '0:0', '-map', '1:0', '-vcodec', 'copy', '-acodec', acodec, final],
                        stdout=sp.PIPE, stderr=sp.PIPE)
                # remove the orignal files
                os.remove(videoFile)
                os.remove(audioFile)
                # try to download the subtitle
                download_youtube_subtitle(dllist[i]["id"], os.path.splitext(final)[0]+".srt")
    elif not ted:
        if len(dllist) > 1:
            tmp = tempfile.mkstemp(suffix=".txt", dir=os.getcwd(), text=True)[1]
            with open(tmp, "w") as f:
                for download in dllist:
                    f.write("file '"+download["out"]+"'\n")
            # refer to https://trac.ffmpeg.org/wiki/Concatenate
            sp.run(['ffmpeg', '-f', 'concat', '-i', tmp, '-c', 'copy', final], stdout=sp.PIPE, stderr=sp.PIPE)
            os.remove(tmp)
            for download in dllist:
                os.remove(download["out"])
        else:
            if os.path.exists(dllist[0]["out"]):
                os.rename(dllist[0]["out"], final)
        # movist doesn't support f4v, convert to mp4, just change the file format, it's fast
        if sys.platform == "darwin" and os.path.splitext(final)[1] == ".f4v" and os.path.exists(final):
            sp.run(['ffmpeg', '-i', final, '-vcodec', 'copy', '-acodec', 'copy', os.path.splitext(final)[0]+".mp4"], stdout=sp.PIPE, stderr=sp.PIPE)
            os.remove(final)
        print("final file:" + final)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Error: there's no download url")
    elif len(sys.argv) == 3 and sys.argv[1] == "-an":
        main(sys.argv[2], autonumber=True)
    else:
        main(sys.argv[1])
