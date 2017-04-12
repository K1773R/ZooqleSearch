# ZooqleSearch
Find torrents from [zooqle.com](https://zooqle.com) using command line

```
Usage: zooqle.py query [--category=<category>] [--quality=<quality>] [--min-quality=<quality>] [--year=<year>] [--audios=<audios>] [--subtitles=<subtitles>] [--season=<season>] [--episode=<episode>] [--seeders=<seeders>] [--size=<size>] [--count=<count>] [--load=<load>]
        category        'TV', 'Movies'
        quality         'Low', 'Med', 'Std', '720p', '1080p', 'Ultra'
        min-quality     Minimum quality required
        year            Release year
        audios          Has audios as <audio1>,<audio2>,...
        subtitles       Has subtitles as <sub1>,<sub2>,...
        season          Season number. Only applies for TV
        episode         Episode number. Only applies for TV
        seeders         Minimum number of seeders
        size            Maximal size in bytes
        count           Number of results
        load            Number of torrents loaded per iteration
```

This script displays on the standard output the torrents found using your criteria as the following:
```
<torrent title [seeders:leechers]>[TAB]<torrent html link>[TAB]<torrent file>
```

## Example
```
$> ./zooqle.py rick and morty --category=TV --min-quality=720p --subtitles=en --season=3 --episode=1 --size=1073741824
Rick and Morty S03E01 720p HDTV x264-W4F [eztv] [628:89]        https://zooqle.com/rick-and-morty-s03e01-720p-hdtv-x264-w4f-eztv-vox2k.html     https://zooqle.com/downloadvox2k.torrent
Rick and Morty S03E01 720p HDTV x264-W4F[rartv] [142:5] https://zooqle.com/rick-and-morty-s03e01-720p-hdtv-x264-w4f-rartv-vox2q.html    https://zooqle.com/download/vox2q.torrent
```

## Requierements
Python 2.x *or* 3.x
