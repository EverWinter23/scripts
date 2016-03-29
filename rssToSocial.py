#!/usr/bin/python
# encoding: utf-8
#
# Very simple Python program to publish the last RSS entry of a feed
# in available social networks. 
#
# It shows the blogs available and allows to select one of them.
# 
# It has a configuration file with a number of blogs with:
#    - The RSS feed of the blog
#    - The Twitter account where the news will be published
#    - The Facebook page where the news will be published
# It uses a configuration file that has two sections:
#      - The oauth access token
#
# And more thins. To be done.
#
#
#

import ConfigParser
import os
import logging
import feedparser
import facebook
from linkedin import linkedin
from twitter import *
import re
import sys
import time,datetime
from bs4 import BeautifulSoup
from bs4 import NavigableString
from bs4 import Tag

reload(sys)
sys.setdefaultencoding("UTF-8")

def extractImage(soup):
    pageImage = soup.findAll("img")
    #  Only the first one
    if len(pageImage) > 0:
        imageLink = (pageImage[0]["src"])
    else:
        imageLink = ""

    return imageLink

def extractLinks(soup, linksToAvoid=""):
    j = 0
    linksTxt = ""
    for link in soup("a"):
        if not isinstance(link.contents[0], Tag):
            # We want to avoid embdeded tags (mainly <img ... )
        
            print linksToAvoid
            print re.escape(linksToAvoid)
            print str(link['href'])
            print re.search(linksToAvoid, link['href'])
            if ((linksToAvoid =="") 
                or (not re.search(linksToAvoid, link['href']))):
                link.append(" ["+str(j)+"]")
                linksTxt = linksTxt + "["+str(j)+"] " + link.contents[0] + "\n"
                linksTxt = linksTxt + "    " + link['href'] + "\n"
                j =  j + 1
    if linksTxt != "":
        theSummaryLinks = soup.get_text() + "\n\n" + linksTxt
    else:
        theSummaryLinks = soup.get_text()

    return theSummaryLinks

def selectBlog(sel='a'):
    config = ConfigParser.ConfigParser()
    config.read([os.path.expanduser('~/.rssBlogs')])

    print "Configured blogs:"

    i = 1

    lastPost={}
    for section in config.sections():
        rssFeed = config.get(section, "rssFeed")
        feed = feedparser.parse(rssFeed)
        lastPost[i] = feed.entries[0]
        print str(i), ')', section, config.get(section, "rssFeed"), '(', time.strftime('%Y-%m-%d %H:%M:%SZ', lastPost[i]['published_parsed']), ')'
        if (i == 1) or (recentDate < lastPost[i]['published_parsed']):
            recentDate = lastPost[i]['published_parsed']
            recentIndex = i
            recentPost = lastPost[recentIndex]
        i = i + 1

    if (sel == 'm'):
        if (int(i)>1):
            recentIndex = raw_input ('Select one: ')
            recentPost = lastPost[int(recentIndex)]
        else:
            i = 1

    i = int(recentIndex)

    if i > 0:
        selectedBlog=config.get("Blog"+str(i), "rssFeed")
        ini=selectedBlog.find('/')+2
        fin=selectedBlog[ini:].find('.')
        identifier=selectedBlog[ini:ini+fin]+"_"+selectedBlog[ini+fin+1:ini+fin+7]
        print "Selected ", selectedBlog
        logging.info("Selected "+ selectedBlog)
    else:
        sys.exit()

    if (config.has_option("Blog"+str(recentIndex), "linksToAvoid")):
        linksToAvoid = config.get("Blog"+str(recentIndex), "linksToAvoid")
    else:
        linksToAvoid = ""

    theTwitter = config.get("Blog"+str(recentIndex), "twitterAC")
    theFbPage = config.get("Blog"+str(recentIndex), "pageFB")

    print "You have chosen " 
    print config.get("Blog"+str(recentIndex), "rssFeed")

    return (selectedBlog, identifier, recentPost, linksToAvoid, theTwitter, theFbPage)

def getBlogData(selectedBlog, identifier, recentPost, linksToAvoid, theTwitter, theFbPage):
    i = 0 # It will publish the last added item

    soup = BeautifulSoup(recentPost.title)
    theTitle = soup.get_text()
    theLink  = recentPost.link

    soup = BeautifulSoup(recentPost.summary)
    theSummary = soup.get_text()

    
    theSummaryLinks = extractLinks(soup, linksToAvoid)
    theImage = extractImage(soup)
    
    
    print "============================================================\n"
    print "Results: \n"
    print "============================================================\n"
    print theTitle.encode('utf-8')
    print theLink
    print theSummary.encode('utf-8')
    print theSummaryLinks.encode('utf-8')
    print theImage
    print theTwitter
    print theFbPage
    print "============================================================\n"

    return (theTitle, theLink, theSummary, theSummaryLinks, theImage, theTwitter, theFbPage)

