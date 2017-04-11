import sys
import json
import urllib
import requests
import xml.etree.ElementTree as ET

def show(s):
  sys.stdout.write(s + '\n')

def get_query():
  query = ""
  for i in range(1, len(sys.argv)):
    if not sys.argv[i].startswith("--"):
      query += sys.argv[i] + " "
  return query.strip()

def get_param(key, default = None):
  for i in range(1, len(sys.argv)):
    if sys.argv[i].startswith("--" + key + "="):
      return sys.argv[i][len(key) + 3:]
  return default

def get_value(json, key, default = None):
  if json == None:
    return default
  return json[key] if key in json else default

def get_media(json):
  if "tv" in json:
    return TV(json["tv"], Metadata(json))
  if "movie" in json:
    return Movie(json["movie"], Metadata(json))
  return Media(None, Metadata(json))

def has_array(cmp_array, array):
  size = 0
  if array == None:
    return True
  if cmp_array == None:
    return True if array == None else False
  for val in array:
    if val in cmp_array:
      size += 1
  return len(array) == size

def as_int(val):
  if val == None:
    return None
  try:
    return int(val)
  except:
    return None

class Media:
  CATEGORY = "all"
  def __init__(self, json, metadata):
    self.infos = json
    self.metadata = metadata
    self.name = None
    self.year = None

  def __str__(self):
    return self.name + " - " + str(self.year)

class TV(Media):
  CATEGORY = "TV"
  def __init__(self, json, metadata):
    Media.__init__(self, json, metadata)
    self.name = get_value(json, "episode_name")
    self.season = get_value(json, "season")
    self.episode = get_value(json, "episode")
    self.year = get_value(json, "show_started")

  def __str__(self):
    return self.name + " - S" + str(self.season) + "E" + str(self.episode)

class Movie(Media):
  CATEGORY = "Movies"
  def __init__(self, json, metadata):
    Media.__init__(self, json, metadata)
    self.name = get_value(json, "name")
    self.year = get_value(json, "year")

class Metadata:
  QUALITIES = ["Std", "720p", "1080p", "Ultra"]
  def __init__(self, json):
    self.infos = get_value(json, "media_info")
    self.quality = get_value(json, "video_quality")
    self.audios = get_value(self.infos, "audio_lang")
    self.subtitles = get_value(self.infos, "subtitle_lang")
    self.size = get_value(json, "size", 0)

  def __str__(self):
    return self.quality

class ZooqleTorrent:
  NAMESPACE = "https://zooqle.com/xmlns/0.1/index.xmlns"
  def __init__(self, xml_node):
    self.title = None
    self.html_link = None
    self.torrent_link = None
    self.seeders = None
    self.leechers = None
    self.info_hash = None
    self.media = None
    self.__load__(xml_node)

  def load_media(self):
    if self.media != None:
      return self.media
    response = requests.get("https://zooqle.com/api/media/" + self.info_hash)
    self.media = get_media(json.loads(response.content))
    return self.media

  def __load__(self, xml_node):
    self.title = xml_node.find("title").text.encode("ascii", "ignore")
    self.html_link = xml_node.find("link").text
    self.torrent_link = xml_node.find("enclosure").attrib["url"]
    self.seeders = int(xml_node.find("{" + ZooqleTorrent.NAMESPACE + "}seeds").text)
    self.leechers = int(xml_node.find("{" + ZooqleTorrent.NAMESPACE + "}peers").text)
    self.info_hash = xml_node.find("{" + ZooqleTorrent.NAMESPACE + "}infoHash").text

  def __str__(self):
    return self.title + " [" + str(self.seeders) + ":" + str(self.leechers) + "]"

