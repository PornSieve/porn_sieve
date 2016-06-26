# porn_sieve
Improve your masturbation efficiency!

What is it?

Porn Sieve learns your adult interests and then fetches videos
that match those interests from xvideos.com. I am in no way
associated with that website and in the future I plan on adding
more websites.


Dependencies:

    numpy

    scipy

    sklearn

    pyside

How to use:

    Run main.py with python3.

    The top-left corner includes a list of fetishes to select.

    Enter the page to start on and the number of pages to go through.
    
    Press scrape when you want the program to load up porn for you. A
    preview should appear on the screen if everything is working okay.

    Note that if this is you first time using the program, you may have
    to manually recalculate your model often before it gets a good idea
    of what you like to see.

    On the right is a slider, the rate button, the open button and the
    skip button. When the slider is at the bottom, that inidicates a
    very poor rating. Moving the nub all the way up to the top tells
    the program this video really gets you.

    DO NOT press rate before you hit open. Pressing open will open the
    link in a browser window, whereas rate will record your vote and
    move on. While the program does remember previous ratings, as of
    yet there is not graphical way to get that data out of the database.
    And at any rate, that'd probably be annoying.


    Skip will move on to the next video, while failing to record a rating.

    Pressing quit makes sure any active threads are terminated before
    exiting. I'm not entirely sure why you would want that, but it felt
    like the UI needed another button to look right.
