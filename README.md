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

    Recalculate predictions should be working properly now and redo
    its prediction for the videos sitting in the video queue. This may
    be necessary in the beginning when the program is still learning
    your interests. Personally, I've found that it may be just as
    important to rate videos you don't like as those you do. I try to
    get an even split in the beginning before the thing warms up.

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

    Pressing quit directly will save your model and encoder in its current
    state. Without it, a new model must be train from scratch which depend-
    ing on the amount of data saved, can take a long time.


Troubleshooting:

    If anything goes wrong try:

        1. Turning it on and then off again.

        2. Deleting *.pkl files and then hitting "recalculate prediction model."

        3. Deleting default.db (will remove your rate history).

        4. Leave an issue so I can fix it.
