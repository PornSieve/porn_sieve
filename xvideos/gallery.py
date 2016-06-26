import re


vid_xpath = "//a[starts-with(@href, '/video')]/@href"
img_xpath = "//div[@class='thumb']/script"


# might as well compile this since it's being called 20 times a page
thumb_regex = re.compile("(http://img).*(.jpg)")

def img_munge(elem):
    return thumb_regex.search(elem.text).group()


def mozaique_munge(url):
    return re.sub("/[0-9a-f]*\.[0-9]*\.jpg", "/mozaiquehome.jpg", url)
