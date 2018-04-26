#!/usr/bin/env python

import sys
import json
import urllib
import requests
import threading
import xml.etree.ElementTree as ET

def out(s):
  sys.stdout.write(s + '\n')
  sys.stdout.flush()

def err(s):
  sys.stderr.write(s + '\n')
  sys.stderr.flush()

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

def get_media(json_str):
  json = {}
  try:
    json = json.loads(json_str)
  except:
    return Media(None, Metadata({}))
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
    return False
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

def load_async_torrents(torrents, index, count):
  threads = []
  size = len(torrents)
  if index + count > size:
    count = size - index
  for i in range(0, count):
    thread = threading.Thread(target = ZooqleTorrent.load_media, args = (torrents[index + i],))
    thread.daemon = True
    thread.start()
    threads.append(thread)
  for thread in threads:
    thread.join()

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
  QUALITIES = ["Low", "Med", "Std", "720p", "1080p", "Ultra"]
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
    self.media = get_media(response.content)
    if response.status_code != 200:
      err("load_media(" + str(self.info_hash) + "): " + str(response.status_code) + " - " + str(response.content))
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
    self.load = as_int(get_param("load", 10))

  def matches(self, torrent):
    is_matching = [
      self.__seeders__,
      self.__max_size__,
      self.__quality__,
      self.__min_quality__,
      self.__year__,
      self.__audios__,
      self.__subtitles__,
      self.__season__,
      self.__episode__
    ]
    for matches in is_matching:
      if not matches(torrent):
        return False
    return True

  def __seeders__(self, torrent):
    return torrent.seeders >= self.seeders

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
    if self.season == None:
      return True
    if not isinstance(torrent.media, TV):
      return False
    return torrent.media.season == self.season

  def __episode__(self, torrent):
    if self.episode == None:
      return True
    if not isinstance(torrent.media, TV):
      return False
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
  out("Usage: " + sys.argv[0] + " query [--category=<category>] [--quality=<quality>] [--min-quality=<quality>] [--year=<year>] [--audios=<audios>] [--subtitles=<subtitles>] [--season=<season>] [--episode=<episode>] [--seeders=<seeders>] [--size=<size>] [--count=<count>] [--load=<load>]")
  out("\tcategory\t'TV', 'Movies'")
  out("\tquality\t\t'Low', 'Med', 'Std', '720p', '1080p', 'Ultra'")
  out("\tmin-quality\tMinimum quality required")
  out("\tyear\t\tRelease year")
  out("\taudios\t\tHas audios as <audio1>,<audio2>,...")
  out("\tsubtitles\tHas subtitles as <sub1>,<sub2>,...")
  out("\tseason\t\tSeason number. Only applies for TV")
  out("\tepisode\t\tEpisode number. Only applies for TV")
  out("\tseeders\t\tMinimum number of seeders")
  out("\tsize\t\tMaximal size in bytes")
  out("\tcount\t\tNumber of results")
  out("\tload\t\tNumber of torrents loaded per iteration")
  out("")
  out("Example: " + sys.argv[0] + " rick and morty --category=TV --min-quality=720p --subtitles=en --season=3 --episode=1 --size=1073741824")

if len(sys.argv) == 1:
  usage()
  sys.exit(1)

count = 0
criteria = Criteria()
torrents = zooqle_search(criteria.query, criteria.category)
for i in range(0, len(torrents)):
  if i % criteria.load == 0:
    load_async_torrents(torrents, i, criteria.load)
  if criteria.matches(torrents[i]):
    out(str(torrents[i]) + "\t" + torrents[i].html_link + "\t" + torrents[i].torrent_link)
    count += 1
    if criteria.count != 0 and count >= criteria.count:
      break