def publishTwitter(index, title, link, twitter):
    
    config = ConfigParser.ConfigParser()
    config.read([os.path.expanduser('~/.rssTwitter')])

    comment='Publicado!'
    statusTxt = comment+" "+title+" "+link

    CONSUMER_KEY = config.get("appKeys", "CONSUMER_KEY")
    CONSUMER_SECRET = config.get("appKeys", "CONSUMER_SECRET")
    TOKEN_KEY = config.get(twitter, "TOKEN_KEY")
    TOKEN_SECRET = config.get(twitter, "TOKEN_SECRET")

    authentication  = OAuth(
                TOKEN_KEY, 
                TOKEN_SECRET, 
                CONSUMER_KEY, 
                CONSUMER_SECRET)
    t = Twitter(auth=authentication)
    t.statuses.update(status=statusTxt)

def publishFacebook(index, title, link, summaryLinks, image, fbPage):
    config = ConfigParser.ConfigParser()
    config.read([os.path.expanduser('~/.rssFacebook')])

    oauth_access_token= config.get("Facebook", "oauth_access_token")

    graph = facebook.GraphAPI(oauth_access_token)
    pages = graph.get_connections("me", "accounts")

    for i in range(len(pages['data'])):
        if (pages['data'][i]['name'] == fbPage):
            print "\tWriting in... ", pages['data'][i]['name'],"\n"
            graph2 = facebook.GraphAPI(pages['data'][i]['access_token'])
            graph2.put_object(pages['data'][i]['id'], 
                "feed", message = title+" \n"+ summaryLinks, link=link, 
                picture = image, 
                name=title, caption='',
                description=summaryLinks.encode('utf-8'))


def publishLinkedin(title, link, summary, image):
    config = ConfigParser.ConfigParser()
    config.read([os.path.expanduser('~/.rssLinkedin')])

    CONSUMER_KEY    = config.get("Linkedin", "CONSUMER_KEY")
    CONSUMER_SECRET = config.get("Linkedin", "CONSUMER_SECRET")
    USER_TOKEN      = config.get("Linkedin", "USER_TOKEN")
    USER_SECRET     = config.get("Linkedin", "USER_SECRET")
    RETURN_URL      = config.get("Linkedin", "RETURN_URL"), 

    authentication  = linkedin.LinkedInDeveloperAuthentication(
                CONSUMER_KEY, 
                CONSUMER_SECRET, 
                USER_TOKEN, 
                USER_SECRET,
                RETURN_URL, 
                linkedin.PERMISSIONS.enums.values())

    application = linkedin.LinkedInApplication(authentication)

    comment='Publicado! '+title
    application.submit_share(comment, title, summary, link, image)


def main():
    logging.basicConfig(filename='/home/ftricas/usr/var/rssSocial_.log',
                            level=logging.INFO,format='%(asctime)s %(message)s')
    if len(sys.argv) > 1:
        if sys.argv[1] == "-m":
            selectedBlog, index, recentPost = selectBlog('m')
    else:
        selectedBlog, index, recentPost, linksToAvoid, twitter, fbPage = selectBlog()

    title, link, summary, summaryLinks, image, twitter, fbPage =  getBlogData(selectedBlog, index, recentPost, linksToAvoid, twitter, fbPage)

    print "Twitter...\n"
    if twitter:
        try:
            publishTwitter(index, title, link, twitter)
        except:
            print "Twitter posting failed!\n"
            print "Unexpected error:", sys.exc_info()[0]

    print "Facebook...\n"
    if fbPage:
        try:
            publishFacebook(index, title, link, summaryLinks, image, fbPage)
        except:
            print "Facebook posting failed!\n"
            print "Unexpected error:", sys.exc_info()[0]

    print "Linkedin...\n"
    try:
        publishLinkedin(title, link, summary, image)
    except:
        print "Linkedin posting failed!\n"
        print "Unexpected error:", sys.exc_info()[0]
    
    # Now we can publish it in some social network

if __name__ == '__main__':
   main()

