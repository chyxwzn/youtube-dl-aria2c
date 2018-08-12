# youtube-dl-aria2c
Integrate youtube-dl with aria2c, download video, audio, subtitle seperately, then use ffmpeg to merge them.
# usage
```text
usage: dl-video [-h] [-an] [-b] [-i INDEX] [-p PROXY] [-f] url

download video easily

positional arguments:
  url                   the video's url or file contains urls

optional arguments:
  -h, --help            show this help message and exit
  -an, --auto_number    append number before file name for playlist
  -b, --best            choose best video quality
  -i INDEX, --index INDEX
                        choose video index manually
  -p PROXY, --proxy PROXY
                        [0/1] choose proxy or not manually
  ```
if you choose -b or -i, then you can download in background with &.  
by default, youtube and ted will be downloaded with proxy `http://127.0.0.1:8118`.  
you could set your proxy with this address or you could modify the code.  
if you want override the deafult option if use proxy or not, use -p 0 or -p 1 manually.  

