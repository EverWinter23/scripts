#!/usr/bin/env python
# encoding: utf-8

#
# Very simple Python program to publish the entries of an RSS recentFeed in
# several channels of bufferapp. It uses three configuration files.
#
# - The first one includes the RSS recentFeed of the blog [~/.rssBlogs]
# [Blog3]
# rssFeed:http://fernand0.tumblr.com/rss
#
# There can exist several blogs, and more parameters if needed for other things
# the program will ask which one we want to publish.
#
# - The second one includes the secret data of the buffer app [~/.rssBuffer]
# [appKeys]
# client_id:XXXXXXXXXXXXXXXXXXXXXXXX
# client_secret:XXXXXXXXXXXXXXXXXXXXXXXXXXXxXXXX
# redirect_uri:XXXXXXXXXXXXXXXXXXXXXXXXX
# access_token:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
#
# These data can be obtained registering an app in the bufferapp site.
# Follow instructions at:
# https://bufferapp.com/developers/api
#
# - The third one contains the last published URL [~/.rssBuffer.last]
# It contains just an URL which is the last one published.
# At this moment it only considers one blog

import os
import configparser
import feedparser
import logging
import re
from bs4 import BeautifulSoup

# sudo pip install buffpy version does not work
# Better use:
# git clone https://github.com/vtemian/buffpy.git
# cd buffpy
# sudo python setup.py install
from colorama import Fore
from buffpy.api import API
from buffpy.managers.profiles import Profiles
from buffpy.managers.updates import Update

import time
import sys
import urllib.request, urllib.parse, urllib.error
import imp

imp.reload(sys)
#sys.setdefaultencoding("UTF-8")

PREFIX = "rssBuffer_"
POSFIX = "last"

def selectBlog(sel='a'):
    config = configparser.ConfigParser()
    config.read([os.path.expanduser('~/.rssBlogs')])
    print("Configured blogs:")

    feed = []
    # We are caching the feeds in order to use them later

    i = 1

    for section in config.sections():
        rssFeed = config.get(section, "rssFeed")
        feed.append(feedparser.parse(rssFeed))
        lastPost = feed[-1].entries[0]
        print('%s) %s %s (%s)' % (str(i), section,
                                  config.get(section, "rssFeed"),
                                  time.strftime('%Y-%m-%d %H:%M:%SZ',
                                  lastPost['published_parsed'])))
        if (i == 1) or (recentDate < lastPost['published_parsed']):
            recentDate = lastPost['published_parsed']
            recentFeed = feed[-1]
            recentPost = lastPost
        i = i + 1

    if (sel == 'm'):
        if (int(i) > 1):
            recentIndex = input('Select one: ')
            i = int(recentIndex)
            recentFeed = feed[i - 1]
        else:
            i = 1

    if i > 0:
        recentFeedBase = recentFeed.feed['title_detail']['base']
        ini = recentFeedBase.find('/')+2
        fin = recentFeedBase[ini:].find('.')
        identifier = recentFeedBase[ini:ini+fin] + \
            "_" + recentFeedBase[ini+fin+1:ini+fin+7]
        print("Selected ", recentFeedBase)
        logging.info("Selected " + recentFeedBase)
    else:
        sys.exit()

    selectedBlog = {}
    if (config.has_option("Blog"+str(recentIndex), "linksToAvoid")):
        selectedBlog["linksToAvoid"] = config.get("Blog" + str(recentIndex),
                                                  "linksToAvoid")
    else:
        selectedBlog["linksToAvoid"] = ""

    selectedBlog["twitterAC"] = config.get("Blog" + str(recentIndex),
                                           "twitterAC")
    selectedBlog["pageFB"] = config.get("Blog" + str(recentIndex),
                                        "pageFB")
    selectedBlog["identifier"] = identifier

    print("You have chosen ")
    print(recentFeed.feed['title_detail']['base'])

    return(recentFeed, selectedBlog)

def lookForLinkPosition(linkLast, recentFeed):
    for i in range(len(recentFeed.entries)):
        if (recentFeed.entries[i].link == linkLast):
            break

    #print("i: ", i)

    if ((i == 0) and (recentFeed.entries[i].link == linkLast)):
        logging.info("No new items")
        sys.exit()
    else:
        if (i == (len(recentFeed.entries)-1)):
            logging.info("All are new")
            logging.info("Please, check manually")
            sys.exit()
            # i = len(recentFeed.entries)-1
        logging.debug("i: " + str(i))

    return i

def connectBuffer():
    config = configparser.ConfigParser()
    config.read([os.path.expanduser('~/.rssBuffer')])

    clientId = config.get("appKeys", "client_id")
    clientSecret = config.get("appKeys", "client_secret")
    redirectUrl = config.get("appKeys", "redirect_uri")
    accessToken = config.get("appKeys", "access_token")

    # instantiate the api object
    api = API(client_id=clientId,
              client_secret=clientSecret,
              access_token=accessToken)

    logging.debug(api.info)

    return(api)

