from bs4 import BeautifulSoup
from urllib import request
from .LiteroticaStoryPage import LiteroticaStoryPage
import os
import logging
import csv


class LiteroticaMemberPage():
    """
    A Literotica member page.
    Allows for downloading, parsing, getting story pages, and saving.
    """
    
    # Stuff an id in between these two lines to get a valid member URL request.
    # Still have to check to see if the member page is valid by downloading it.
    __memberSubmissionBase = "http://www.literotica.com/stories/memberpage.php?uid="
    __memberSubmissionEnding = """&page=submissions"""

    # Story series row match
    __storySeriesTitleClass = {"class" : "ser-ttl"}
    __storySeriesTitleTag = "tr"

    # Story row match
    __storyTitleClass = {"class" : "root-story r-ott"}
    __storyTitleTag = "tr"

    # Story row match within Series
    __storySeriesIndividualTitleClass = {"class" : "sl"}
    __storySeriesIndividualTitleTag = "tr"
     
    # __save* items are used when saving member pages to disk.
    # Member page header for saving to disk.
    __saveHeader = """<html>\r\n<title>{MemberPageTitle}</title>\r\n<body>\r\n"""

    # Member page series title line for saving to disk.
    __saveSeriesTitleEntry = """<br><strong>{SeriesTitle}</strong><br>\r\n"""    
    
    # Member page individual story line for saving to disk.
    __saveIndividualStoryEntry = """<a href="{StoryLink}">{StoryTitle}</a> - {StorySecondaryLine} - {StoryCategory}<br>\r\n"""
    
    # Member page series story line for saving to disk.
    # Making it the same as individual story lines currently but
    # offers some future options to change this.
    __saveSeriesStoryEntry = __saveIndividualStoryEntry

    # Member page foot for saving to disk.
    __saveFooter = """</body>\r\n</html>\r\n"""

    __savefile_format = "member_{memberID}.html"

    def __init__(self, memberID):
        self.__html = None
        self.__soup = None
        self.__seriesIsParsed = False
        self.__singleStoriesIsParsed = False
        self.__isLoaded = False
        self.__isValidMemberPage = False

        self.MemberPageURL = LiteroticaMemberPage.FormMemberPageURL(memberID)
        self.MemberID = memberID
        self.MemberName = None
        self.MemberCopyright = None
        self.SeriesStories = []
        self.IndividualStories = []

    def IsValidMemberPage(self):
        return self.__isValidMemberPage

    def IsLoaded(self):
        return self.__isLoaded

    def IsParsed(self):
        return self.IsSeriesParsed() and self.IsSingleStoriesParsed()

    def IsSeriesParsed(self):
        return self.__seriesIsParsed

    def IsSingleStoriesParsed(self):
        return self.__singleStoriesIsParsed

    def DownloadMemberPage(self):
        try:
            urlStream = request.urlopen(self.MemberPageURL)
            self.__html = urlStream.read()
            self.__soup = BeautifulSoup(self.__html, features="lxml")
        except:
            return False

        self.__isLoaded = True

        if "Literotica.com - error" in self.__soup.title.string:
            return False
        
        self.__isValidMemberPage = True
        
        try:
            self.ParseMemberInfo()
            self.ParseAllStories()
        except:
            return False

        return self.IsParsed()

    def ParseMemberInfo(self):
        self.MemberName = self.__soup.find("a", class_="contactheader").text

    def ParseAllStories(self):
        try:
            self.ParseSingleStories()
            self.__singleStoriesIsParsed = True

            self.ParseSeriesStories()
            self.__seriesIsParsed = True

        except:
            return False

        return True

    def ParseSingleStories(self):
        SingleStoryResults = self.__soup.findAll(LiteroticaMemberPage.__storyTitleTag,attrs=LiteroticaMemberPage.__storyTitleClass)
        self.IndividualStories = self.__ParseStoryResultForStoryLines(SingleStoryResults)
        return

    def __GetSeriesTitleBlocks(self):
        seriesStoryTitleBlocks = self.__soup.findAll(LiteroticaMemberPage.__storySeriesTitleTag,attrs= LiteroticaMemberPage.__storySeriesTitleClass)
        return seriesStoryTitleBlocks

    def SeriesTitles(self):
        seriesStoryTitleBlocks = self.__GetSeriesTitleBlocks()
        seriesTitles = []
        for storiesSeries in seriesStoryTitleBlocks:
            seriesTitle = storiesSeries.text
            seriesTitles += seriesTitle

        return seriesTitles

    def __ParseSeriesStoriesFromTitleBlocks(self, storiesSeriesBlock):
        rowSibling = storiesSeriesBlock.nextSibling
        thisSeriesStories = []

        # get the next rows on until we no longer have rows or
        # we find a row that is not a series story class
        while rowSibling != None and rowSibling.name == "tr" and LiteroticaMemberPage.__storySeriesIndividualTitleClass["class"] in rowSibling.attrs["class"]:
            thisSeriesStories += self.__ParseStoryResultForStoryLines([rowSibling])
            rowSibling = rowSibling.nextSibling

        return thisSeriesStories

    def ParseSeriesStories(self):
        seriesStoryTitleBlocks = self.__GetSeriesTitleBlocks()
        allSeriesStories = []
        for storiesSeriesBlock in seriesStoryTitleBlocks:
            seriesTitle = storiesSeriesBlock.text
            
            thisSeriesStories = self.__ParseSeriesStoriesFromTitleBlocks(storiesSeriesBlock)

            for story in thisSeriesStories:
                story.SeriesTitle = seriesTitle
        
            allSeriesStories += [(seriesTitle,thisSeriesStories)]

        self.SeriesStories = allSeriesStories
        return 

    def CreateMemberPage(self, contentDirectory):
        # contentDirectory must be a valid directory
        try:
            memberFileName = LiteroticaMemberPage.__savefile_format.format(memberID=self.MemberID)
            memberFilePath = os.path.join(contentDirectory, memberFileName)
            file = open(memberFilePath,"w+")
        except:
            return None

        return file

    def HasStories(self):
        if len(self.SeriesStories) != 0 or len(self.IndividualStories) != 0:
            return True
        else:
            return False

    def WriteToDisk(self, contentDirectory):
        if not self.IsLoaded() or not self.IsParsed() or not self.IsValidMemberPage():
            return False
        try:
            with self.CreateMemberPage(contentDirectory) as file:
                file.write(self.__saveHeader.replace("{MemberPageTitle}" ,"Member #"+str(self.MemberID)))

                for storyEntry in self.IndividualStories:
                    self.__WriteIndividualStoryLine(file,storyEntry)


                for seriesEntry in self.SeriesStories:
                    self.__WriteSeriesTitleLine(file, seriesEntry[0])
                    for seriesIndividualStory in seriesEntry[1]:
                        self.__WriteSeriesStoryLine(file, seriesIndividualStory)

                file.write(self.__saveFooter)
        except:
            return False

        return True
    
    def WriteCSVToDisk(self, contentDirectory):
        if not self.IsLoaded() or not self.IsParsed() or not self.IsValidMemberPage():
            return False
        
        with open(os.path.join(contentDirectory, f'member_{self.MemberID}.csv'),"w+") as file:
            file.write('StoryLink,MemberName,MemberUID,FilePrefix,StoryTitle,StorySecondaryLine,StoryCategory\r\n')  # Write header
            writer = csv.writer(file)  # We use a CSV Writer to appropriately escape commas and quotes

            for storyEntry in self.IndividualStories:
                story_info = [storyEntry.URL, self.MemberName, self.MemberID, storyEntry.FileName.replace('.html', ''), 
                              storyEntry.Title.strip(), storyEntry.SecondaryLine.strip(),storyEntry.Category]
                writer.writerow(story_info)

            for seriesTitle, seriesEntries in self.SeriesStories:
                storyEntry = seriesEntries[0]
                story_info = [storyEntry.URL, self.MemberName, self.MemberID, storyEntry.FileName.replace('.html', ''), 
                              seriesTitle.strip(), storyEntry.SecondaryLine.strip(),storyEntry.Category]
                writer.writerow(story_info)
    
    def WritePlainTextToFile(self, contentDirectory, force_redownload=False):
        if not self.IsLoaded() or not self.IsParsed() or not self.IsValidMemberPage():
            logging.warning('Member page not appropriately loaded!')
            return False

        for storyEntry in self.IndividualStories:
            storyEntry.DownloadAndWriteStory(contentDirectory, force_redownload=force_redownload)

        for seriesTitle, seriesEntries in self.SeriesStories:
            series_slug = seriesTitle.split(":")[0].lower().strip().replace(" ","-")
            series_path = os.path.join(contentDirectory, series_slug)
            if not os.path.exists(series_path):
                os.makedirs(series_path)
            
            series_text = ''
            for seriesIndividualStory in seriesEntries:
                seriesIndividualStory.DownloadAndWriteStory(series_path, force_redownload=force_redownload)
                series_text += seriesIndividualStory.PlainText
            
            with open(os.path.join(contentDirectory, series_slug + '.txt'), 'w') as file:
                file.write(series_text)

        return True

    def __WriteSeriesTitleLine(self, file, seriesTitle):
        entryLine = self.__saveSeriesTitleEntry
        entryLine = entryLine.format(SeriesTitle=seriesTitle)
        # file.write(entryLine.encode("utf-8"))
        file.write(entryLine)

    def __WriteIndividualStoryLine(self, file, storyEntry):
        entryLine = self.__saveIndividualStoryEntry
        entryLine = entryLine.format(StoryLink=storyEntry.RelativePath(),
                                     StoryTitle=storyEntry.Title,
                                     StorySecondaryLine=storyEntry.SecondaryLine,
                                     StoryCategory=storyEntry.Category)
        # file.write(entryLine.encode("utf-8"))
        file.write(entryLine)
        return

    def __WriteSeriesStoryLine(self, file,storyEntry):
        # In the current code, this is the same as the individual story line
        self.__WriteIndividualStoryLine(file, storyEntry)
        return

    @staticmethod
    def FormMemberPageURL(memberID):
        return LiteroticaMemberPage.__memberSubmissionBase + str(memberID) + LiteroticaMemberPage.__memberSubmissionEnding

    
    def __ParseStoryResultForStoryLines(self, storyResults):
        stories = []
        
        for result in storyResults:
            storyFileName = ""
            storyWebLink = ""
            storyTitle = ""

            subElements = result.findAll('td')

            if len(subElements) == 0:
                continue

            storyPage = LiteroticaStoryPage()
            storyPage.URL = subElements[0].find("a")["href"]
            if "showstory.php?id=" in storyPage.URL:
                storyPage.FileName = storyPage.URL.split("showstory.php?id=")[1] + ".html"
            else:
                storyPage.FileName = storyPage.URL.split("/")[-1] + ".html"
            storyPage.MemberID = self.MemberID
            storyTitleLine = subElements[0].text
            if u"\xa0" in storyTitleLine:
                storyTitleLine = storyTitleLine.split(u"\xa0")[0]
                storyTitleLine = storyTitleLine.replace("//","")
                storyTitleLine.strip()

            storyPage.Title = storyTitleLine
            storyPage.Category = subElements[2].find("a").find("span").text
            storyPage.SecondaryLine = subElements[1].text
            storyPage.Date = subElements[3].text
            stories.append(storyPage)

        return stories
