from LiteroticaStoryPage import LiteroticaStoryPage
import pytest
import os
import glob

STORY_URL = "https://www.literotica.com/s/a-pale-court-in-beauty-and-decay"

def test_story_load(story_url=STORY_URL):
    story = LiteroticaStoryPage()
    story.URL = story_url

    res = story.DownloadAllPagesNewFormat()

    assert res, "Error loading story page"
    assert story.Text is not None, "Error with loading HTML"
    assert story.PlainText is not None, "Error with loading plaintext"

    return