def checkPendingPosts(api):
    # We can put as many items as the service with most items allow
    # The limit is ten.
    # Get all pending updates of a social network profile
    serviceList = ['twitter', 'facebook', 'linkedin']
    profileList = {}

    lenMax = 0
    logging.info("Checking services...")

    for service in serviceList:
        profileList[service] = Profiles(api=api).filter(service=service)[0]
        if (len(profileList[service].updates.pending) > lenMax):
            lenMax = len(profileList[service].updates.pending)
        logging.info("%s ok" % service)

    logging.info("There are %d in some buffer, we can put %d" %
                 (lenMax, 10-lenMax))

    return(lenMax, profileList)

def getBlogData(recentFeed, selectedBlog, i=0):
    i = 0  # It will publish the last added item

    soup = BeautifulSoup(recentFeed.entries[i].title)
    theTitle = soup.get_text()
    theLink = recentFeed.entries[i].link

    soup = BeautifulSoup(recentFeed.entries[i].summary)
    theSummary = soup.get_text()

    theSummaryLinks = extractLinks(soup, selectedBlog["linksToAvoid"])
    theImage = extractImage(soup)
    theTwitter = selectedBlog["twitterAC"]
    theFbPage = selectedBlog["pageFB"]

    print("============================================================\n")
    print("Results: \n")
    print("============================================================\n")
    print(theTitle.encode('utf-8'))
    print(theLink)
    print(theSummary.encode('utf-8'))
    print(theSummaryLinks.encode('utf-8'))
    print(theImage)
    print(theTwitter)
    print(theFbPage)
    print("============================================================\n")

    return (theTitle, theLink, theSummary, theSummaryLinks,
            theImage, theTwitter, theFbPage)


def publishPosts(selectedBlog, profileList, recentFeed, lenMax, i):
    for j in range(10-lenMax, 0, -1):
        if (i == 0):
            break
        i = i - 1
        post = obtainBlogData(recentFeed, lenMax, i)
        print("post",post)
        sys.exit()
        serviceList = ['twitter', 'facebook', 'linkedin']
        for service in serviceList:
            line = service
            profile = profileList[service]
            try:
                #profile.updates.new(post)
                line = line + ' ok'
                time.sleep(3)
            except:
                line = line + ' fail'
                failFile = open(os.path.expanduser("~/." +
                                PREFIX+selectedBlog['identifier'] +
                                ".fail"), "w")
                failFile.write(post)
            logging.info("  %s service" % line)
    urlFile = open(os.path.expanduser("~/." +
                   PREFIX + selectedBlog['identifier'] +
                   "." + POSFIX), "w")
    urlFile.write(recentFeed.entries[i].link)
    urlFile.close()

def obtainBlogData(recentFeed, lenMax, i):
        if (recentFeed.feed['title_detail']['base'].find('tumblr') > 0):
            # Link in the content
            soup = BeautifulSoup(recentFeed.entries[i].summary)
            pageLink = soup.findAll("a")
            if pageLink:
                theLink = pageLink[0]["href"]
                theTitle = pageLink[0].get_text()
                if len(re.findall(r'\w+', theTitle)) == 1:
                    logging.debug("Una palabra, probamos con el titulo")
                    theTitle = recentFeed.entries[i].title
                if (theLink[:26] == "https://www.instagram.com/") and \
                   (theTitle[:17] == "A video posted by"):
                    # exception for Instagram videos
                    theTitle = recentFeed.entries[i].title
                if (theLink[:22] == "https://instagram.com/") and \
                   (theTitle.find("(en") > 0):
                    theTitle = theTitle[:theTitle.find("(en")-1]
            else:
                # Some entries do not have a proper link and the rss contains
                # the video, image, ... in the description.
                # In this case we use the title and the link of the entry.
                theLink = recentFeed.entries[i].link
                theTitle = recentFeed.entries[i].title.encode('utf-8')
        elif (selectedBlog.find('wordpress') > 0):
            theTitle = BeautifulSoup(recentFeed.entries[i].title).get_text()
            theLink = recentFeed.entries[i].link
        else:
            logging.info("I don't know what to do!")

        # pageImage = soup.findAll("img")
        theTitle = urllib.parse.quote(theTitle.encode('utf-8'))
        theLink = urllib.parse.quote(theLink,safe=":/")
        post = re.sub('\n+', ' ', theTitle) + " " + theLink
        # Sometimes there are newlines and unnecessary spaces
        # print "post", post
        # There are problems with &

        logging.info("Publishing... %s" % post)

        return post

def main():

    logging.basicConfig(filename='/home/ftricas/usr/var/' + PREFIX + '.log',
                        level=logging.INFO,
                        format='%(asctime)s %(message)s')

    recentFeed, selectedBlog = selectBlog('m')

    urlFile = open(os.path.expanduser("~/." +
                   PREFIX + selectedBlog['identifier'] +
                   "." + POSFIX), "r")

    linkLast = urlFile.read().rstrip()  # Last published

    i = lookForLinkPosition(linkLast, recentFeed)
    i = 0
    api = connectBuffer()

    lenMax, profileList = checkPendingPosts(api)
    logging.info("We have %d items to post" % i)
    print(("We have %d items to post" % i))

    publishPosts(selectedBlog, profileList, recentFeed, lenMax, i)


if __name__ == '__main__':
    main()
