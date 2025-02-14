from bs4 import BeautifulSoup
from bs4 import NavigableString
from urllib import request
import requests as requestslib
import os
import sys
import logging


def convert_inline_tags_to_markdown(html_text):
    # input: html_text which can be soupified
    # output: html_text which can be soupified, but where the tags_to_replace have been replaced with Markdown equivalents

    tags_to_replace = {
                        'b': '**',
                        'strong': '**',
                        'em': '*',
                        'i': '*'
                        }
    punctuation = {',', '.', ';', ':', '!', '?'}
    soup = BeautifulSoup(html_text, features="lxml")

    # Replace tags with markdown equivalents
    for tag, replacement in tags_to_replace.items():
        for match in soup.find_all(tag):
            if match.string is None:
                match.replace_with("")
                continue
            if len(match.string.strip()) == 0:
                match.replace_with(match.string)
                continue
            if match.string in punctuation:
                match.replace_with(match.string)
                continue

            next_sibling = match.next_sibling
            prev_sibling = match.previous_sibling

            # Punctuation at start of next sibling: Move to inside of tag
            # Whitespace at end of inline tag: Move to next sibling
            # Punctuation at beginning of inline tag: Move to previous sibling
            # Whitespace at beginning of inline tag: Move to previous sibling

            # If there is punctuation at the start of the next sibling string, move it inside the inline tag
            if isinstance(next_sibling, NavigableString) and len(next_sibling) > 0 and next_sibling[0] in punctuation:
                match.string += next_sibling[0]
                match.next_sibling.replace_with(next_sibling[1:])

            # If there is trailing whitespace, move it to the next sibling if there is one:
            rstrip_len = len(match.string.rstrip())
            if len(match.string) > rstrip_len:
                if isinstance(next_sibling, NavigableString) and len(next_sibling) > 0:
                    match.next_sibling.replace_with(match.string[rstrip_len:] + match.next_sibling)
                match.string = match.string[:rstrip_len]

            # If there is a punctuation at the start of the inline tag, move it to the previous sibling
            if isinstance(prev_sibling, NavigableString) and len(prev_sibling) > 0 and match.string[0] in punctuation:
                match.previous_sibling.replace_with(match.previous_sibling + match.string[0])
                match.string = match.string[1:]

            # If there is leading whitespace, move it to the previous sibling if there is one:
            len_leading_whitespace = len(match.string) - len(match.string.lstrip())
            if len_leading_whitespace > 0:
                if isinstance(prev_sibling, NavigableString) and len(prev_sibling) > 0:
                    match.previous_sibling.replace_with(match.previous_sibling + match.string[:len_leading_whitespace])
                match.string = match.string[len_leading_whitespace:]

            match.replace_with(replacement + match.get_text() + replacement)
            
    return str(soup)

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
        html_text = convert_inline_tags_to_markdown(html_text)  # Clean italics and bold
        soup = BeautifulSoup(html_text, features="lxml")

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
        # End conditions: plaintext and html files exist, self.PlainText is populated with rawtext, self.html is populated with html
        html_fname = os.path.join(contentDirectory, self.FileName)
        plaintext_fname = os.path.join(contentDirectory, self.FileName.replace('.html', '.txt'))

        if force_redownload or (self.PlainText is None and not os.path.exists(plaintext_fname)):
            self.DownloadAllPagesNewFormat()
            with open(plaintext_fname, 'w') as file:
                file.write(self.PlainText)
            with open(html_fname, 'w') as file:
                file.write(self.Text)
        elif self.PlainText is None and os.path.exists(plaintext_fname):
            self.PlainText = open(plaintext_fname, 'r').read()
            self.Text = open(html_fname, 'r').read()
        elif self.PlainText is not None and not os.path.exists(plaintext_fname):
            with open(plaintext_fname, 'w') as file:
                file.write(self.PlainText)
            with open(html_fname, 'w') as file:
                file.write(self.Text)

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

    


