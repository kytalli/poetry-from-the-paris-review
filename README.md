# Project Title: Getting poems from gmail :D

## Description
Hello!!! I'm just using a funny template generated by gpt. the program is rather straightforward but you need to get a gmail api credentials first online. please search that up urself and drop the credentials json into this directory. install requirements.txt then run credentials.py for the other token. YAY you're almost set up!!!

after this, you should just run email_extractor, which is basically the code that scrapes ur email based off a query hardcoded into the main function.
the item class is coded in poems_util.py, and basically found values of each poem is being written to these items. it will get stored into a directory called "saved_poems". after you're done scraping, just run pdf_generator.py. This will just loop through the directory n collate it into a whole pdf document :D

i realised that i was rather stupid in the sense that the emails could actually have been parsed as html documents straight and then an infinite scroll html page could just be the document, but then err i guess it wouldn't have the nice pirated e-book look it presently has. But also designing it this way allows me to isolate different components of the poem and then you know, feed it to other things, manipulate it further, maybe generate a content page, get further enriched with SERP-LLM flows... bla bla bla.... but that's for next time. 

this was really fun to build and a good use of my sunday afternoon :D 

here's the link to the anthology/ what you can expect from this code: https://drive.google.com/file/d/1oZWH4OPjPk9fgYWM9uaFjTIIrx2c6ri3/view?usp=share_link