class Criteria:
  def __init__(self):
    self.query = get_query()
    self.category = get_param("category", "all")
    self.quality = get_param("quality")
    self.min_quality = get_param("min-quality")
    self.year = as_int(get_param("year"))
    self.audios = get_param("audios")
    if self.audios != None:
      self.audios = self.audios.split(',')
    self.subtitles = get_param("subtitles")
    if self.subtitles != None:
      self.subtitles = self.subtitles.split(',')
    self.season = as_int(get_param("season"))
    self.episode = as_int(get_param("episode"))
    self.seeders = as_int(get_param("seeders", 0))
    self.max_size = as_int(get_param("size"))
    self.count = as_int(get_param("count", 0))

  def matches(self, torrent):
    is_matching = [
      self.__max_size__,
      self.__quality__,
      self.__min_quality__,
      self.__year__,
      self.__audios__,
      self.__subtitles__,
      self.__season__,
      self.__episode__
    ]
    if torrent.seeders < self.seeders:
      return False
    media = torrent.load_media()
    for func in is_matching:
      if not func(torrent):
        return False
    return True

  def __max_size__(self, torrent):
    if self.max_size == None:
      return True
    return torrent.media.metadata.size <= self.max_size

  def __quality__(self, torrent):
    if self.quality == None:
      return True
    return torrent.media.metadata.quality == self.quality

  def __min_quality__(self, torrent):
    if self.min_quality == None:
      return True
    try:
      i = Metadata.QUALITIES.index(self.min_quality)
      j = Metadata.QUALITIES.index(torrent.media.metadata.quality)
      return j >= i
    except:
      return False

  def __year__(self, torrent):
    if self.year == None:
      return True
    return torrent.media.year == self.year

  def __audios__(self, torrent):
    return has_array(torrent.media.metadata.audios, self.audios)

  def __subtitles__(self, torrent):
    return has_array(torrent.media.metadata.subtitles, self.subtitles)

  def __season__(self, torrent):
    if not isinstance(torrent.media, TV) or self.season == None:
      return True
    return torrent.media.season == self.season

  def __episode__(self, torrent):
    if not isinstance(torrent.media, TV) or self.episode == None:
      return True
    return torrent.media.episode == self.episode

def zooqle_search(what, category = "all"):
  page = 1
  torrents = []
  has_torrents = True
  while has_torrents:
    response = requests.get("https://zooqle.com/search?q=" + urllib.quote_plus(what) + "+category%3A" + category + "&s=ns&v=t&sd=d&fmt=rss&pg=" + str(page))
    channel = ET.fromstring(response.content)[0]
    has_torrents = False
    for child in channel:
      if child.tag == "item":
        has_torrents = True
        torrents.append(ZooqleTorrent(child))
    page += 1
  return torrents

def usage():
  show("Usage: " + sys.argv[0] + " query [--category=<category>] [--quality=<quality>] [--min-quality=<quality>] [--year=<year>] [--audios=<audios>] [--subtitles=<subtitles>] [--season=<season>] [--episode=<episode>] [--seeders=<seeders>] [--size=<size>] [--count=<count>]")
  show("\tcategory\t'TV', 'Movies'")
  show("\tquality\t\t'Std', '720p', '1080p', 'Ultra'")
  show("\tmin-quality\tMinimum quality required")
  show("\tyear\t\tRelease year")
  show("\taudios\t\tHas audios as <audio1>,<audio2>,...")
  show("\tsubtitles\tHas subtitles as <sub1>,<sub2>,...")
  show("\tseason\t\tSeason number. Only applies for TV")
  show("\tepisode\t\tEpisode number. Only applies for TV")
  show("\tseeders\t\tMinimum number of seeders")
  show("\tsize\t\tMaximal size in bytes")
  show("\tcount\t\tNumber of results")
  show("")
  show("Example: " + sys.argv[0] + " rick and morty --category=TV --min-quality=720p --subtitles=en --season=3 --episode=1 --size=1073741824")
  show("Powered by zooqle.com")

if len(sys.argv) == 1:
  usage()
  sys.exit(1)

count = 0
criteria = Criteria()
torrents = zooqle_search(criteria.query, criteria.category)
for torrent in torrents:
  if criteria.matches(torrent):
    show(str(torrent) + "\t" + torrent.html_link + "\t" + torrent.torrent_link)
    count += 1
    if criteria.count != 0 and count >= criteria.count:
      break