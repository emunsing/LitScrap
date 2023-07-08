from bs4 import BeautifulSoup
from urllib import request
import requests as requestslib
import os
import logging


class LiteroticaStoryPage():
    """Literotica Story Page"""

    __saveHeader = """<html>\r\n<title>{Title}</title>\r\n<body>\r\n"""

    __saveMemberLine = '<h1><a href="..\\memberPages\\member_{MemberID}.html">member #{MemberID}</a></h1><br>\r\n'

    __saveFooter = """</body>\r\n</html>"""

    def __init__(self):
        self.Title = None
        self.MemberID = 0
        self.FileName = None
        self.URL = None
        self.Category = None
        self.SecondaryLine = None
        self.Text = None  # Concatenated HTML blocks of the story pages
        self.PlainText = None  # Raw text, separated with newlines
        self.Rating = None
        
        self.SavePath = None

        self.__isSeries = False
        self.__isSingleStory = False
        self.__isDownloaded = False
        self.__isParsed = False
        self.__PageCount = 0

    @staticmethod
    def clean_plaintext(html_text):        
        tags_to_replace = {
                                'b': '**',
                                'strong': '**',
                                'em': '*',
                                'i': '*'
                            }
        soup = BeautifulSoup(html_text, features="lxml")

        # Replace tags with markdown equivalents
        for tag, replacement in tags_to_replace.items():
            for match in soup.find_all(tag):
                match.replace_with(replacement + match.get_text() + replacement)

        paragraphs = soup.find_all('p')
        paragraph_texts = [txt for p in paragraphs if (txt:=p.get_text().strip()) != '']
        return '\n\n'.join(paragraph_texts)
    
    def DownloadAllPages(self):
        urlStream = request.urlopen(self.URL+"?page=1")
        html = urlStream.read()
        soup = BeautifulSoup(html, features="lxml")
        try:
            pageblock = soup.findAll("span",attrs={"class" :"b-pager-caption-t r-d45"})
            self.__PageCount = int(pageblock[0].contents[1].replace(" Pages:",""))
        except:
            # TODO: Make this more specific. This fails quietly on a valid page when the format changes.
            return False

        # Note: Avoid .prettify() as it inserts linebreaks around inline tags, which make future processing difficult. 
        storyText = str(soup.find("div",attrs={"class": "b-story-body-x x-r15"})) + "\r\n"
        if self.__PageCount != 1:
            for pageNum in range(2,self.__PageCount+1):
                urlStream = request.urlopen(self.URL+"?page="+str(pageNum))
                html = urlStream.read()
                soup = BeautifulSoup(html)
                storyText += str(soup.find("div",attrs={"class": "b-story-body-x x-r15"})) + "\r\n"
        self.Text = storyText.encode("utf-8")
        self.PlainText = self.clean_plaintext(self.Text)
        return True
    
    def DownloadAllPagesNewFormat(self):
        # Handles HTML format which is current as of 2023-06-23

        urlstream = request.urlopen(self.URL)
        html = urlstream.read()
        soup = BeautifulSoup(html, features="lxml")

        # Get number of pages
        pageblock = soup.findAll("div",attrs={"class" :"panel clearfix l_bH"})
        if pageblock:
            pagenums = pageblock[0].findAll("a",attrs={"class" :"l_bJ"})
            page_count = int(pagenums[-1].text)
        else:
            page_count = 1
            
        # self.Rating = soup.find("span", class_="aT_cl").text
        # Get first page story
        storyText = str(soup.find("div", class_='aa_ht')) + "\r\n"

        for i in range(2, page_count+1):
            logging.info(f"Getting page {i}")
            urlstream = request.urlopen(self.URL + f'?page={i:d}')
            html = urlstream.read()
            soup = BeautifulSoup(html, features="lxml")
            storyText += str(soup.find("div", class_='aa_ht')) + "\r\n"

        self.Text = storyText
        self.PlainText = self.clean_plaintext(storyText)
        return True

            
    def DownloadAndWriteStory(self, contentDirectory, force_redownload=False):
        # End conditions: plaintext file exists, and self.PlainText is populated with the text
        output_fname = os.path.join(contentDirectory, self.FileName.replace('.html', '.txt'))

        if force_redownload or (self.PlainText is None and not os.path.exists(output_fname)):
            self.DownloadAllPagesNewFormat()
            with open(output_fname, 'w') as file:
                file.write(self.PlainText)
        elif self.PlainText is None and os.path.exists(output_fname):
            self.PlainText = open(output_fname, 'r').read()
        elif self.PlainText is not None and not os.path.exists(output_fname):
            with open(output_fname, 'w') as file:
                file.write(self.PlainText)

    def WriteToDisk(self, contentDirectory):
        # This did not have a caller or a unit test, so I'm working with my best understanding of the intent
        try:
            with self.CreateStoryPage(contentDirectory, self.FileName) as file:
                self.__WriteStoryPageHeader(file)
                self.__WriteStoryPageMemberLine(file)
                self.__WriteStoryPageText(file)
                self.__WriteStoryPageFooter(file)
        except:
            return False

        return True

    def __WriteStoryPageText(self,file):
        file.write(self.Text.encode("utf-8"))
        return

    def __WriteStoryPageFooter(self, file):
        file.write(self.__saveFooter)
        return

    def __WriteStoryPageMemberLine(self, file):
        memberLine = self.__saveMemberLine.replace("{MemberID}",str(self.MemberID))
        file.write(memberLine.encode("utf-8"))
        return

    def __WriteStoryPageHeader(self, file):
        storyPageHeader = self.__saveHeader.replace("{Title}", self.Title)
        file.write(storyPageHeader.encode("utf-8"))
        return

    def CreateStoryPage(self, contentDirectory, fileName):
        try:
            storyFilePath = os.path.join(contentDirectory, "storyPages", fileName)
            file = open(storyFilePath,"w+")
        except:
            return None
        return file

    def RelativePath(self):
        # text Path for insertion into the summary page written to HTML
        return "../storyPages/" + self.FileName

    


