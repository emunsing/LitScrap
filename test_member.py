from .LiteroticaMemberPage import LiteroticaMemberPage
import pytest
import os
import glob

AUTHOR_ID = 1332946  # BuckyDuckman - 16 total stories, mix of series and individual

def test_author_load(author_id=AUTHOR_ID):
    author = LiteroticaMemberPage(author_id)
    author_load_success = author.DownloadMemberPage()

    assert author_load_success, "Error loading author page"
    assert author.MemberName is not None, "Error with author setup"
    assert author.SeriesStories is not None, "SeriesStories should be populated"
    assert author.IndividualStories is not None, "IndividualStories should be populated"

    return

@pytest.mark.skip(reason="Modifies directory structure; needs to be reworked with test fixtures")
def test_author_write(author_id=AUTHOR_ID):
    author = LiteroticaMemberPage(author_id)
    author_load_success = author.DownloadMemberPage()

    # TODO: This modifies the system directory so should be avoided/rewritten
    save_dir = os.path.expanduser("~/Documents/Projects/2026_06_airotica/data")
    member_dir = os.path.join(save_dir, f'{author.MemberName}_{author.MemberID}')
    if not os.path.exists(member_dir):
        os.makedirs(member_dir)

    author.WritePlainTextToFile(member_dir)
    assert len(glob.glob(os.path.join(member_dir,'*.txt'))) > 0, "No text files written"

    author.WriteCSVToDisk(member_dir)
    assert len(glob.glob(os.path.join(member_dir,'*.csv'))) > 0, "No CSV file written"

    author.WriteToDisk(member_dir)
    assert len(glob.glob(os.path.join(member_dir,'*.html'))) > 0, "No HTML files written"
