from LiteroticaStoryPage import LiteroticaStoryPage, convert_inline_tags_to_markdown
from bs4 import BeautifulSoup
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

#@pytest.mark.skip(reason="Modifies directory structure; needs to be reworked with test fixtures")
def test_story_write(story_url=STORY_URL):
    story = LiteroticaStoryPage()
    story.URL = story_url
    save_dir = os.path.expanduser("~/Documents/Projects/2023_06_airotica/test/story")

    if "showstory.php?id=" in story.URL:
        story.FileName = story.URL.split("showstory.php?id=")[1] + ".html"
    else:
        story.FileName = story.URL.split("/")[-1] + ".html"

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    story.DownloadAndWriteStory(save_dir, force_redownload=True)
    assert story.Text is not None, "Error with loading HTML"
    assert story.PlainText is not None, "Error with loading plaintext"
    
    out_fname = os.path.join(save_dir, story.FileName)
    assert os.path.exists(out_fname), "HTML File not written"
    assert os.path.exists(out_fname.replace('.html', '.txt')), "Plaintext File not written"

    return


MARKDOWN_CASES = [
         ("<p>Hello, <em>World.</em></p>", 'Hello, *World.*'),
         ("<p>Hello,<em> World.</em></p>", 'Hello, *World.*'),
         ("<p>Hello<em>, World.</em></p>", 'Hello, *World.*'),
         ("<p>Hello<em>, World</em>.</p>", 'Hello, *World.*'), 
         ("<p>Hello,<em></em> World.</p>", "Hello, World."), # Degenerate, empty tag
         ("<p>Hello,<em> </em>World.</p>", "Hello, World."), # Near-degenerate, only space in tag
         ("<p>Hello,<em>\n</em>World.</p>", "Hello,\nWorld."), # Near-degenerate, only newline in tag
         ("<p>Hello<em>, World. </em></p>", 'Hello, *World.*'), # If whitespace falls at end of full string, it should be trimmed
         ("<p>Hello<em>, World. </em>Fizz buzz.</p>", 'Hello, *World.* Fizz buzz.'),
         ("<p>Hello<em>, World.\n\n</em></p>", 'Hello, *World.*'),
         ("<p>Hello<em>,\n\n World.</em></p>", 'Hello,\n\n *World.*'),
         ("<p>Hello<em>, World. </em><b>Fizz</b> buzz.</p>", 'Hello, *World.* **Fizz** buzz.'),
         ("<p>Hello<em>, World. </em><b>Fizz </b>buzz.</p>", 'Hello, *World.* **Fizz** buzz.'),
         ("<p>Hello<em>, World. </em>Fizz <b>buzz.</b></p>", 'Hello, *World.* Fizz **buzz.**'),
         ("<p>Hello<em>, World. </em>Fizz<b> buzz</b>.</p>", 'Hello, *World.* Fizz **buzz.**'),
        ]

@pytest.mark.parametrize("input_html, target_text", MARKDOWN_CASES)
def test_markdown_converter(input_html, target_text):
    output_doc = convert_inline_tags_to_markdown(input_html)
    output_soup = BeautifulSoup(output_doc, 'html.parser')
    output_text = output_soup.get_text()
    assert output_text == target_text, "error on %s: %s != %s"%(input_html, output_text, target_text)
    return